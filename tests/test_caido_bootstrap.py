"""Regression tests for dead-container handling during Caido bootstrap."""

from __future__ import annotations

from binarypilot.runtime import caido_bootstrap


def _chained_transport_error(message: str) -> Exception:
    """Build the exception chain docker-py produces for a 409 on exec."""
    try:
        try:
            raise RuntimeError(message)
        except RuntimeError as api_err:
            raise OSError("exec transport error") from api_err
    except OSError as wrapped:
        return wrapped


def test_is_container_dead_detects_409_not_running() -> None:
    # Exact phrase from the observed docker 409:
    # 'container 9432b...be5b is not running' wrapped by the SDK.
    err = _chained_transport_error('container 9432b is not running')
    assert caido_bootstrap._is_container_dead(err) is True


def test_is_container_dead_ignores_other_transport_errors() -> None:
    err = _chained_transport_error("connection reset by peer")
    assert caido_bootstrap._is_container_dead(err) is False


def test_is_container_dead_handles_bare_error() -> None:
    err = RuntimeError("plain error, no chain")
    assert caido_bootstrap._is_container_dead(err) is False
