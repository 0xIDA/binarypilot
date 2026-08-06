"""Build the JSON payloads the viewer SPA consumes from a run directory."""

from __future__ import annotations

import json
import logging
from typing import TYPE_CHECKING, Any

from binarypilot.core.paths import run_record_path


if TYPE_CHECKING:
    from pathlib import Path


logger = logging.getLogger(__name__)

_TERMINAL_STATUSES = {"completed", "stopped", "failed", "interrupted"}

_KNOWN_SEVERITIES = ("critical", "high", "medium", "low")


def severity_counts(vulns: list[Any]) -> dict[str, int]:
    """Bucket vulnerabilities into critical/high/medium/low counts.

    Mirrors the SPA's ``severityCounts``: severities are lowercased and
    trimmed, and anything outside the four known buckets (``info``,
    ``informational``, ``unknown``, missing, ...) folds into ``low`` so the
    shared UI renders cleanly.
    """
    counts = dict.fromkeys(_KNOWN_SEVERITIES, 0)
    for vuln in vulns:
        raw = vuln.get("severity") if isinstance(vuln, dict) else None
        severity = str(raw or "").lower().strip()
        if severity not in counts:
            severity = "low"
        counts[severity] += 1
    return counts


def build_run_state(run_dir: Path) -> dict[str, Any]:
    """Agent graph + full per-agent event/message stream.

    Reuses the Textual-free ``TuiLiveView`` projection so the viewer and the TUI
    share one parser for ``agents.json`` + ``agents.db`` and never drift.
    """
    # Imported lazily so importing binarypilot.interface.viewer does not eagerly pull the TUI.
    from binarypilot.interface.tui.live_view import TuiLiveView

    view = TuiLiveView()
    view.hydrate_from_run_dir(run_dir)
    return {"agents": list(view.agents.values()), "events": view.events}


def read_run_summary(run_dir: Path) -> dict[str, Any]:
    """The ``run.json`` record plus a computed ``finished`` flag."""
    record = _load_json(run_record_path(run_dir), default={})
    if not isinstance(record, dict):
        record = {}
    status = record.get("status")
    finished = status in _TERMINAL_STATUSES and bool(record.get("end_time"))
    return {**record, "finished": finished}


def primary_target(record: dict[str, Any]) -> str | None:
    """The first target's original string from a run record, or None."""
    targets = record.get("targets_info")
    if isinstance(targets, list):
        for entry in targets:
            if isinstance(entry, dict):
                original = entry.get("original")
                if isinstance(original, str) and original:
                    return original
    return None


def read_vulnerabilities(run_dir: Path) -> list[Any]:
    """The ``vulnerabilities.json`` list (empty until a scan writes it)."""
    data = _load_json(run_dir / "vulnerabilities.json", default=[])
    return data if isinstance(data, list) else []


def read_solves(run_dir: Path) -> list[Any]:
    """The ``solves.json`` list — confirmed CTF solves recorded by report_solve."""
    data = _load_json(run_dir / "solves.json", default=[])
    return data if isinstance(data, list) else []


def read_findings(run_dir: Path) -> list[Any]:
    """The finding list the Findings tab renders — vulnerabilities when present
    (pentest runs), solves otherwise (CTF runs).

    Solves arrive mapped into a vulnerability-shaped record so the existing
    frontend (findings list + detail card) renders them unchanged:

    - severity is always ``"low"`` — CTF challenges don't carry a severity
      palette and the TS type has no "info" bucket, so the parser's fold-to-low
      rule would land them there anyway.
    - the solve's markdown writeup maps to ``technical_analysis`` (the detail
      card renders that as the long-form body); PoC code and language map to
      ``poc_script_code`` / ``poc_description``.
    - platform and flag ride in the record as extra fields. The TS interface
      tolerates unknown keys (``Record<string, unknown>`` in the API client).
    """
    vulns = read_vulnerabilities(run_dir)
    if vulns:
        return vulns
    solves = read_solves(run_dir)
    out: list[Any] = []
    for s in solves:
        if not isinstance(s, dict):
            continue
        poc_lang = str(s.get("poc_language") or "").strip()
        poc = str(s.get("poc") or "").strip()
        record = {
            "id": str(s.get("id") or "solve"),
            "title": str(s.get("title") or "Untitled solve"),
            "severity": "low",
            "timestamp": str(s.get("timestamp") or ""),
            "target": str(s.get("challenge") or ""),
            "technical_analysis": str(s.get("writeup") or ""),
            "poc_description": (f"Solver ({poc_lang})" if poc_lang else "Solver") if poc else "",
            "poc_script_code": poc,
            # CTF extras — frontend renders these via the shared detail card
            # only if we teach it, but they're present in the JSON for scripts.
            "platform": str(s.get("platform") or ""),
            "flag": str(s.get("flag") or ""),
        }
        out.append(record)
    return out


def read_report_markdown(run_dir: Path) -> str:
    """The executive report markdown (empty until a scan writes it)."""
    report_path = run_dir / "solve_report.md"
    try:
        return report_path.read_text(encoding="utf-8")
    except OSError:
        return ""


def _load_json(path: Path, *, default: Any) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return default


__all__ = [
    "build_run_state",
    "primary_target",
    "read_report_markdown",
    "read_run_summary",
    "read_vulnerabilities",
    "severity_counts",
]
