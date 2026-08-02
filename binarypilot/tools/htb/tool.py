"""HackTheBox platform tools — challenges, containers, downloads, flag submission.

Direct REST (https://labs.hackthebox.com/api/v4, machines' own endpoint on v5).
Bearer auth via ``HTB_TOKEN``. Endpoint paths ported from
htb-mcp-server (0xIDA/htb-mcp-server).
"""

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any

import requests
from agents import RunContextWrapper, function_tool

from binarypilot.config import load_settings


API_V4 = "https://labs.hackthebox.com/api/v4"
API_V5 = "https://labs.hackthebox.com/api/v5"


class HTBClient:
    def __init__(self) -> None:
        token = (load_settings().platforms.htb_token or "").strip()
        if not token:
            raise RuntimeError("Set HTB_TOKEN (HTB app token, JWT format)")
        self.session = requests.Session()
        self.session.headers.update(
            {
                "Authorization": f"Bearer {token}",
                "Accept": "application/json",
                "Content-Type": "application/json",
                "User-Agent": "binarypilot/1.0",
            }
        )

    def request(
        self,
        method: str,
        path: str,
        *,
        params: dict[str, Any] | None = None,
        json_body: Any = None,
        v5: bool = False,
        timeout: int = 60,
    ) -> Any:
        base = API_V5 if v5 else API_V4
        r = self.session.request(
            method, f"{base}{path}", params=params, json=json_body, timeout=timeout
        )
        if r.status_code == 204:
            return {"isSuccess": True, "status_code": 204}
        try:
            data = r.json()
        except ValueError:
            data = {"raw": r.text[:2000], "status_code": r.status_code}
        if r.status_code >= 400:
            return {"isSuccess": False, "status_code": r.status_code, "error": data}
        return data


_client: HTBClient | None = None


def client() -> HTBClient:
    global _client  # noqa: PLW0603
    if _client is None:
        _client = HTBClient()
    return _client


def _json(data: Any) -> str:
    return json.dumps(data, indent=2, ensure_ascii=False, default=str)


@function_tool
def htb_list_challenges(ctx: RunContextWrapper, retired: bool = False) -> str:
    """List HackTheBox challenges (active by default, retired if retired=True)."""
    path = "/challenge/list/retired" if retired else "/challenge/list"
    return _json(client().request("GET", path))


@function_tool
def htb_search_content(ctx: RunContextWrapper, query: str) -> str:
    """Search HackTheBox for challenges/machines/users by name."""
    return _json(client().request("GET", "/search/fetch", params={"query": query}))


@function_tool
def htb_get_challenge_info(ctx: RunContextWrapper, challenge_id: int) -> str:
    """Get HackTheBox challenge details: description, category, difficulty, docker status."""
    return _json(client().request("GET", f"/challenge/info/{challenge_id}"))


@function_tool
def htb_spawn_challenge_container(
    ctx: RunContextWrapper, challenge_id: int, wait_seconds: int = 20
) -> str:
    """Spawn a HackTheBox challenge Docker instance; polls briefly for the IP:port."""
    c = client()
    start = c.request("POST", "/container/start", json_body={"challenge_id": challenge_id})
    info: Any = None
    deadline = time.time() + max(0, wait_seconds)
    while True:
        info = c.request("GET", f"/challenge/info/{challenge_id}")
        docker = (info.get("challenge") or {}).get("docker_ip") if isinstance(info, dict) else None
        if docker:
            break
        if time.time() >= deadline:
            break
        time.sleep(2)
    return _json({"start_result": start, "challenge": (info or {}).get("challenge")})


@function_tool
def htb_stop_challenge_container(ctx: RunContextWrapper, challenge_id: int) -> str:
    """Stop a running HackTheBox challenge Docker instance."""
    return _json(
        client().request("POST", "/container/stop", json_body={"challenge_id": challenge_id})
    )


@function_tool
def htb_download_challenge(
    ctx: RunContextWrapper, challenge_id: int, output_dir: str = "/workspace/challenge-files"
) -> str:
    """Download a HackTheBox challenge zip into output_dir inside the sandbox."""
    c = client()
    meta = c.request("GET", f"/challenges/{challenge_id}/download_link")
    url = meta.get("url") if isinstance(meta, dict) else None
    if not url:
        return _json(meta)
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    path = out / f"challenge_{challenge_id}.zip"
    r = c.session.get(url, timeout=300)
    path.write_bytes(r.content)
    return _json(
        {
            "isSuccess": True,
            "path": str(path),
            "size": len(r.content),
            "expires_in": meta.get("expires_in"),
        }
    )


@function_tool
def htb_submit_challenge_flag(ctx: RunContextWrapper, challenge_id: int, flag: str) -> str:
    """Submit a HackTheBox challenge flag (format: HTB{...}). Returns accepted/rejected.

    Call this ONLY with a flag you have actually recovered from the challenge.
    """
    if not flag.startswith("HTB{"):
        return _json({"isSuccess": False, "error": "flag must match HTB{...}"})
    return _json(
        client().request(
            "POST", "/challenge/own", json_body={"challenge_id": challenge_id, "flag": flag}
        )
    )


@function_tool
def htb_submit_machine_flag(ctx: RunContextWrapper, machine_id: int, flag: str) -> str:
    """Submit a HackTheBox machine flag (user or root, format: HTB{...}).

    Requires the machine running and the host/sandbox on the HTB VPN.
    """
    if not flag.startswith("HTB{"):
        return _json({"isSuccess": False, "error": "flag must match HTB{...}"})
    return _json(
        client().request(
            "POST", "/machine/own", json_body={"id": machine_id, "flag": flag}, v5=True
        )
    )
