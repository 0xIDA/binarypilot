"""Machine branch of ``_format_ctf_challenge_line`` — mandated solve phases."""

from __future__ import annotations

from typing import Any

from binarypilot.core.inputs import _format_ctf_challenge_line


def _details(kind: str, **extra: Any) -> dict[str, Any]:
    base: dict[str, Any] = {"platform": "htb", "kind": kind, "name": "Lame", "machine_id": 1}
    base.update(extra)
    return base


def test_machine_line_mandates_spawn_and_dual_flags() -> None:
    line = _format_ctf_challenge_line(_details("machine"))
    assert "htb_spawn_machine(machine_id)" in line
    assert "user.txt" in line
    assert "root.txt" in line
    assert "privilege escalation" in line
    assert "flag_type='user'" in line
    assert "flag_type='root'" in line
    assert "htb_stop_machine" in line


def test_machine_line_keeps_vpn_product_guidance() -> None:
    line = _format_ctf_challenge_line(_details("machine"))
    assert "BINARYPILOT_VPN_PROFILE" in line
    assert "HTB_VPN_OVPN" in line
    assert "NOT interchangeable" in line


def test_machine_line_documents_bare_hex_flag_shape() -> None:
    line = _format_ctf_challenge_line(_details("machine"))
    assert "32-hex" in line
    assert "HTB{" in line


def test_starting_point_uses_machine_flow_too() -> None:
    line = _format_ctf_challenge_line(_details("starting-point"))
    assert "htb_spawn_machine" in line
    assert "starting-point" in line  # names its own VPN product


def test_sherlock_keeps_generic_vpn_hint_without_machine_phases() -> None:
    line = _format_ctf_challenge_line(_details("sherlock", sherlock_id=7))
    assert "HTB_VPN_OVPN" in line
    assert "htb_spawn_machine" not in line
    assert "root.txt" not in line


def test_challenge_line_has_no_machine_flow() -> None:
    line = _format_ctf_challenge_line(
        {
            "platform": "flagyard",
            "kind": "challenge",
            "name": "Web 01",
            "lab_id": 12,
            "challenge_id": "abc",
        }
    )
    assert "Phases in strict order" in line
    assert "htb_spawn_machine" not in line
