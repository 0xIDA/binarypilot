# BinaryPilot

### Autonomous CTF solver. Resolves, instances, solves, submits, writes the writeup. HackTheBox + FlagYard.

<br/>

<a href="https://github.com/0xIDA/binarypilot"><img src="https://img.shields.io/github/stars/0xIDA/binarypilot?style=flat-square" alt="GitHub Stars"></a>
<a href="LICENSE"><img src="https://img.shields.io/badge/License-Apache%202.0-3b82f6?style=flat-square" alt="License"></a>
<a href="https://pypi.org/project/binarypilot-agent/"><img src="https://img.shields.io/pypi/v/binarypilot-agent?style=flat-square" alt="PyPI Version"></a>
<a href="https://b0f.ru"><img src="https://img.shields.io/badge/Site-b0f.ru-2b9246?style=flat-square" alt="b0f.ru"></a>

---

## What it does

- You give it a challenge — a name or a URL on HackTheBox or FlagYard.
- It resolves the challenge, starts its instance, downloads the attachments, and solves it with a tree of specialized agents.
- Every candidate flag is verified, regex-checked for the platform's format, submitted via the platform API, and recorded.
- Every accepted flag produces a markdown writeup in `binarypilot_runs/<run>/writeups/`.

## Quick Start

**Prerequisites:** Docker (running) and an LLM endpoint.

```bash
# One-line install
curl -sSL https://raw.githubusercontent.com/0xIDA/binarypilot/main/scripts/install.sh | bash

# Creds
export BINARYPILOT_LLM="openai/gpt-5.4"
export LLM_API_KEY="***"
export HTB_TOKEN="eyJhbGc..."                                # or:
export FLAGYARD_USERNAME="you" FLAGYARD_PASSWORD="***"

# Solve
binarypilot --challenge https://app.hackthebox.com/challenges/15
binarypilot --challenge "Lame" --platform htb
binarypilot --challenge "Web 01" --platform flagyard
```

First run pulls the sandbox image (`ghcr.io/0xida/binarypilot-sandbox:1.2.0`). Runs land in `binarypilot_runs/<run>/`.

## Categories

- **Crypto** — RSA, block ciphers, classical, ECC, exotic, historical, ZKP, PRNG
- **Pwn** — stack + heap, ret2*, format strings, kernel + sandbox escapes
- **Reverse** — anti-analysis, x86/ARM/MIPS, .NET, Java, Python bytecode, WASM, custom VMs, packed
- **Web** — SQLi, SSTI, XSS, SSRF, IDOR, JWT, deserialization, prototype pollution, Web3
- **Forensics** — steganography, PCAP, memory, deleted data, signal/hardware captures
- **OSINT** — geolocation, social, dorking, DNS, wayback
- **Misc** — Python/Bash jails, esoteric languages, games/VMs, RF/SDR, encoding layers

100+ playbooks vendored in [`binarypilot/skills/ctf/`](binarypilot/skills/README.md).

## Configuration

```bash
# LLM
export BINARYPILOT_LLM="openai/gpt-5.4"     # litellm-compatible, any provider
export LLM_API_KEY="sk-..."
export LLM_API_BASE="http://localhost:11434" # local (Ollama, LMStudio)

# Platforms
export HTB_TOKEN="***"                       # HackTheBox App Token
export FLAGYARD_USERNAME="you"
export FLAGYARD_PASSWORD="***"               # or FLAGYARD_ACCESS_TOKEN

# Sandbox image (default fine)
export BINARYPILOT_IMAGE="ghcr.io/0xida/binarypilot-sandbox:1.2.0"
```

Or persist in `~/.binarypilot/cli-config.json`.

## Usage Examples

```bash
# CTF by URL (platform auto-detected)
binarypilot --challenge https://app.hackthebox.com/challenges/15
binarypilot --challenge https://ctf.flagyard.com/labs/12/challenges/34

# By name (platform required)
binarypilot --challenge "Lame" --platform htb
binarypilot --challenge "Web 01" --platform flagyard

# Headless/silent (CI or servers)
binarypilot -n --challenge ...

# Steer with a hint
binarypilot --challenge "Lame" --platform htb --instruction "Focus on ret2libc, not shellcode"

# Resume a previous run
binarypilot --resume 2026-08-03-lame

# Budget + turn caps
binarypilot --challenge "Web 01" --platform flagyard --max-budget 5.00 --max-turns 400

# Open local viewer of the last run
binarypilot view

# Existing pentest-mode compatibility
binarypilot --target https://your-app.com
```

## CLI (subset)

```
--challenge NAME_OR_URL         challenge name or full URL
--platform {flagyard,htb}      required when --challenge is a name
--instruction "text"           steering hint
--instruction-file PATH        steering from a file
-m {quick,standard,deep}       solve intensity
-n                             headless
--resume RUN_NAME              resume a prior run
--max-turns N                  per-agent turn cap (default 500)
--max-budget USD               LLM cost cap
-v, --version                  version
```

See [`docs/cli.md`](docs/cli.md) for the full flag reference.

## Docs

- [`docs/usage.md`](docs/usage.md) — everyday flows
- [`docs/cli.md`](docs/cli.md) — complete flag reference + URL shapes
- [`docs/platforms.md`](docs/platforms.md) — per-platform auth env + endpoints
- [`docs/architecture.md`](docs/architecture.md) — agent tree, prompt wiring, skills, debug-by-symptom
- [`docs/llm-providers.md`](docs/llm-providers.md) — LLM config per provider
- [`docs/advanced.md`](docs/advanced.md) — budget/turns, sandbox tuning, resume rules
- [`docs/integrations.md`](docs/integrations.md) — CI, viewer, Caido, HTB VPN
- [`docs/docker.md`](docs/docker.md) — sandbox contents + build
- [`docs/contributing.md`](docs/contributing.md) — dev setup + commit style + skill writing

## License

Apache-2.0. See [`LICENSE`](LICENSE).

> [!WARNING]
> Run against challenges you own or have permission to solve. You are responsible for complying with each platform's rules of engagement.
