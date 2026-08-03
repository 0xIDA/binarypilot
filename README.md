# BinaryPilot

Autonomous CTF solver that plays security competitions end to end: picks a challenge, starts its instance, solves it, submits the flag, and writes a writeup. Built as a fork of [Strix](https://github.com/usestrix/strix), retargeted from application pentesting to CTF.

Supports **HackTheBox** and **FlagYard** out of the box.

## Quick start

Requirements: Docker, an LLM endpoint (OpenAI/Anthropic/etc. or local), HTB or FlagYard account.

```bash
pipx install binarypilot-agent

# Credentials
export HTB_TOKEN="eyJhbGc..."                          # HackTheBox App Token
export FLAGYARD_USERNAME="you" FLAGYARD_PASSWORD="***" # or FLAGYARD_ACCESS_TOKEN

# LLM
export BINARYPILOT_LLM="openai/gpt-5.4"
export LLM_API_KEY="sk-..."

# Solve a challenge
binarypilot --challenge https://app.hackthebox.com/challenges/15
binarypilot --challenge "Lame" --platform htb
binarypilot --challenge "Web 01" --platform flagyard
```

The run ends with `writeups/<challenge>.md` and a hex-encoded report in `binarypilot_runs/<run>/` — the flag, the solve chain, and a reproduction.

## How it works

1. **Resolve** — `--challenge` accepts a challenge name or a URL. Names are resolved via the platform's search API; exact match or loud failure on ambiguity.
2. **Prepare** — Metadata + challenge files pulled into the sandbox; the instance/container starts.
3. **Solve** — Multi-agent tree (root orchestrator + category specialists). 100+ playbooks ship under `binarypilot/skills/ctf/` covering crypto, pwn, reverse, web, forensics, OSINT, misc, each with concrete attack recipes and working snippets.
4. **Submit** — Platform API calls; the response is validated as accepted, then recorded. No submit before the flag's format is regex-checked (`HTB{...}` / `FlagY{...}`).
5. **Writeup** — `report_solve` persists `writeups/<id>-<challenge>.md` + `solves.json` to the run directory; `finish_solve` closes the run.

The agent runs inside a single Docker sandbox: Kali Linux, Caido MITM proxy, the standard web pentest set (nmap/sqlmap/nuclei/ffuf/katana/agent-browser), plus the CTF layer (radare2, gdb-multiarch, qemu-user-static, pwntools, ropper, ROPgadget, checksec, z3, sympy, pycryptodome, r2pipe, binwalk, foremost, steghide, exiftool, tshark, p7zip-full, john, hashcat, hashid, socat, ruby + zsteg/one_gadget). No GUI tools — Ghidra/IDA excluded by design.

## CLI

```
binarypilot --challenge NAME_OR_URL [--platform flagyard|htb]
           [--instruction "..."] [-n] [-m quick|standard|deep]
           [--max-turns N] [--max-budget USD] [--resume RUN]

binarypilot --target <url|repo|dir>   # original strix pentest flow, still works
```

- `--challenge` is the CTF entrypoint; conflicts with `--target`, `--target-list`, `--resume`.
- `<URL>` parses platform automatically. Names require `--platform`.
- `--platform htb` + machine/sherlock URLs supported too (`/machines/<name>`, `/sherlocks/<id>`).

## Environment

```
# LLM
BINARYPILOT_LLM=openai/gpt-5.4                # or anthropic/claude-* or litellm/*
LLM_API_KEY=sk-...
LLM_API_BASE=http://localhost:11434           # local models only

# Platforms
HTB_TOKEN=eyJhbGc...                           # HackTheBox App Token
FLAGYARD_USERNAME=you FLAGYARD_PASSWORD=***    # FlagYard (Keycloak password grant)
FLAGYARD_ACCESS_TOKEN=eyJhbGc...               #   or pre-issued token

# Sandbox image (default)
BINARYPILOT_IMAGE=ghcr.io/0xida/binarypilot-sandbox:1.2.0

# Optional
WEB_SEARCH_API_KEY=...                         # Perplexity for web_search tool
```

Env vars can also live in `~/.binarypilot/cli-config.json` (see `binarypilot/core/paths.py`).

## Image

`ghcr.io/0xida/binarypilot-sandbox:1.2.0` — thin layer over [`ghcr.io/usestrix/strix-sandbox:1.2.0`](https://github.com/usestrix/strix), adding the CTF toolchain only. Build: `docker build -f containers/Dockerfile .` (~2 min; the base is cached).

## Architecture (delta from strix)

- `binarypilot/tools/flagyard/`, `binarypilot/tools/htb/` — REST wrappers for both platforms, direct (no MCP framework).
- `binarypilot/core/resolver.py` — challenge name/URL → target entry.
- `binarypilot/report/state.py` — adds `solves` + `add_solve()`; writeups persisted alongside `findings.sarif`.
- `binarypilot/tools/finish/tool.py` — `report_solve` + `finish_solve`, parallel to `finish_scan`.
- `binarypilot/skills/ctf/` — 73 CTF playbooks (7 base + 66 deep-dives), vendored from `oh-my-open-pentest` and `reverse-skill`, GUI-free.
- `binarypilot/agents/prompts/system_prompt.jinja` — CTF loop + platform rules replacing the pentest methodology.

Everything else — runner, multi-agent SDK runtime, TUI, viewer, session handling, Caido proxy, Dockerfile base — inherited unchanged from strix.

## HTB VPN note

Machines and some Fortress/Endgame targets require the HTB VPN reachable from the sandbox. Run `openvpn` on your host with your HTB pack before you start; the Docker sandbox will use the host's network for that flow. Challenge Docker instances don't need it.

## Docs

- [`docs/cli.md`](docs/cli.md) — full flag reference
- [`docs/platforms.md`](docs/platforms.md) — per-platform environment and API notes
- [`docs/architecture.md`](docs/architecture.md) — agent tree, prompts, skills, report pipeline
- [`docs/docker.md`](docs/docker.md) — image contents + build
- [`binarypilot/skills/README.md`](binarypilot/skills/README.md) — skill layout + how to add one

## Status

Beta. Verified: one FlagYard challenge end-to-end (manual + agent flow). HTB machines path built but untested against live VPN. Runes+villages fork-quality imported from stock strix (670 test suite passes, one pre-existing upstream flake).

## License

Apache-2.0 (same as upstream). See [LICENSE](LICENSE).
