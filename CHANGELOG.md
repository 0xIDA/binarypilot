# Changelog

All notable changes to BinaryPilot, sorted newest-first. The format is loose
[Keep a Changelog](https://keepachangelog.com/en/1.0.0/) aligned with Semantic
Versioning — fixes go under Fixed, new behavior under Added, prompts/skills
work under their own headings.

## [Unreleased]

### Fixed
- `_apply_vpn_support` no longer emits `vpn.binarypilot.internal -> <profile-stem>` into `extra_hosts`. The stem is the profile filename (`release_arena_eu-release-1`), not an IP, and docker rejects add-host entries with non-IP values: every `HTB_VPN_OVPN` user hit `docker.errors.APIError: 400 ... invalid IP address in add-host` at container create time. The hostname alias served no purpose; mounts + env + /dev/net/tun + NET_ADMIN are all the VPN stack needs. (`tests/test_docker_client_vpn.py` covers all four wiring branches.)

### Added
- Image entrypoint wrapper `containers/binarypilot-entrypoint.sh`: when `BINARYPILOT_VPN_PROFILE` is set (or `/vpn/*.ovpn` is mounted), the sandbox auto-starts `openvpn --config` in daemon mode before handing off to the base entrypoint. No-op when unset.
- All HTB VPN products recognized by `_format_ctf_challenge_line` (machines, starting-point, sherlocks, fortresses, seasonal); each gets the correct VPN path hint in the root-task message.

### Fixed
- `_apply_vpn_support` now binds `/dev/net/tun` and adds `NET_ADMIN` (required for openvpn+tun setup inside the container); previously only the read-only profile mount and env var were wired.
- Stale hard-refusal language in the system prompt + root-task line — replaced with the VPN-wired-vs-not-wired dual state (the 1.5.0 prompt still said "NOT YET SUPPORTED" after OpenVPN shipped).

## [1.5.0] — 2026-08-04

### Added
- OpenVPN client layer in the sandbox image (`openvpn` + `iproute2`). Image tag bumped to `ghcr.io/0xida/binarypilot-sandbox:1.5.0`.
- `_apply_vpn_support` in `binarypilot/runtime/docker_client.py` — when the host exports `HTB_VPN_OVPN`, the profile is bind-mounted read-only at `/vpn/<name>.ovpn` and `BINARYPILOT_VPN_PROFILE` is set inside the sandbox. No-op when the env var is unset.

### Fixed
- Tool-call loop stalls: `wait_for_agents` default timeout 300s → 120s (parents wake sooner when subagents park) (`bcaee23`).
- HTB machine targets: dropped the "machines require OpenVPN — not yet supported" hard refusal. Root-task line + system prompt now say "if `BINARYPILOT_VPN_PROFILE` is present the entrypoint wires the tunnel; machines reachable", and machines still decline gracefully when the env is absent.

## [1.0.0] — 2026-08-04

### Fixed
- HTB machine targets (`kind=machine` from `--challenge <machine>` or search) now refuse politely instead of burning turns trying to run: the sandbox has no OpenVPN client. Root-task line + inline prompt both prep machines-need-VPN as the answer. Challenge containers via `htb_spawn_challenge_container` / `flagyard_start_instance` are unchanged (`MACHINE ACCESS` rule added to system prompt).
- Fresh machine/challenge resolution paths: `machine_id` lookups hit v5's own endpoint instead of v4's challenge endpoint (typo in endpoint choice, similar path semantics).

### Added
- CHANGELOG.md (this file), pinned at this version going forward.
- Sandbox image ships `openvpn-client` binaries (currently inert — check back after a future VPN feature story) — placeholder; deliberately not wired up yet.

## [1.0.0] — 2026-08-04

### Fixed
- `binarypilot --resume RUN` no longer rejects itself with the fresh-target error — the parse-args `else:` branch was attaching to the wrong `if` (`363c1e5`).
- Completion card on CTF runs shows `Solves N: <challenge>: <flag>` instead of the pentest-oriented `Vulnerabilities 0 (No exploitable vulnerabilities detected)` (`55bc594`).
- FlagYard downloads (`flagyard_download_files`) no longer claim host-side files are in the sandbox — the tool now returns signed URLs and the agent fetches them with `curl` inside the container (`9fd8f31`).
- Tool-written workspace EACCES on hosts where UID remapping mismatches the image's `pentester:1000` (the `/tmp/challenge-files` default path).
- `warm_up_llm` startup smoke call capped at 30s (was 300s = `LLM_TIMEOUT`); start now fails fast on dead endpoints instead of hanging (`36454de`).
- HTB zips: hint string in `htb_download_challenge` records `unzip -o -P hackthebox` so agents stop relearning it (`f0dc089`).
- Forensics long-running subagents no longer get auto-stopped while productive (was tied to the turn-activity counter instead of task-state).
- `stop_agent` and `finish_scan` description text synced with CTF lifecycle (deleted stale pentest references).

### Added
- `report_solve` + `finish_solve` tools: per-solve writeup persistence (`writeups/<solve-id>-<challenge>.md` + consolidated `solves.json`) with resume-safe numbering (`bf4d372`).
- Startup `--platform {flagyard,htb}` and `--challenge NAME_OR_URL`; URL shapes infer the platform, exact-match name search, `flagyard_search_challenges` / `htb_search_content` tools, resolver pipeline in `core/resolver.py` (`42e7bc0`).
- Agent prompt: ABSOLUTE RULE — SOLVE ORDER + STRICT ORDER (1)-(9) closing out at `finish_solve`, flagged candidates with reasons-for-choosing listed and resubmits forbidden (`632383c`).
- Prompt stage: SOURCE-FIRST ANALYSIS, ALL CATEGORIES — per-category solve shape and "no fuzzing without reading source" rule (`6f5980a`, `VERSIONING`).
- Sandboxing: rockyou.txt + seclists wordlists baked into `ghcr.io/0xida/binarypilot-sandbox:1.2.0` (`f9c0057`).
- `wait_for_agents` default timeout 300s → 120s to wake parents sooner when subagents park (`[1.0.0]`).
- One-line install: `curl -sSL https://raw.githubusercontent.com/0xIDA/binarypilot/main/scripts/install.sh | bash` （從 `scripts/install.sh`) (`18844be`, `fdab3a6`).

### Changed
- Package default LLM is `openai/gpt-5.4` (was `openai/gpt-5.1`) to match currently-published OpenAI model family for agentic work.
- `Dockerfile` base moved from Kali-rolling to the upstream `ghcr.io/usestrix/strix-sandbox:1.2.0` image — same Caido/Playwright/Cert stack, plus our CTF toolchain layer (radare2, gdb-multiarch, pwntools, pycryptodome, z3-solver, ropper, ROPgadget, checksec.py, john, hashcat, steghide, exiftool, binwalk, tshark, foremost, pngcheck, 7z, unrar, socat, ruby, zsteg, one_gadget, hashid).
- `finish_scan`'s tool's sanity check for new skills is `python -m pytest tests/test_skills_md.py` instead of `-k'flagyard or htb'`.
- `binarypilot --challenge "Lame" --platform htb` and `--challenge <URL>` both resolve to `ctf_challenge` target type; pentest-style `--target` keeps working unchanged.

[Unreleased]: https://github.com/0xIDA/binarypilot/compare/v1.0.0...HEAD
[1.0.0]: https://github.com/0xIDA/binarypilot/releases/tag/v1.0.0
