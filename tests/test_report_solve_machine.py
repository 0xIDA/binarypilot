"""report_solve machine metadata — kind/flag_type land in solves.json and writeups."""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

import pytest
from agents.tool_context import ToolContext

from binarypilot.report.state import ReportState, set_global_report_state
from binarypilot.report.writer import render_solve_md
from binarypilot.tools.finish.tool import report_solve


if TYPE_CHECKING:
    from pathlib import Path


async def _call_report_solve(**overrides: object) -> dict[str, object]:
    args: dict[str, object] = {
        "title": "Lame — user flag",
        "challenge": "Lame",
        "platform": "htb",
        "flag": "0" * 32,
        "writeup": "Samba 3.0.20 username map script command injection.",
        "poc": "python3 exploit.py",
        "poc_language": "bash",
    }
    args.update(overrides)
    ctx = ToolContext(
        context={},
        tool_name="report_solve",
        tool_call_id="call-1",
        tool_arguments="{}",
    )
    raw = await report_solve.on_invoke_tool(ctx, json.dumps(args))
    return json.loads(raw)  # type: ignore[no-any-return]


@pytest.fixture
def report_state(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> ReportState:
    monkeypatch.chdir(tmp_path)
    state = ReportState(run_name="machine-run")
    set_global_report_state(state)
    return state


async def test_machine_solve_records_kind_and_flag_type(report_state: ReportState) -> None:
    result = await _call_report_solve(kind="machine", flag_type="user")
    assert result["success"] is True
    solve = report_state.solves[0]
    assert solve["kind"] == "machine"
    assert solve["flag_type"] == "user"


async def test_challenge_solve_omits_machine_fields(report_state: ReportState) -> None:
    """Default shape unchanged — old solves must not grow new keys."""
    await _call_report_solve()
    solve = report_state.solves[0]
    assert "kind" not in solve
    assert "flag_type" not in solve


async def test_invalid_kind_rejected(report_state: ReportState) -> None:
    result = await _call_report_solve(kind="fortress")
    assert result["success"] is False
    assert "kind" in str(result["error"])
    assert report_state.solves == []


async def test_invalid_flag_type_rejected(report_state: ReportState) -> None:
    result = await _call_report_solve(kind="machine", flag_type="admin")
    assert result["success"] is False
    assert "flag_type" in str(result["error"])
    assert report_state.solves == []


def test_render_solve_md_labels_machine_flags() -> None:
    md = render_solve_md(
        {
            "id": "solve-0001",
            "title": "Lame — root flag",
            "challenge": "Lame",
            "platform": "htb",
            "flag": "1" * 32,
            "writeup": "privesc via samba",
            "timestamp": "2026-08-16 00:00:00 UTC",
            "kind": "machine",
            "flag_type": "root",
        }
    )
    assert "**Kind:** HTB machine (root flag)" in md


def test_render_solve_md_plain_solve_unchanged() -> None:
    md = render_solve_md(
        {
            "id": "solve-0002",
            "title": "Web 01",
            "challenge": "Web 01",
            "platform": "flagyard",
            "flag": "FlagY{...}",
            "writeup": "idor",
            "timestamp": "2026-08-16 00:00:00 UTC",
        }
    )
    assert "**Kind:**" not in md
    assert "**Challenge:** Web 01" in md
