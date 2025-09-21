import datetime as dt
import gzip
import json
import logging
import lzma
import os
import shutil
import time
import tomllib
import traceback
import uuid
from collections.abc import Callable
from logging.config import dictConfig
from logging.handlers import RotatingFileHandler, TimedRotatingFileHandler
from pathlib import Path
from typing import Any, Literal
from zoneinfo import ZoneInfo

from mrml_common.error import PathTraversalError
from mrml_common.secure import secure_path


logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)

logger = logging.getLogger(__name__)


def setup_logging_from_toml(
    path: str = "logging.toml",
    section: str = "logging",
    *,
    logging_basedir: str = "/appdata/applogs",
) -> None:
    with open(path, "rb") as f:
        data: dict[str, Any] = tomllib.load(f)
    cfg: dict[str, Any] = data.get(section, {})

    handlers = cfg.get("handlers", {})
    for name, handler in sorted(handlers.items()):
        if "filename" in handler:
            try:
                log_path = Path(handler["filename"]).resolve()
                logger.debug("before secure log filepath: %s", log_path)
                log_path = secure_path(
                    log_path,
                    logging_basedir,
                    allow_relative=False,
                )
                logger.debug("after secure log filepath: %s", log_path)
                log_path.parent.mkdir(exist_ok=True, parents=True)
                logger.info("%s directory is created for logging", log_path.parent)
            except PathTraversalError as e:
                logger.warning(f"Fail to create logfile: {log_path}, {e.__cause__}")
                del handlers[name]
                continue

    cfg["handlers"] = handlers
    if cfg.get("root"):  # add only valid handlers
        cfg["root"]["handlers"] = list(handlers.keys())
    dictConfig(cfg)


def create_logger_config_file(filepath: str) -> Path:
    config_filepath = Path(filepath)
    if not config_filepath.parent.exists():
        config_filepath.parent.mkdir(exist_ok=True, parents=True)

    config_filepath.write_text("""[logging]""")
    return config_filepath


class BaseFormatter(logging.Formatter):
    """
    Base Log formatters. Provides common log field extraction.
    """

    def __init__(self, *, tz: str = "UTC", **kwargs):
        super().__init__(**kwargs)
        self._tz = ZoneInfo(tz)

    def formatTime(self, record: logging.LogRecord, datefmt: str | None = None) -> str:
        """Override formatTime of super"""
        ts = dt.datetime.fromtimestamp(record.created, tz=self._tz)
        fmt = datefmt or self.datefmt
        if fmt:
            return ts.strftime(fmt)
        return ts.isoformat()

    def get_log_data(self, record: logging.LogRecord) -> dict[str, Any]:
        # NOTE: `service` field는 Kubernetes 에서 환경변수로 설정
        log_data = {
            "timestamp": self.formatTime(record),
            "level": record.levelname,
            "module": record.module,
            "line": record.lineno,
            "logger.name": record.name,
            "logger.process": record.process,
            "logger.thread_name": record.threadName,
            "function": record.funcName,
            "trace_id": getattr(record, "transaction", uuid.uuid4()),
            "message": record.getMessage(),
        }
        if record.exc_info:
            log_data["traceback"] = traceback.format_exc().strip().replace("\n", " | ")
        elif isinstance(record.msg, str) and "RuntimeWarning" in record.msg:
            log_data["traceback"] = record.getMessage()
        return log_data


class JsonFormatter(BaseFormatter):
    def format(self, record: logging.LogRecord) -> str:
        log_data = self.get_log_data(record)
        try:
            result = json.dumps(log_data, ensure_ascii=False)
        except TypeError:
            result = json.dumps(log_data, ensure_ascii=False, default=str)
        return result


class LogfmtFormatter(BaseFormatter):
    def format(self, record: logging.LogRecord) -> str:
        log_data = self.get_log_data(record)

        def fmt_value(val: Any) -> str:
            if isinstance(val, str):
                if any(c in val for c in " ="):
                    return '"' + val.replace('"', '""') + '"'
                return val
            return str(val)

        return " ".join(f"{k}={fmt_value(v)}" for k, v in log_data.items())


class CompressedRotatingFileHandler(RotatingFileHandler):
    def __init__(
        self,
        filename: str | os.PathLike[str],
        *,
        max_bytes: int = 10 * 1024 * 1024,
        backup_count: int = 7,
        compression: Literal["gz", "xz"] | None = None,
        compresslevel: int = 6,
        encoding: str | None = "utf-8",
        delay: bool = True,
        mode: str = "a",
    ) -> None:
        if not (0 < compresslevel < 9):
            raise ValueError("compresslevel must be in [0, 9].")

        p = Path(filename)
        p.parent.mkdir(parents=True, exist_ok=True)

        super().__init__(
            filename=str(p),
            maxBytes=max_bytes,
            backupCount=backup_count,
            encoding=encoding,
            delay=delay,
            mode=mode,
        )

        if compression is None:
            return  # RotatingFileHandler
        if compression not in ("gz", "xz"):
            raise ValueError("compression must be 'gz', 'xz', or None")

        level = max(0, min(9, int(compresslevel)))  # minimum is 0

        # select rotator function
        match compression:
            case "gz":

                def _rotator(src: str, dst: str) -> None:
                    with (
                        open(src, "rb") as sf,
                        gzip.open(dst, "wb", compresslevel=level) as zf,
                    ):
                        shutil.copyfileobj(sf, zf)
                    os.remove(src)

            case "xz":

                def _rotator(src: str, dst: str) -> None:
                    with (
                        open(src, "rb") as sf,
                        lzma.open(dst, "wb", preset=level) as zf,
                    ):
                        shutil.copyfileobj(sf, zf)
                    os.remove(src)

            case _:
                return  # RotatingFileHandler

        self.namer = lambda name: f"{name}.{compression}"
        self.rotator = _rotator


class CompressedTimedRotatingFileHandler(TimedRotatingFileHandler):
    def __init__(
        self,
        filename: str,
        when: str = "h",
        interval: int = 1,
        backupCount: int = 0,
        encoding: str | None = None,
        delay: bool = False,
        utc: bool = False,
        atTime: dt.datetime.time | None = None,
        errors: str | None = None,
        *,
        compression: str = "gz",
        compression_level: int = 9,
        date_format: str = "%Y-%m-%d",
    ) -> None:
        base_path = Path(filename)
        self.dir_path: Path = base_path.parent
        self.stem: str = base_path.stem
        self.ext: str = base_path.suffix or ".log"

        now = dt.datetime.utcnow() if utc else dt.datetime.now()
        date_str = now.strftime(date_format)
        initial_filename = self.dir_path / f"{self.stem}-{date_str}{self.ext}"

        super().__init__(
            filename=str(initial_filename),
            when=when,
            interval=interval,
            backupCount=backupCount,
            encoding=encoding,
            delay=delay,
            utc=utc,
            atTime=atTime,
            errors=errors,
        )

        if compression not in {"gz", "xz"}:
            raise ValueError("compression must be 'gz' or 'xz'")
        if not (0 <= compression_level <= 9):
            raise ValueError("compression_level must be between 0 and 9")

        self.compression = compression
        self.compression_level = compression_level
        self.date_format = date_format

        # rotate() -> rotator(src, dst) 에서 dst가 최종 경로이므로 namer는 쓰지 않음
        self.namer = None
        self.rotator = self._make_rotator()

    def _make_rotator(self) -> Callable[[str, str], None]:
        if self.compression == "gz":

            def _rotator(src: str, dst: str) -> None:
                with (
                    open(src, "rb") as sf,
                    gzip.open(dst, "wb", compresslevel=self.compression_level) as df,
                ):
                    shutil.copyfileobj(sf, df)
                os.remove(src)

        else:

            def _rotator(src: str, dst: str) -> None:
                with (
                    open(src, "rb") as sf,
                    lzma.open(dst, "wb", preset=self.compression_level) as df,
                ):
                    shutil.copyfileobj(sf, df)
                os.remove(src)

        return _rotator

    def _build_backup_path(self, date_str: str) -> Path:
        # default backup path
        candidate = (
            self.dir_path / f"{self.stem}{self.ext}.{date_str}.{self.compression}"
        )
        if not candidate.exists():
            return candidate

        # if duplicate, add index
        index = 1
        while True:
            indexed = (
                self.dir_path
                / f"{self.stem}{self.ext}.{date_str}-{index}.{self.compression}"
            )
            if not indexed.exists():
                return indexed
            index += 1

    def doRollover(self) -> None:  # type: ignore[override]
        if self.stream:
            self.stream.close()
            self.stream = None

        # 백업 파일명 생성 (date_format 적용, 충돌 시 .<idx> 부여)
        last_rollover_timestamp = self.rolloverAt - 1
        suffix_tuple = (
            time.gmtime(last_rollover_timestamp)
            if self.utc
            else time.localtime(last_rollover_timestamp)
        )
        date_str_for_backup = time.strftime(self.suffix, suffix_tuple)
        backup_path = self._build_backup_path(date_str_for_backup)

        # rotator가 압축 실행
        if os.path.exists(self.baseFilename):
            self.rotate(self.baseFilename, str(backup_path))

        # 오래된 백업 삭제
        if self.backupCount > 0:
            self._prune_backups(self.backupCount)

        # 새 실행 파일 오픈 (date_format 적용)
        now = dt.datetime.utcnow() if self.utc else dt.datetime.now()
        date_str_for_live = now.strftime(self.date_format)
        new_live_path = self.dir_path / f"{self.stem}-{date_str_for_live}{self.ext}"
        self.baseFilename = os.path.abspath(str(new_live_path))
        if not self.delay:
            self.stream = self._open()

        # 다음 회전 시각 계산
        current_time = int(time.time())
        next_rollover_time = self.computeRollover(current_time)
        if next_rollover_time <= current_time:
            next_rollover_time = current_time + self.interval
        self.rolloverAt = next_rollover_time

    def _prune_backups(self, keep: int) -> None:
        """
        appname.log.<date>[.<idx>].(gz|xz) 패턴으로 오래된 파일 삭제.
        # date_format에 시간/분이 들어가도 와일드카드로 모두 매칭
        """
        pattern_gz = f"{self.stem}{self.ext}.*.gz"
        pattern_xz = f"{self.stem}{self.ext}.*.xz"
        files = sorted(
            [
                *self.dir_path.glob(pattern_gz),
                *self.dir_path.glob(pattern_xz),
            ],
            key=lambda p: p.name,
        )

        excess_count = len(files) - keep
        for old_file in files[: max(0, excess_count)]:
            try:
                old_file.unlink()
            except FileNotFoundError:
                pass


def create_default_logger_config(filepath: str) -> Path:
    config_filepath = Path(filepath)
    if not config_filepath.parent.exists():
        config_filepath.parent.mkdir(exist_ok=True, parents=True)

    config_filepath.write_text(LOGGING_TEMPLATE)
    return config_filepath


LOGGING_TEMPLATE = """[logging]
version = 1
disable_existing_loggers = true

[logging.formatters.json]
class = "mrml_common.JSONFormatter"
tz = "Asia/Seoul"
datefmt = "%Y-%m-%dT%H:%M:%S%z"

[logging.formatters.logfmt]
class = "mrml_common.LogfmtFormatter"
tz = "Asia/Seoul"
datefmt = "%Y-%m-%dT%H:%M:%S%z"

[logging.handlers.console]
class = "logging.StreamHandler"
level = "DEBUG"
formatter = "json"
stream = "ext://sys.stdout"

[logging.handlers.file]
class = "mrml_common.CompressedTimedRotatingFileHandler"
level = "DEBUG"
formatter = "json"
filename = "./logs/simulator.log"
maxBytes = 10485760
backupCount = 5
encoding = "utf-8"

# Child Loggers
[logging.loggers."uvicorn"]
level = "INFO"
handlers = ["console"]
propagate = false

[logging.loggers."uvicorn.error"]
level = "INFO"
handlers = ["console"]
propagate = false

[logging.loggers."uvicorn.access"]
level = "INFO"
handlers = ["console"]
propagate = false

[logging.loggers.simulator]
level = "INFO"
handlers = ["console", "file"]
propagate = false

# Root Logger
[logging.root]
level = "INFO"
handlers = ["console"]
"""
