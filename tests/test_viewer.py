"""Tests for the local run viewer (binarypilot.interface.viewer) and its path helpers."""

from __future__ import annotations

import json
import os
import sqlite3
import urllib.error
import urllib.request
from typing import TYPE_CHECKING
from urllib.parse import urlsplit

from binarypilot.core.paths import latest_run_dir, runs_base_dir
from binarypilot.interface.viewer.server import serve
from binarypilot.interface.viewer.transcript import (
    build_run_state,
    read_findings,
    read_report_markdown,
    read_run_summary,
)


if TYPE_CHECKING:
    from collections.abc import Mapping
    from pathlib import Path

    import pytest


def _make_run(base: Path, name: str, *, status: str, end_time: str | None) -> Path:
    run_dir = base / "binarypilot_runs" / name
    state_dir = run_dir / ".state"
    state_dir.mkdir(parents=True)
    record = {"run_name": name, "status": status, "end_time": end_time}
    (run_dir / "run.json").write_text(json.dumps(record), encoding="utf-8")
    agents = {
        "statuses": {"root": "completed", "child": "running"},
        "names": {"root": "binarypilot", "child": "recon"},
        "parent_of": {"root": None, "child": "root"},
    }
    (state_dir / "agents.json").write_text(json.dumps(agents), encoding="utf-8")
    return run_dir


def test_latest_run_dir_none_when_no_runs(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(tmp_path)
    assert latest_run_dir() is None
    assert runs_base_dir() == tmp_path / "binarypilot_runs"


def test_latest_run_dir_picks_newest_by_record_mtime(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(tmp_path)
    older = _make_run(tmp_path, "old", status="completed", end_time="2026-01-01T00:00:00Z")
    newer = _make_run(tmp_path, "new", status="running", end_time=None)
    # Force a newer mtime on the second run's record.
    os.utime(newer / "run.json", (2_000_000_000, 2_000_000_000))
    os.utime(older / "run.json", (1_000_000_000, 1_000_000_000))
    assert latest_run_dir() == newer


def test_read_run_summary_finished_flag(tmp_path: Path) -> None:
    finished = _make_run(tmp_path, "done", status="completed", end_time="2026-01-01T00:00:00Z")
    live = _make_run(tmp_path, "live", status="running", end_time=None)
    assert read_run_summary(finished)["finished"] is True
    assert read_run_summary(live)["finished"] is False
    # A terminal status without an end_time is not "finished".
    partial = _make_run(tmp_path, "partial", status="failed", end_time=None)
    assert read_run_summary(partial)["finished"] is False


def test_read_missing_artifacts_return_defaults(tmp_path: Path) -> None:
    run_dir = _make_run(tmp_path, "empty", status="running", end_time=None)
    assert read_findings(run_dir) == []
    assert read_report_markdown(run_dir) == ""


def test_read_findings_prefers_solves_over_vulnerabilities(tmp_path: Path) -> None:
    """CTF runs write solves.json instead of vulnerabilities.json; the findings
    endpoint maps each solve into a vulnerability-shaped record so the existing
    frontend renders it without code changes."""
    run_dir = _make_run(tmp_path, "ctf", status="completed", end_time="2026-01-01T00:10:00Z")
    solves = [
        {
            "id": "solve-0001",
            "title": "FlagYard Beginner Web 01 — IDOR",
            "challenge": "Beginner Web 01",
            "platform": "flagyard",
            "flag": "FlagY{abc123}",
            "writeup": (
                "1. Enum'd /api/users/<id>. 2. numeric id guesses other users."
                " 3. /api/users/1 is admin."
            ),
            "poc": "#!/usr/bin/env bash\nexec curl -s https://inst/api/users/1",
            "poc_language": "bash",
            "timestamp": "2026-01-01 00:10:00 UTC",
        }
    ]
    (run_dir / "solves.json").write_text(json.dumps(solves), encoding="utf-8")

    findings = read_findings(run_dir)
    assert len(findings) == 1
    f = findings[0]
    assert f["id"] == "solve-0001"
    assert f["title"] == "FlagYard Beginner Web 01 — IDOR"
    assert f["severity"] == "low"  # CTF has no severity palette; fold to low
    assert f["target"] == "Beginner Web 01"
    assert f["technical_analysis"] == solves[0]["writeup"]
    assert f["poc_script_code"] == solves[0]["poc"]
    assert f["platform"] == "flagyard"
    assert f["flag"] == "FlagY{abc123}"


def test_read_findings_passes_through_vulnerabilities_first(tmp_path: Path) -> None:
    """If a run happens to have both files (e.g. mixed workflow), the finding
    list prefers the explicit vulnerability records over solve mappings."""
    run_dir = _make_run(tmp_path, "mixed", status="completed", end_time="2026-01-01T00:10:00Z")
    (run_dir / "vulnerabilities.json").write_text(
        json.dumps([{"id": "vuln-0001", "title": "SQLi", "severity": "high"}]),
        encoding="utf-8",
    )
    (run_dir / "solves.json").write_text(
        json.dumps(
            [
                {
                    "id": "solve-0001",
                    "title": "ignored",
                    "challenge": "x",
                    "platform": "flagyard",
                    "flag": "F{}",
                    "writeup": "w",
                }
            ]
        ),
        encoding="utf-8",
    )

    findings = read_findings(run_dir)
    assert [r["id"] for r in findings] == ["vuln-0001"]


def test_build_run_state_from_agents_json(tmp_path: Path) -> None:
    run_dir = _make_run(tmp_path, "graph", status="running", end_time=None)
    state = build_run_state(run_dir)
    ids = {a["id"] for a in state["agents"]}
    assert ids == {"root", "child"}
    child = next(a for a in state["agents"] if a["id"] == "child")
    assert child["parent_id"] == "root"
    assert child["name"] == "recon"
    # No agents.db, so no message/tool events.
    assert state["events"] == []


def test_build_run_state_keeps_same_call_id_separate_per_agent(tmp_path: Path) -> None:
    run_dir = _make_run(tmp_path, "tools", status="completed", end_time=None)
    agents_db = run_dir / ".state" / "agents.db"
    rows = [
        (
            "root",
            {
                "type": "function_call",
                "call_id": "exec_command_0",
                "name": "exec_command",
                "arguments": json.dumps({"cmd": "echo root"}),
            },
        ),
        (
            "root",
            {
                "type": "function_call_output",
                "call_id": "exec_command_0",
                "output": json.dumps({"success": True, "output": "root"}),
            },
        ),
        (
            "child",
            {
                "type": "function_call",
                "call_id": "exec_command_0",
                "name": "exec_command",
                "arguments": json.dumps({"cmd": "echo child"}),
            },
        ),
        (
            "child",
            {
                "type": "function_call_output",
                "call_id": "exec_command_0",
                "output": json.dumps({"success": True, "output": "child"}),
            },
        ),
    ]
    with sqlite3.connect(agents_db) as conn:
        conn.execute(
            """
            create table agent_messages (
                id integer primary key,
                session_id text not null,
                message_data text not null,
                created_at text not null
            )
            """
        )
        conn.executemany(
            """
            insert into agent_messages (session_id, message_data, created_at)
            values (?, ?, '2026-01-01T00:00:00+00:00')
            """,
            [(agent_id, json.dumps(message)) for agent_id, message in rows],
        )

    state = build_run_state(run_dir)
    tools = [event for event in state["events"] if event["type"] == "tool"]

    assert len(tools) == 2
    by_agent = {event["agent_id"]: event for event in tools}
    assert by_agent["root"]["data"]["args"] == {"cmd": "echo root"}
    assert by_agent["root"]["data"]["result"]["output"] == "root"
    assert by_agent["child"]["data"]["args"] == {"cmd": "echo child"}
    assert by_agent["child"]["data"]["result"]["output"] == "child"


def _get(url: str, *, cookie: str | None = None) -> tuple[int, str, bytes]:
    headers = {"Cookie": cookie} if cookie else {}
    req = urllib.request.Request(url, headers=headers)  # noqa: S310 - localhost test server
    with urllib.request.urlopen(req) as resp:  # noqa: S310 - localhost test server  # nosec B310
        return resp.status, resp.headers.get("Content-Type", ""), resp.read()


def test_server_serves_api_and_static(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    run_dir = _make_run(tmp_path, "served", status="completed", end_time="2026-01-01T00:00:00Z")

    assets = tmp_path / "bundle"
    (assets / "assets").mkdir(parents=True)
    (assets / "index.html").write_text("<!doctype html><div id=root></div>", encoding="utf-8")
    (assets / "assets" / "app.js").write_text("console.log(1)", encoding="utf-8")
    monkeypatch.setattr("binarypilot.interface.viewer.server.bundle_dir", lambda: assets)

    httpd, url, _ = serve(run_dir, open_browser=False)
    try:
        status, ctype, body = _get(f"{url}/api/run")
        assert status == 200
        assert "application/json" in ctype
        assert json.loads(body)["finished"] is True

        status, _, body = _get(f"{url}/api/transcript")
        assert {a["id"] for a in json.loads(body)["agents"]} == {"root", "child"}

        # Real asset is served.
        status, ctype, _ = _get(f"{url}/assets/app.js")
        assert status == 200

        # Unknown non-API route falls back to index.html (SPA routing).
        status, ctype, body = _get(f"{url}/agents/root")
        assert status == 200
        assert b"<div id=root>" in body
    finally:
        httpd.shutdown()
        httpd.server_close()


def test_server_event_endpoint_forwards_cta(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    run_dir = _make_run(tmp_path, "evt", status="running", end_time=None)
    assets = tmp_path / "bundle"
    assets.mkdir()
    (assets / "index.html").write_text("x", encoding="utf-8")
    monkeypatch.setattr("binarypilot.interface.viewer.server.bundle_dir", lambda: assets)

    seen: list[tuple[str, str | None]] = []
    monkeypatch.setattr(
        "binarypilot.telemetry.posthog.viewer_cta_clicked",
        lambda cta, surface=None: seen.append((cta, surface)),
    )

    httpd, url, _ = serve(run_dir, open_browser=False)
    try:
        body = json.dumps(
            {"event": "cta_clicked", "cta": "PR reviews", "surface": "sidebar_nav"}
        ).encode()
        req = urllib.request.Request(  # noqa: S310 - localhost test server
            f"{url}/api/event", data=body, headers={"Content-Type": "application/json"}
        )
        with urllib.request.urlopen(req) as resp:  # noqa: S310  # nosec B310
            assert resp.status == 204
        assert seen == [("PR reviews", "sidebar_nav")]
    finally:
        httpd.shutdown()
        httpd.server_close()


def test_server_event_endpoint_forwards_agent_steered(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    run_dir = _make_run(tmp_path, "steerevt", status="running", end_time=None)
    _bundle(tmp_path, monkeypatch)

    seen: list[bool] = []
    monkeypatch.setattr(
        "binarypilot.telemetry.posthog.viewer_agent_steered", lambda: seen.append(True)
    )

    httpd, url, _ = serve(run_dir, open_browser=False)
    try:
        req = urllib.request.Request(  # noqa: S310 - localhost test server
            f"{url}/api/event",
            data=json.dumps({"event": "agent_steered"}).encode(),
            headers={"Content-Type": "application/json"},
        )
        with urllib.request.urlopen(req) as resp:  # noqa: S310  # nosec B310
            assert resp.status == 204
        assert seen == [True]
    finally:
        httpd.shutdown()
        httpd.server_close()


def _post(
    url: str, path: str, payload: Mapping[str, object], *, cookie: str | None = None
) -> tuple[int, bytes]:
    headers = {"Content-Type": "application/json"}
    if cookie:
        headers["Cookie"] = cookie
    req = urllib.request.Request(  # noqa: S310 - localhost test server
        url + path, data=json.dumps(payload).encode(), headers=headers, method="POST"
    )
    try:
        with urllib.request.urlopen(req) as resp:  # noqa: S310  # nosec B310
            return resp.status, resp.read()
    except urllib.error.HTTPError as exc:
        return exc.code, exc.read()


def _session_cookie(url: str, token: str) -> str:
    """Bootstrap a session via the tokened URL and return its ``name=value`` cookie."""
    bootstrap = f"{url}/?token={token}"
    with urllib.request.urlopen(bootstrap) as resp:  # noqa: S310 - localhost test server  # nosec B310
        raw = str(resp.headers.get("Set-Cookie", ""))
    return raw.split(";", 1)[0]


def _cookie_name(url: str) -> str:
    """The per-server session cookie name, derived from the bound port."""
    return f"binarypilot_viewer_session_{urlsplit(url).port}"


def _get_status(url: str, *, cookie: str | None = None) -> int:
    headers = {"Cookie": cookie} if cookie else {}
    req = urllib.request.Request(url, headers=headers)  # noqa: S310 - localhost test server
    try:
        with urllib.request.urlopen(req) as resp:  # noqa: S310  # nosec B310
            return int(resp.status)
    except urllib.error.HTTPError as exc:
        return int(exc.code)


def _bundle(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    assets = tmp_path / "bundle"
    assets.mkdir()
    (assets / "index.html").write_text("<!doctype html><div id=root></div>", encoding="utf-8")
    monkeypatch.setattr("binarypilot.interface.viewer.server.bundle_dir", lambda: assets)


def test_capability_issued_only_for_tokened_bootstrap(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    run_dir = _make_run(tmp_path, "cookie", status="running", end_time=None)
    assets = tmp_path / "bundle"
    (assets / "assets").mkdir(parents=True)
    (assets / "index.html").write_text("<!doctype html>index", encoding="utf-8")
    (assets / "assets" / "app.js").write_text("1", encoding="utf-8")
    monkeypatch.setattr("binarypilot.interface.viewer.server.bundle_dir", lambda: assets)

    httpd, url, token = serve(run_dir, open_browser=False)
    try:
        # A bare index load -- all a reachable client can do -- hands out nothing.
        with urllib.request.urlopen(url + "/") as resp:  # noqa: S310  # nosec B310
            assert resp.headers.get("Set-Cookie") is None

        # A wrong token is likewise refused the capability.
        with urllib.request.urlopen(f"{url}/?token=wrong") as resp:  # noqa: S310  # nosec B310
            assert resp.headers.get("Set-Cookie") is None

        # Only the correct bootstrap token mints the session cookie.
        with urllib.request.urlopen(f"{url}/?token={token}") as resp:  # noqa: S310  # nosec B310
            cookie = str(resp.headers.get("Set-Cookie", ""))
        assert f"{_cookie_name(url)}=" in cookie
        assert "HttpOnly" in cookie and "SameSite=Strict" in cookie

        # Static assets never carry it.
        with urllib.request.urlopen(url + "/assets/app.js") as resp:  # noqa: S310  # nosec B310
            assert resp.headers.get("Set-Cookie") is None
    finally:
        httpd.shutdown()
        httpd.server_close()


def test_unauthorized_client_cannot_acquire_capability(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    run_dir = _make_run(tmp_path, "exposed", status="running", end_time=None)
    _bundle(tmp_path, monkeypatch)

    delivered: list[tuple[str, str]] = []

    def handler(agent_id: str, message: str) -> bool:
        delivered.append((agent_id, message))
        return True

    httpd, url, _ = serve(run_dir, open_browser=False, steer_handler=handler)
    try:
        # A direct network client can reach the page but is handed no capability,
        # so replaying an empty/guessed cookie cannot steer a live scan.
        with urllib.request.urlopen(url + "/") as resp:  # noqa: S310  # nosec B310
            assert resp.headers.get("Set-Cookie") is None
        status, _ = _post(
            url,
            "/api/agents/steer",
            {"agent_id": "root", "message": "pwn"},
            cookie=f"{_cookie_name(url)}=",
        )
        assert status == 403
        assert delivered == []
    finally:
        httpd.shutdown()
        httpd.server_close()


def test_steer_requires_session_cookie(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    run_dir = _make_run(tmp_path, "steer", status="running", end_time=None)
    _bundle(tmp_path, monkeypatch)

    delivered: list[tuple[str, str]] = []

    def handler(agent_id: str, message: str) -> bool:
        delivered.append((agent_id, message))
        return True

    httpd, url, token = serve(run_dir, open_browser=False, steer_handler=handler)
    try:
        body = {"agent_id": "root", "message": "focus on auth"}
        # No cookie: rejected before reaching the live coordinator.
        status, _ = _post(url, "/api/agents/steer", body)
        assert status == 403
        assert delivered == []

        # With the session cookie the message is delivered.
        status, raw = _post(url, "/api/agents/steer", body, cookie=_session_cookie(url, token))
        assert status == 200
        assert json.loads(raw)["ok"] is True
        assert delivered == [("root", "focus on auth")]
    finally:
        httpd.shutdown()
        httpd.server_close()


def test_concurrent_servers_use_distinct_cookies(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Cookies are host-scoped, not port-scoped: two viewers on 127.0.0.1 must
    not share a cookie slot, and one server's cookie must not pass the other's
    session gate."""
    run_a = _make_run(tmp_path / "a", "run-a", status="running", end_time=None)
    run_b = _make_run(tmp_path / "b", "run-b", status="running", end_time=None)
    _bundle(tmp_path, monkeypatch)

    httpd_a, url_a, token_a = serve(run_a, open_browser=False)
    httpd_b, url_b, token_b = serve(run_b, open_browser=False)
    try:
        cookie_a = _session_cookie(url_a, token_a)
        cookie_b = _session_cookie(url_b, token_b)

        # The two servers mint differently named cookies, so a browser stores both.
        assert cookie_a.split("=", 1)[0] == _cookie_name(url_a)
        assert cookie_b.split("=", 1)[0] == _cookie_name(url_b)
        assert cookie_a.split("=", 1)[0] != cookie_b.split("=", 1)[0]

        def _steer_status(url: str, cookie: str) -> int:
            # The session-gated POST endpoint behaves as the gate probe: a
            # matching cookie gets past the 403 check (and lands at 400 on the
            # body validation), a foreign cookie gets 403.
            req = urllib.request.Request(  # noqa: S310 - localhost test server
                f"{url}/api/agents/steer",
                data=b"{}",
                headers={"Content-Type": "application/json", "Cookie": cookie},
            )
            try:
                with urllib.request.urlopen(req) as resp:  # noqa: S310  # nosec B310  # local viewer URL, controlled by the test
                    return resp.status
            except urllib.error.HTTPError as e:
                return e.code

        # Each server honors its own cookie (400 = past the session gate)...
        assert _steer_status(url_a, cookie_a) == 400
        assert _steer_status(url_b, cookie_b) == 400
        # ...but treats the other server's cookie as session-less (403).
        assert _steer_status(url_a, cookie_b) == 403
        assert _steer_status(url_b, cookie_a) == 403
        # Both cookies together (what a real browser would send) still match
        # the token minted by the receiving server only.
        both = f"{cookie_a}; {cookie_b}"
        assert _steer_status(url_a, both) == 400
        assert _steer_status(url_b, both) == 400
    finally:
        httpd_a.shutdown()
        httpd_a.server_close()
        httpd_b.shutdown()
        httpd_b.server_close()


def test_server_rejects_path_traversal(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    run_dir = _make_run(tmp_path, "guard", status="completed", end_time="2026-01-01T00:00:00Z")
    secret = tmp_path / "secret.txt"
    secret.write_text("top secret", encoding="utf-8")

    assets = tmp_path / "bundle"
    assets.mkdir()
    (assets / "index.html").write_text("<!doctype html>index", encoding="utf-8")
    monkeypatch.setattr("binarypilot.interface.viewer.server.bundle_dir", lambda: assets)

    httpd, url, _ = serve(run_dir, open_browser=False)
    try:
        # A traversal target must never leak the file; it falls back to index.html.
        _, _, body = _get(f"{url}/..%2f..%2fsecret.txt")
        assert b"top secret" not in body
    finally:
        httpd.shutdown()
        httpd.server_close()
