from __future__ import annotations

import logging
import platform
import sys
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path
from typing import Any
from uuid import uuid4


logger = logging.getLogger(__name__)

SESSION_ID: str = uuid4().hex[:16]

_FIRST_RUN_CACHED: bool | None = None


def get_version() -> str:
    try:
        return version("binarypilot-agent")
    except PackageNotFoundError:
        logger.debug("binarypilot-agent version lookup failed", exc_info=True)
        return "unknown"


def is_first_run() -> bool:
    global _FIRST_RUN_CACHED  # noqa: PLW0603
    if _FIRST_RUN_CACHED is not None:
        return _FIRST_RUN_CACHED
    marker = Path.home() / ".binarypilot" / ".seen"
    if marker.exists():
        _FIRST_RUN_CACHED = False
        return False
    try:
        marker.parent.mkdir(parents=True, exist_ok=True)
        marker.touch()
    except Exception:  # noqa: BLE001, S110
        pass  # nosec B110
    _FIRST_RUN_CACHED = True
    return True


def base_props() -> dict[str, Any]:
    return {
        "os": platform.system().lower(),
        "arch": platform.machine(),
        "python": f"{sys.version_info.major}.{sys.version_info.minor}",
        "binarypilot_version": get_version(),
    }
