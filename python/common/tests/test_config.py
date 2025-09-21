from unittest import mock

from mrml_common.config import setup_logger


def make_toml_config(tmp_path):
    log_dir = tmp_path / "tmp"
    log_dir.mkdir(exist_ok=True)
    toml_content = f"""
version = 1
disable_existing_loggers = true

[formatters.json]
class = "simulator.JSONFormatter"

[handlers.console]
class = "logging.StreamHandler"
level = "DEBUG"
formatter = "json"
stream = "ext://sys.stdout"

[handlers.file]
class = "logging.handlers.RotatingFileHandler"
level = "INFO"
formatter = "json"
filename = "{log_dir / "simulator.log"}"
maxBytes = 10485760
backupCount = 5
encoding = "utf-8"

[loggers."uvicorn"]
level = "INFO"
handlers = ["console"]
propagate = false

[loggers."uvicorn.error"]
level = "INFO"
handlers = ["console"]
propagate = false

[loggers."uvicorn.access"]
level = "INFO"
handlers = ["console"]
propagate = false

[loggers.simulator]
level = "INFO"
handlers = ["console", "file"]
propagate = false

[root]
level = "INFO"
handlers = ["console"]
"""
    toml_path = tmp_path / "logger.toml"
    with open(toml_path, "w") as f:
        f.write(toml_content)
    return toml_path, log_dir


def test_setup_logger_with_config(tmp_path):
    toml_path, log_dir = make_toml_config(tmp_path)
    with mock.patch("logging.config.dictConfig") as mock_dictConfig:
        setup_logger(str(toml_path))
        # Log file directory should be created
        assert log_dir.exists() and log_dir.is_dir()
        # dictConfig should be called
        mock_dictConfig.assert_called()
