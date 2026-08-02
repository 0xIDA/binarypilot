"""FlagYard platform tools — labs, challenge instances, files, flag submission.

Direct REST (https://api.flagyard.com/api). Credentials come from
``PlatformSettings`` (env: FLAGYARD_USERNAME/PASSWORD or FLAGYARD_ACCESS_TOKEN).
Auth code adapted from flagyard-mcp-server (0xIDA/flagyard-mcp-server).
"""

from __future__ import annotations

import json
import os
import time
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, unquote, urlparse

import requests
from agents import RunContextWrapper, function_tool

from binarypilot.config import load_settings


SSO_TOKEN_URL = os.environ.get(
    "FLAGYARD_SSO_TOKEN",
    "https://sso.tuwaiq.edu.sa/auth/realms/main/protocol/openid-connect/token",
)
CLIENT_ID = os.environ.get("FLAGYARD_CLIENT_ID", "flagyard")


class FlagyardClient:
    def __init__(self) -> None:
        s = load_settings().platforms
        self.api_base = s.flagyard_api_base.rstrip("/")
        self.session = requests.Session()
        self.session.headers.update({"Accept": "application/json", "User-Agent": "binarypilot/1.0"})
        self.access_token = (s.flagyard_access_token or "").strip()
        self.refresh_token = ""
        self.username = (s.flagyard_username or "").strip()
        self.password = (s.flagyard_password or "").strip()
        self.token_expiry = 0.0
        if not self.access_token and not (self.username and self.password):
            raise RuntimeError("Set FLAGYARD_USERNAME+FLAGYARD_PASSWORD or FLAGYARD_ACCESS_TOKEN")

    def ensure_token(self) -> str:
        now = time.time()
        if self.access_token and now < self.token_expiry - 60:
            return self.access_token
        if self.refresh_token:
            try:
                self._token_request(
                    {
                        "grant_type": "refresh_token",
                        "client_id": CLIENT_ID,
                        "refresh_token": self.refresh_token,
                    }
                )
            except Exception:  # noqa: BLE001, S110 - stale refresh token; fall through to password grant
                pass
            else:
                return self.access_token
        if self.username and self.password:
            self._token_request(
                {
                    "grant_type": "password",
                    "client_id": CLIENT_ID,
                    "username": self.username,
                    "password": self.password,
                }
            )
            return self.access_token
        if self.access_token:
            return self.access_token
        raise RuntimeError("Unable to obtain FlagYard access token")

    def _token_request(self, data: dict[str, str]) -> None:
        r = self.session.post(
            SSO_TOKEN_URL,
            data=data,
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            timeout=30,
        )
        if r.status_code != 200:
            raise RuntimeError(f"SSO token error {r.status_code}: {r.text[:300]}")
        payload = r.json()
        self.access_token = payload["access_token"]
        if payload.get("refresh_token"):
            self.refresh_token = payload["refresh_token"]
        self.token_expiry = time.time() + int(payload.get("expires_in", 3600))

    def request(
        self,
        method: str,
        path: str,
        *,
        params: dict[str, Any] | None = None,
        json_body: Any = None,
        timeout: int = 60,
    ) -> Any:
        token = self.ensure_token()
        r = self.session.request(
            method,
            f"{self.api_base}{path}",
            params=params,
            json=json_body,
            headers={"Authorization": f"Bearer {token}"},
            timeout=timeout,
        )
        if r.status_code == 401 and (self.refresh_token or (self.username and self.password)):
            self.token_expiry = 0
            token = self.ensure_token()
            r = self.session.request(
                method,
                f"{self.api_base}{path}",
                params=params,
                json=json_body,
                headers={"Authorization": f"Bearer {token}"},
                timeout=timeout,
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


_client: FlagyardClient | None = None


def client() -> FlagyardClient:
    global _client  # noqa: PLW0603
    if _client is None:
        _client = FlagyardClient()
    return _client


def _json(data: Any) -> str:
    return json.dumps(data, indent=2, ensure_ascii=False, default=str)


def _redact_instance(obj: Any) -> Any:
    if isinstance(obj, dict):
        return {
            k: ("[redacted]" if k in ("correctFlag", "correct_flag") else _redact_instance(v))
            for k, v in obj.items()
        }
    if isinstance(obj, list):
        return [_redact_instance(x) for x in obj]
    return obj


def _flag_error(flag: str) -> str | None:
    if not flag or len(flag) > 250 or not flag.startswith("FlagY{"):
        return "flag must match FlagY{...} (1..250 chars), per FlagYard flag format"
    return None


@function_tool
def flagyard_list_labs(ctx: RunContextWrapper, lab_type: str = "training", page: int = 1) -> str:
    """List FlagYard public labs. lab_type: 'training' or 'competitive'."""
    data = client().request(
        "GET", "/labs/public", params={"type": lab_type, "page": page, "limit": 20}
    )
    return _json(data)


@function_tool
def flagyard_get_lab(ctx: RunContextWrapper, lab_id: int) -> str:
    """Get a FlagYard lab and its challenges (ids, points, difficulty, completion)."""
    return _json(client().request("GET", f"/labs/{lab_id}/public"))


@function_tool
def flagyard_get_challenge(ctx: RunContextWrapper, lab_id: int, challenge_id: str) -> str:
    """Get full FlagYard challenge details (description, files, running instance)."""
    return _json(
        _redact_instance(client().request("GET", f"/labs/{lab_id}/challenges/{challenge_id}"))
    )


@function_tool
def flagyard_start_instance(
    ctx: RunContextWrapper, lab_id: int, challenge_id: str, wait_seconds: int = 15
) -> str:
    """Start a FlagYard challenge instance; polls briefly for instanceAddress."""
    c = client()
    start = c.request("POST", f"/labs/{lab_id}/challenges/{challenge_id}/instance", json_body={})
    instance = None
    deadline = time.time() + max(0, wait_seconds)
    while True:
        details = c.request("GET", f"/labs/{lab_id}/challenges/{challenge_id}")
        instance = ((details or {}).get("data") or {}).get("currentRunningInstanceForUser")
        if instance and (instance.get("isRunning") or instance.get("instanceAddress")):
            break
        if time.time() >= deadline:
            break
        time.sleep(2)
    return _json(
        _redact_instance(
            {
                "start_result": start,
                "instance": instance,
                "instanceAddress": (instance or {}).get("instanceAddress"),
            }
        )
    )


@function_tool
def flagyard_stop_instance(ctx: RunContextWrapper, lab_id: int, challenge_id: str) -> str:
    """Stop a running FlagYard challenge instance."""
    return _json(client().request("DELETE", f"/labs/{lab_id}/challenges/{challenge_id}/instance"))


@function_tool
def flagyard_download_files(
    ctx: RunContextWrapper,
    lab_id: int,
    challenge_id: str,
    output_dir: str = "/workspace/challenge-files",
) -> str:
    """Download FlagYard challenge attachments to output_dir inside the sandbox."""
    c = client()
    meta = c.request("GET", f"/labs/{lab_id}/challenges/{challenge_id}/challenge-files")
    if not isinstance(meta, dict) or meta.get("isSuccess") is False:
        return _json(meta)
    files = ((meta.get("data") or {}).get("files")) or []
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    saved = []
    for f in files:
        url = f.get("url")
        name = f.get("fileName") or f.get("name")
        if not name and url:
            disp = parse_qs(urlparse(url).query).get("response-content-disposition", [""])[0]
            if "filename=" in disp:
                name = unquote(disp.split("filename=")[-1].strip().strip('"'))
        if not name:
            name = f"file_{len(saved) + 1}.bin"
        try:
            r = c.session.get(url, timeout=120)
            path = out / Path(name).name
            path.write_bytes(r.content)
            saved.append({"file": name, "path": str(path), "size": len(r.content)})
        except (OSError, requests.RequestException) as e:
            saved.append({"file": name, "error": str(e)})
    return _json({"isSuccess": True, "files": saved})


@function_tool
def flagyard_search_challenges(
    ctx: RunContextWrapper, query: str, lab_type: str = "training"
) -> str:
    """Search FlagYard challenge names across public labs (case-insensitive substring)."""
    c = client()
    q = query.lower().strip()
    results = []
    page = 1
    labs = []
    while True:
        resp = c.request(
            "GET", "/labs/public", params={"type": lab_type, "page": page, "limit": 50}
        )
        items = ((resp or {}).get("data") or {}).get("items") or []
        labs.extend(items)
        meta = ((resp or {}).get("data") or {}).get("meta") or {}
        if not meta.get("hasNextPage") or page >= 20:
            break
        page += 1
    for lab in labs:
        lid = lab.get("id")
        lab_data = (c.request("GET", f"/labs/{lid}/public") or {}).get("data") or {}
        results.extend(
            {
                "lab_id": lid,
                "lab_name": lab_data.get("nameEn") or lab.get("nameEn"),
                "challenge": ch,
            }
            for ch in lab_data.get("challenges") or []
            if q in (ch.get("name") or "").lower() or q in str(ch.get("id", "")).lower()
        )
    return _json({"query": query, "count": len(results), "results": results})


@function_tool
def flagyard_submit_flag(ctx: RunContextWrapper, lab_id: int, challenge_id: str, flag: str) -> str:
    """Submit a FlagYard flag (format: FlagY{...}). Returns accepted/rejected.

    Call this ONLY with a flag you have actually recovered from the challenge.
    """
    if err := _flag_error(flag):
        return _json({"isSuccess": False, "error": err})
    return _json(
        client().request(
            "POST", f"/labs/{lab_id}/challenges/{challenge_id}/flag", json_body={"flag": flag}
        )
    )
