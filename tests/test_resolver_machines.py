"""Machine-specifier resolution — URL slug → numeric machine_id + name."""

from __future__ import annotations

from typing import Any

import pytest

from binarypilot.core import resolver


def _patch_search(monkeypatch: pytest.MonkeyPatch, hits: list[dict[str, Any]]) -> None:
    monkeypatch.setattr(resolver, "_search_htb", lambda _name: hits)


def test_machine_url_slug_resolves_to_numeric_id(monkeypatch: pytest.MonkeyPatch) -> None:
    _patch_search(
        monkeypatch,
        [
            {"kind": "machine", "id": 1, "name": "Lame"},
            {"kind": "machine", "id": 2, "name": "Lame-ish"},
        ],
    )
    target = resolver.resolve_challenge("https://app.hackthebox.com/machines/Lame")
    details = target["details"]
    assert details["kind"] == "machine"
    assert details["machine"] == "Lame"  # slug preserved for reference
    assert details["machine_id"] == 1
    assert details["name"] == "Lame"


def test_machine_url_numeric_slug_is_used_directly(monkeypatch: pytest.MonkeyPatch) -> None:
    # No search call expected — numeric slugs are ids already.
    def _boom(_name: str) -> list[dict[str, Any]]:
        raise AssertionError("numeric slug must not trigger a search")

    monkeypatch.setattr(resolver, "_search_htb", _boom)
    target = resolver.resolve_challenge("https://app.hackthebox.com/machines/157")
    assert target["details"]["machine_id"] == 157


def test_machine_url_slug_match_survives_punctuation(monkeypatch: pytest.MonkeyPatch) -> None:
    """URL slugs lose spaces/apostrophes; normalize both sides before comparing."""
    _patch_search(monkeypatch, [{"kind": "machine", "id": 9, "name": "Bastard's Box"}])
    target = resolver.resolve_challenge("https://app.hackthebox.com/machines/bastards-box")
    assert target["details"]["machine_id"] == 9
    assert target["details"]["name"] == "Bastard's Box"


def test_machine_url_slug_no_fuzzy_fallback(monkeypatch: pytest.MonkeyPatch) -> None:
    """A URL slug names ONE machine — a fuzzy near-match must not be picked."""
    _patch_search(monkeypatch, [{"kind": "machine", "id": 3, "name": "Sequel"}])
    with pytest.raises(resolver.ResolutionError, match="no exact htb machine matches"):
        resolver.resolve_challenge("https://app.hackthebox.com/machines/definitely-not-real")


def test_machine_url_slug_unknown_raises(monkeypatch: pytest.MonkeyPatch) -> None:
    _patch_search(monkeypatch, [])
    with pytest.raises(resolver.ResolutionError, match="no htb machine matches"):
        resolver.resolve_challenge("https://app.hackthebox.com/machines/definitely-not-real")


def test_machine_url_slug_ambiguous_raises(monkeypatch: pytest.MonkeyPatch) -> None:
    # Defensive branch: normalized-duplicate names (not possible with real HTB
    # data) must raise rather than pick one.
    _patch_search(
        monkeypatch,
        [
            {"kind": "machine", "id": 4, "name": "Poison"},
            {"kind": "machine", "id": 5, "name": "Poison!"},
        ],
    )
    with pytest.raises(resolver.ResolutionError, match="ambiguous htb machine"):
        resolver.resolve_challenge("https://app.hackthebox.com/machines/poison")


def test_machine_name_resolves_with_id(monkeypatch: pytest.MonkeyPatch) -> None:
    _patch_search(monkeypatch, [{"kind": "machine", "id": 1, "name": "Lame"}])
    target = resolver.resolve_challenge("Lame", platform="htb")
    assert target["details"] == {
        "specifier": "Lame",
        "platform": "htb",
        "kind": "machine",
        "name": "Lame",
        "machine_id": 1,
    }


def test_machine_search_ignores_challenge_hits(monkeypatch: pytest.MonkeyPatch) -> None:
    """A challenge named like the machine must not satisfy a machine slug."""
    _patch_search(
        monkeypatch,
        [
            {"kind": "challenge", "id": 99, "name": "Lame"},
            {"kind": "machine", "id": 1, "name": "Lame"},
        ],
    )
    target = resolver.resolve_challenge("https://app.hackthebox.com/machines/Lame")
    assert target["details"]["machine_id"] == 1
