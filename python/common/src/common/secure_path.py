from __future__ import annotations

import logging
from collections.abc import Callable
from pathlib import Path

from error import PathTraversalError

logger = logging.getLogger(__name__)


def secure_path(
    filepath: str | Path,
    base_dir: str | Path,
    *,
    allow_relative: bool = True,
) -> Path:
    """Resolve a secure path within a base directory."""
    try:
        base_dir = Path(base_dir).resolve(strict=True)
        logger.debug("Secure base dirpath %s", base_dir)
    except FileNotFoundError as e:
        raise PathTraversalError(f"No Base Directory: {base_dir}") from e

    attempted = Path(filepath)
    logger.debug("Attempted filepath: %s", attempted)
    resolved = (base_dir / attempted).resolve(strict=False)
    logger.debug("Resolved attempted filepath: %s", resolved)

    if (not allow_relative) and (not attempted.is_absolute()):
        raise PathTraversalError(f"Relative paths not allowed: {filepath}")

    try:
        resolved.relative_to(base_dir)
    except ValueError as e:
        raise PathTraversalError(f"Path escapes base_dir: {resolved}") from e

    return resolved


def secure_path_factory(
    base_dir: str | Path,
    *,
    allow_relative: bool = True,
) -> Callable[[str | Path], Path]:
    bound_base = base_dir
    bound_allow_relative = allow_relative

    def _secure_path(
        attempted: str | Path,
        *,
        base_dir: Path | None = None,
        allow_relative: bool | None = None,
    ) -> Path:
        base_dir = base_dir if base_dir else bound_base
        allow_relative = (
            allow_relative if allow_relative is None else bound_allow_relative
        )

        return secure_path(attempted, base_dir, allow_relative=allow_relative)

    return _secure_path
