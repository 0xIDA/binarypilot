# Changelog

All notable changes to BinaryPilot, sorted newest-first. The format is loose
[Keep a Changelog](https://keepachangelog.com/en/1.0.0/) aligned with Semantic
Versioning — fixes go under Fixed, new behavior under Added, prompts/skills
work under their own headings.

## [Unreleased]

### Added
- Two new HTB platform tools: `htb_get_machine_info(machine_id)` (machine profile + IP if spawned) and `htb_spawn_machine(machine_id, wait_seconds=30)` (spawns the VM and polls for the assigned 10.x IP). Both registered in the agent factory.
- Image entrypoint wrapper `containers/binarypilot-entrypoint.sh`: when `BINARYPILOT_VPN_PROFILE` is set (or `/vpn/*.ovpn` is mounted), the sandbox auto-starts `openvpn --config` in daemon mode and waits up to 30s for `tun0` to come up before handing off to the base entrypoint. No-op when unset.
- All HTB VPN products recognized by `_format_ctf_challenge_line` (machines, starting-point, sherlocks, fortresses, seasonal); each gets the correct VPN path hint in the root-task message.
- `system_prompt.jinja` MACHINE ACCESS rewritten as an ordered 6-step procedure: (1) resolve kind, (2) refuse on missing profile, (3) one-shot `ip a | grep tun` check, (4) `htb_spawn_machine` BEFORE any nmap, (5) `ping -c2 <10.x>` gate before enum, (6) `htb_submit_machine_flag` at the end. Explicit anti-patterns called out (no curling api endpoints, no container spawns for kind=machine, no repeated VPN probing).

### Fixed
- `_apply_vpn_support` no longer emits `vpn.binarypilot.internal -> <profile-stem>` into `extra_hosts`. The stem is the profile filename (`release_arena_eu-release-1`), not an IP, and docker rejects add-host entries with non-IP values: every `HTB_VPN_OVPN` user hit `docker.errors.APIError: 400 ... invalid IP address in add-host` at container create time. The hostname alias served no purpose; mounts + env + /dev/net/tun + NET_ADMIN are all the VPN stack needs. (`tests/test_docker_client_vpn.py` covers all four wiring branches.)
- `_apply_vpn_support` binds `/dev/net/tun` and adds `NET_ADMIN` (required for openvpn+tun setup inside the container); previously only the read-only profile mount and env var were wired.
- Stale hard-refusal language in the system prompt + root-task line — replaced with the VPN-wired-vs-not-wired dual state (the 1.5.0 prompt still said "NOT YET SUPPORTED" after OpenVPN shipped).

## [1.5.2] — 2026-08-05

### Fixed
- `_apply_vpn_support` no longer emits `vpn.binarypilot.internal -> <profile-stem>` into `extra_hosts`. The stem is the profile filename (`release_arena_eu-release-1`), not an IP, and docker rejects add-host entries with non-IP values. (`tests/test_docker_client_vpn.py`.)

## [1.5.1] — 2026-08-05

### Added
- Image entrypoint wrapper `containers/binarypilot-entrypoint.sh`.
- `_apply_vpn_support` `/dev/net/tun` + `NET_ADMIN` wiring.
- HTB VPN product kind-awareness in `_format_ctf_challenge_line`.

### Fixed
- Stale "not yet supported" prompt language for machines.

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
