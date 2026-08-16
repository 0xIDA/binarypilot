"""HTB machine tools — flag validation, submit payloads, spawn/stop/reset lifecycle.

Regression: ``htb_submit_machine_flag`` used to require the ``HTB{`` prefix,
which rejected every regular-machine flag (user.txt/root.txt are bare 32-hex
MD5-style hashes) before the API was ever called.

Spawn/reset IP polling is verified against captured HTB web-UI traffic:
GET /api/v5/virtual_machine/active is the authoritative source for the
assigned IP (``info.ip`` is null while ``isSpawning`` is true) and carries
``expires_at`` / ``vpn_server_type``.
"""

from __future__ import annotations

import json
from typing import TYPE_CHECKING, Any

from agents.tool_context import ToolContext

from binarypilot.tools.htb import tool as htb


if TYPE_CHECKING:
    import pytest


class _FakeClient:
    def __init__(
        self,
        *,
        active_machine: dict[str, Any] | None = None,
    ) -> None:
        self.calls: list[dict[str, Any]] = []
        self._active = active_machine

    def request(  # signature mirrors the real client for duck-typing
        self,
        method: str,
        path: str,
        *,
        params: dict[str, Any] | None = None,  # noqa: ARG002
        json_body: Any = None,
        v5: bool = False,
        timeout: int = 60,  # noqa: ARG002
    ) -> Any:
        self.calls.append({"method": method, "path": path, "json_body": json_body, "v5": v5})
        if path == "/virtual_machine/active":
            return {"info": self._active} if self._active else {"info": None}
        return {"isSuccess": True}


def _ctx() -> ToolContext:
    return ToolContext(
        context={},
        tool_name="htb",
        tool_call_id="call-1",
        tool_arguments="{}",
    )


async def _invoke(
    tool: Any, fake: _FakeClient, monkeypatch: pytest.MonkeyPatch, **args: Any
) -> dict[str, Any]:
    monkeypatch.setattr(htb, "client", lambda: fake)
    raw = await tool.on_invoke_tool(_ctx(), json.dumps(args))
    return json.loads(raw)  # type: ignore[no-any-return]


async def test_machine_flag_accepts_bare_hex(monkeypatch: pytest.MonkeyPatch) -> None:
    """Regular machines put bare MD5-style hashes in user.txt/root.txt."""
    fake = _FakeClient()
    flag = "0f2a" + "b" * 28  # 32 hex chars
    result = await _invoke(htb.htb_submit_machine_flag, fake, monkeypatch, machine_id=42, flag=flag)
    assert result == {"isSuccess": True}
    assert fake.calls == [
        {
            "method": "POST",
            "path": "/machine/own",
            "json_body": {"id": 42, "flag": flag},
            "v5": True,
        }
    ]


async def test_machine_flag_accepts_htb_wrapper(monkeypatch: pytest.MonkeyPatch) -> None:
    """Products like starting-point use HTB{...} machine flags."""
    fake = _FakeClient()
    result = await _invoke(
        htb.htb_submit_machine_flag,
        fake,
        monkeypatch,
        machine_id=7,
        flag="HTB{starting_point_style}",
    )
    assert result == {"isSuccess": True}
    assert fake.calls[0]["json_body"] == {"id": 7, "flag": "HTB{starting_point_style}"}


async def test_machine_flag_strips_whitespace(monkeypatch: pytest.MonkeyPatch) -> None:
    """Flags arrive with trailing newlines from cat/su output; strip before submit."""
    fake = _FakeClient()
    flag = "c" * 32
    await _invoke(htb.htb_submit_machine_flag, fake, monkeypatch, machine_id=1, flag=f"  {flag}\n")
    assert fake.calls[0]["json_body"] == {"id": 1, "flag": flag}


async def test_machine_flag_rejects_garbage(monkeypatch: pytest.MonkeyPatch) -> None:
    """Neither hex nor HTB{} — reject locally, never call the API."""
    fake = _FakeClient()
    # 32 chars, but not hex
    for bad in ("not-a-flag", "zzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzz"):
        result = await _invoke(
            htb.htb_submit_machine_flag, fake, monkeypatch, machine_id=1, flag=bad
        )
        assert result["isSuccess"] is False
        assert "error" in result
    assert fake.calls == []


async def test_stop_machine_posts_vm_terminate(monkeypatch: pytest.MonkeyPatch) -> None:
    fake = _FakeClient()
    result = await _invoke(htb.htb_stop_machine, fake, monkeypatch, machine_id=42)
    assert result == {"isSuccess": True}
    assert fake.calls == [
        {
            "method": "POST",
            "path": "/vm/terminate",
            "json_body": {"machine_id": 42},
            "v5": True,
        }
    ]


async def test_spawn_polls_v5_active_for_ip(monkeypatch: pytest.MonkeyPatch) -> None:
    """The UI polls /v5/virtual_machine/active for the assigned IP — so do we."""
    fake = _FakeClient(
        active_machine={
            "id": 933,
            "name": "Cohort",
            "ip": "10.129.244.174",
            "isSpawning": False,
            "expires_at": "2026-08-16 13:22:26",
            "vpn_server_type": "Machines",
        }
    )
    result = await _invoke(htb.htb_spawn_machine, fake, monkeypatch, machine_id=933, wait_seconds=0)
    assert result["machine"]["ip"] == "10.129.244.174"
    assert fake.calls[0] == {
        "method": "POST",
        "path": "/vm/spawn",
        "json_body": {"machine_id": 933},
        "v5": True,
    }
    poll = [c for c in fake.calls[1:] if c["path"] == "/virtual_machine/active"]
    assert poll and all(c["v5"] for c in poll)
    assert "warning" not in result


async def test_spawn_warns_when_other_machine_active(monkeypatch: pytest.MonkeyPatch) -> None:
    """One active machine per user — spawning while another runs must surface it."""
    fake = _FakeClient(active_machine={"id": 1, "name": "Lame", "ip": "10.10.10.5"})
    result = await _invoke(htb.htb_spawn_machine, fake, monkeypatch, machine_id=933, wait_seconds=0)
    assert result["warning"]
    assert "Lame" in result["warning"]
    assert result["machine"]["id"] == 1


async def test_reset_machine_posts_vm_reset_and_repolls_ip(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fake = _FakeClient(active_machine={"id": 42, "name": "Anchor", "ip": "10.10.10.3"})
    result = await _invoke(htb.htb_reset_machine, fake, monkeypatch, machine_id=42, wait_seconds=0)
    assert result["machine"]["ip"] == "10.10.10.3"
    assert fake.calls[0] == {
        "method": "POST",
        "path": "/vm/reset",
        "json_body": {"machine_id": 42},
        "v5": True,
    }
    assert any(c["path"] == "/virtual_machine/active" for c in fake.calls[1:])
