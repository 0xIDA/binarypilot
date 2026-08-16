"""_apply_vpn_support() — wires HTB OpenVPN profile into the sandbox container.

Regression: v1.5.0 shipped ``extra_hosts.setdefault("vpn.binarypilot.internal", p.stem)``
where ``p.stem`` was the profile filename stem (e.g. ``release_arena_eu-release-1``).
Docker rejects add-host entries whose right-hand side is not an IP; failure at create:

    docker.errors.APIError: 400 Client Error ... invalid IP address in add-host.

The fix deletes the extra_hosts entry entirely; the profile filename is not a hostname
we ever need to resolve. mounts + env + /dev/net/tun + NET_ADMIN is all the VPN stack
needs.
"""

from __future__ import annotations

import os
from pathlib import Path  # noqa: TC003  # used at runtime in _mkprofile
from typing import TYPE_CHECKING, Any
from unittest.mock import patch

from binarypilot.runtime.docker_client import _apply_vpn_support


if TYPE_CHECKING:
    import pytest


def _mkprofile(tmp_path: Path, name: str = "release_arena_eu-release-1.ovpn") -> Path:
    prof = tmp_path / name
    prof.write_text("client\ndev tun\n")
    return prof


def test_vpn_wires_mount_env_device_and_caps(tmp_path: Path) -> None:
    profile = _mkprofile(tmp_path)
    with patch.dict(os.environ, {"HTB_VPN_OVPN": str(profile)}):
        kwargs: dict[str, Any] = {}
        _apply_vpn_support(kwargs)

    assert kwargs["mounts"] == [
        {
            "type": "bind",
            "source": str(profile),
            "target": f"/vpn/{profile.name}",
            "read_only": True,
        }
    ]
    assert kwargs["environment"]["BINARYPILOT_VPN_PROFILE"] == f"/vpn/{profile.name}"
    assert "/dev/net/tun:/dev/net/tun" in kwargs["devices"]
    assert "NET_ADMIN" in kwargs["cap_add"]


def test_vpn_does_not_add_extra_hosts(tmp_path: Path) -> None:
    """Regression: p.stem ('release_arena_eu-release-1') is not an IP; docker rejects."""
    profile = _mkprofile(tmp_path)
    with patch.dict(os.environ, {"HTB_VPN_OVPN": str(profile)}):
        kwargs: dict[str, Any] = {}
        _apply_vpn_support(kwargs)

    hosts = kwargs.get("extra_hosts", {})
    assert "vpn.binarypilot.internal" not in hosts


def test_vpn_noop_when_env_unset(monkeypatch: pytest.MonkeyPatch) -> None:
    # Fresh default settings too — the memoized cache may predate this test's
    # env clearing, and the user's own cli-config.json must not leak in.
    from binarypilot.config.settings import Settings  # noqa: PLC0415

    monkeypatch.setattr("binarypilot.config.load_settings", Settings)
    with patch.dict(os.environ, {}, clear=True):
        kwargs: dict[str, Any] = {}
        _apply_vpn_support(kwargs)
    assert kwargs == {}


def test_vpn_noop_when_profile_missing(tmp_path: Path) -> None:
    with patch.dict(os.environ, {"HTB_VPN_OVPN": str(tmp_path / "nope.ovpn")}):
        kwargs: dict[str, Any] = {}
        _apply_vpn_support(kwargs)
    assert kwargs == {}


def test_vpn_wires_from_settings_not_just_env(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """HTB_VPN_OVPN is a first-class setting: a profile from cli-config.json
    (not present in the process env) must still wire the mount."""
    profile = _mkprofile(tmp_path)
    from binarypilot.config.settings import PlatformSettings, Settings  # noqa: PLC0415

    settings = Settings(platforms=PlatformSettings(htb_vpn_ovpn=str(profile)))
    monkeypatch.setattr("binarypilot.config.load_settings", lambda: settings)
    with patch.dict(os.environ, {}, clear=True):
        kwargs: dict[str, Any] = {}
        _apply_vpn_support(kwargs)

    assert kwargs["mounts"] == [
        {
            "type": "bind",
            "source": str(profile),
            "target": f"/vpn/{profile.name}",
            "read_only": True,
        }
    ]
    assert kwargs["environment"]["BINARYPILOT_VPN_PROFILE"] == f"/vpn/{profile.name}"
    assert "/dev/net/tun:/dev/net/tun" in kwargs["devices"]
    assert "NET_ADMIN" in kwargs["cap_add"]
