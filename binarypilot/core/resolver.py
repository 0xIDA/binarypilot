"""Resolve CTF challenge specifiers (name or URL) to platform IDs.

Two accepted shapes per platform:
- URL:  https://ctf.flagyard.com/labs/12/challenges/34
        https://app.hackthebox.com/challenges/15
        https://app.hackthebox.com/machines/Lame
        https://app.hackthebox.com/sherlocks/7
- Name: "Web 01" / "Lame" / "Blue" — resolved via the platform's search API.

The resolver is the CLI-side glue: it returns a ``targets[]`` entry shaped for
``scan_config`` so the agent sees the challenge the same way it sees a repo or
URL target. Ambiguous names raise; we never pick silently.
"""

from __future__ import annotations

import re
from typing import Any
from urllib.parse import urlparse


# ---------------------------------------------------------------------------
# URL parsing
# ---------------------------------------------------------------------------

_PATTERNS: list[tuple[str, re.Pattern[str], str]] = [
    (
        "flagyard",
        re.compile(r"/labs/(\d+)(?:/challenges/([A-Za-z0-9_-]+))?/?$"),
        "challenge",
    ),
    ("htb", re.compile(r"/challenges/(\d+)/?$"), "challenge"),
    ("htb", re.compile(r"/machines/([\w.-]+)/?$"), "machine"),
    ("htb", re.compile(r"/sherlocks/(\d+)/?$"), "sherlock"),
]

_PLATFORM_DOMAINS = {
    "flagyard": ("ctf.flagyard.com", "flagyard.com"),
    "htb": ("app.hackthebox.com", "hackthebox.com"),
}


class ResolutionError(RuntimeError):
    pass


def _looks_like_url(spec: str) -> bool:
    return spec.startswith(("http://", "https://"))


def parse_challenge_url(spec: str) -> dict[str, Any]:
    """Parse a platform URL into a challenge descriptor. Returns {} on no match."""
    if not _looks_like_url(spec):
        return {}
    u = urlparse(spec)
    host = u.netloc.lower()
    for platform, pattern, kind in _PATTERNS:
        if host not in _PLATFORM_DOMAINS[platform]:
            continue
        m = pattern.search(u.path)
        if m:
            ids = [g for g in m.groups() if g is not None]
            out: dict[str, Any] = {"platform": platform, "kind": kind}
            if platform == "flagyard" and len(ids) >= 2:
                out["lab_id"] = int(ids[0])
                out["challenge_id"] = ids[1]
            elif platform == "flagyard":
                out["lab_id"] = int(ids[0])
            else:
                key = {
                    "challenge": "challenge_id",
                    "machine": "machine",
                    "sherlock": "sherlock_id",
                }[kind]
                out[key] = ids[-1] if kind == "machine" else int(ids[-1])
            return out
    return {}


# ---------------------------------------------------------------------------
# Name search (host-side REST, same code as the agent tools)
# ---------------------------------------------------------------------------


def _search_flagyard(name: str) -> list[dict[str, Any]]:
    from binarypilot.tools.flagyard import tool as fy  # noqa: PLC0415 - lazy import

    c = fy.client()
    q = name.lower().strip()
    results: list[dict[str, Any]] = []
    for lab_type in ("training", "competitive"):
        page = 1
        labs: list[Any] = []
        while True:
            resp = c.request(
                "GET", "/labs/public", params={"type": lab_type, "page": page, "limit": 50}
            )
            labs.extend(((resp or {}).get("data") or {}).get("items") or [])
            meta = ((resp or {}).get("data") or {}).get("meta") or {}
            if not meta.get("hasNextPage") or page >= 20:
                break
            page += 1
        for lab in labs:
            lid = lab.get("id") if isinstance(lab, dict) else None
            lab_data = (c.request("GET", f"/labs/{lid}/public") or {}).get("data") or {}
            results.extend(
                {
                    "lab_id": lid,
                    "challenge_id": ch.get("id"),
                    "name": ch.get("name"),
                    "points": ch.get("points"),
                    "difficulty": ch.get("difficulty"),
                }
                for ch in lab_data.get("challenges") or []
                if q in (ch.get("name") or "").lower() or q in str(ch.get("id", "")).lower()
            )
    return results


def _search_htb(name: str) -> list[dict[str, Any]]:
    from binarypilot.tools.htb import tool as hb  # noqa: PLC0415

    c = hb.client()
    data = c.request("GET", "/search/fetch", params={"query": name})
    out = []
    for kind_key, kind in (("challenges", "challenge"), ("machines", "machine")):
        out.extend(
            {
                "kind": kind,
                "id": item.get("id"),
                "name": item.get("name") or item.get("value"),
            }
            for item in ((data or {}).get(kind_key) or [])
        )
    return out


def _exact_or_raise(name: str, results: list[dict[str, Any]], platform: str) -> dict[str, Any]:
    if not results:
        raise ResolutionError(f"no {platform} challenge matches {name!r}")
    exact = [r for r in results if (r.get("name") or "").lower() == name.lower().strip()]
    pool = exact if exact else results
    if len(pool) > 1:
        listed = ", ".join(
            f"{r.get('name')} (id={r.get('id') or r.get('challenge_id')})" for r in pool[:8]
        )
        raise ResolutionError(
            f"ambiguous {platform} challenge {name!r}: {len(pool)} matches — {listed}. "
            f"Refine the name or pass the challenge URL."
        )
    return pool[0]


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def resolve_challenge(spec: str, platform: str | None = None) -> dict[str, Any]:
    """Resolve a user-supplied challenge specifier (name or URL) to a target entry.

    Returns a dict suitable for ``scan_config["targets"]``:
    ``{"type": "ctf_challenge", "details": {...}}``.
    """
    if not spec or not spec.strip():
        raise ResolutionError("empty challenge specifier")

    parsed = parse_challenge_url(spec)
    if parsed:
        details: dict[str, Any] = {"specifier": spec, **parsed}
        return {
            "type": "ctf_challenge",
            "original": spec,
            "details": details,
        }

    if platform not in {"flagyard", "htb"}:
        raise ResolutionError(
            f"--challenge {spec!r} is a name, not a URL — pass --platform flagyard|htb, "
            f"or use the challenge URL."
        )

    if platform == "flagyard":
        matches = _search_flagyard(spec)
        hit = _exact_or_raise(spec, matches, platform)
        details = {
            "specifier": spec,
            "platform": "flagyard",
            "kind": "challenge",
            "lab_id": hit["lab_id"],
            "challenge_id": hit["challenge_id"],
            "name": hit.get("name"),
        }
    else:
        matches = _search_htb(spec)
        hit = _exact_or_raise(spec, matches, "htb")
        details = {
            "specifier": spec,
            "platform": "htb",
            "kind": hit["kind"],
            "name": hit.get("name"),
        }
        if hit["kind"] == "challenge":
            details["challenge_id"] = hit["id"]
        else:
            details["machine_id"] = hit["id"]

    return {
        "type": "ctf_challenge",
        "original": spec,
        "details": details,
    }
