<p align="center">
  <a href="https://github.com/0xIDA/binarypilot">
    <img src="https://github.com/0xIDA/.github/raw/main/imgs/cover.png" alt="BinaryPilot Banner" width="100%">
  </a>
</p>

<div align="center">

# BinaryPilot

### The open-source AI CTF solver. Autonomous agents that solve HackTheBox and FlagYard challenges end to end — flag, writeup, submission.

<br/>

<a href="https://github.com/0xIDA/binarypilot"><img src="https://img.shields.io/badge/Docs-GitHub-2b9246?style=for-the-badge&logo=gitbook&logoColor=white" alt="Docs"></a>
<a href="https://github.com/0xIDA/binarypilot"><img src="https://img.shields.io/github/stars/0xIDA/binarypilot?style=flat-square" alt="GitHub Stars"></a>
<a href="LICENSE"><img src="https://img.shields.io/badge/License-Apache%202.0-3b82f6?style=flat-square" alt="License"></a>
<a href="https://pypi.org/project/binarypilot-agent/"><img src="https://img.shields.io/pypi/v/binarypilot-agent?style=flat-square" alt="PyPI Version"></a>

<a href="https://discord.gg/binarypilot"><img src="https://github.com/0xIDA/.github/raw/main/imgs/Discord.png" height="40" alt="Join Discord"></a>
<a href="https://x.com/binarypilot_ai"><img src="https://github.com/0xIDA/.github/raw/main/imgs/X.png" height="40" alt="Follow on X"></a>

</div>

---

## BinaryPilot Overview

BinaryPilot is an autonomous AI CTF player. Give it a challenge name or URL and it pulls the metadata, starts the instance, solves the challenge with a team of specialized agents, submits the flag back to the platform, and writes a human-readable writeup with the reproduction.

**Key Capabilities:**

- **Full CTF toolkit** — crypto, pwn, reverse engineering, web, forensics, OSINT, misc
- **Multi-agent orchestration** — a root coordinator plus deep-specialized solver subagents
- **Direct platform integration** — HackTheBox and FlagYard APIs (start/stop instance, download files, submit flag)
- **100+ playbooks** — vendored from community skill packs, per-category recipes with working snippets
- **Writeup generation** — every accepted flag lands in `binarypilot_runs/<run>/writeups/<challenge>.md`

<br>

<div align="center">
  <a href="https://github.com/0xIDA/binarypilot">
    <img src=".github/screenshot.png" alt="BinaryPilot Demo" width="1000" style="border-radius: 16px;">
  </a>
</div>

## Use Cases

- **HackTheBox training** — grind challenges end to end against lab instances, with writeups you can re-run by hand
- **FlagYard training & competitions** — teams or individuals tackling training/competitive labs autonomously
- **Research automation** — batch-solve categories to compare model strength across crypto/pwn/web/rev
- **Learning** — watch the agent tree's choices via the live TUI; the playbook it picked is on disk with the writeup

## 🚀 Quick Start

**Prerequisites:**
- Docker (running)
- An LLM API key from any [supported provider](https://docs.litellm.ai/docs/providers) (OpenAI, Anthropic, Google, litellm, Ollama, etc.)
- HTB App Token or FlagYard credentials (or both)

### Installation & First Solve

```bash
# Install BinaryPilot
pipx install binarypilot-agent

# Credentials
export HTB_TOKEN="eyJhbGc..."                          # HackTheBox App Token
export FLAGYARD_USERNAME="you" FLAGYARD_PASSWORD="***"  # or FLAGYARD_ACCESS_TOKEN

# LLM
export BINARYPILOT_LLM="openai/gpt-5.4"
export LLM_API_KEY="sk-..."

# Solve a challenge
binarypilot --challenge https://app.hackthebox.com/challenges/15
binarypilot --challenge "Lame" --platform htb
binarypilot --challenge "Web 01" --platform flagyard
```

> [!NOTE]
> First run automatically pulls the sandbox Docker image. Results are saved to `binarypilot_runs/<run-name>/`.

---

## ✨ Features

### Agentic CTF Toolkit

BinaryPilot agents come equipped with a comprehensive competition toolkit in the sandbox:

- **HTTP Interception Proxy** — full request/response manipulation and analysis with Caido
- **Browser Exploitation** — automated browser for client-side and auth flow challenges
- **Shell & Command Execution** — interactive terminal for exploit development and PoC testing
- **Custom Solver Runtime** — Python sandbox for exploits, decoders, constraint solvers
- **Reverse Engineering** — radare2, gdb-multiarch, qemu-user-static (no Ghidra/IDA; terminal-only)
- **Crypto & Constraint Solving** — z3, sympy, pycryptodome, RsaCtfTool-style helpers
- **Forensics & Stego** — binwalk, foremost, steghide, exiftool, tshark, zsteg, p7zip
- **Web Exploitation** — nmap, sqlmap, nuclei, ffuf, katana, agent-browser
- **Pwn Primitives** — pwntools, ropper, ROPgadget, checksec, one_gadget

### Challenge Coverage

BinaryPilot identifies, validates, and solves challenges across the standard CTF categories:

- **Crypto** — RSA attacks, block ciphers, LCG/MT PRNG recovery, padding oracles, classical ciphers, ECC, exotic constructions, historical schemes, ZKP
- **Pwn / Binary Exploitation** — stack + heap, ROP/ret2libc/format-string, modern glibc heap techniques, kernel + sandbox escapes, advanced primitives
- **Reverse Engineering** — anti-analysis bypass, x86/ARM/MIPS, .NET, Java, Python bytecode, WASM, custom VMs, packed binaries
- **Web** — injection (SQLi, SSTI, XXE, NoSQL), auth/JWT attacks, SSRF, IDOR, business logic, prototype pollution, Web3
- **Forensics** — steganography, PCAP, memory dumps, deleted-file recovery, signal/hardware captures, smartphone/iTunes artifacts
- **OSINT** — geolocation, social graph, domain/DNS/whois, public records
- **Misc** — Python/Bash jails, esoteric languages, ML model tampering, RF/SDR, encoding layers

### Multi-Agent Solving

- **Distributed Solving** — specialized agents tackle recon, analysis, exploitation, verification, reporting in parallel
- **Validation Before Submission** — candidate flags are re-derived by an independent agent before the platform submit call
- **Structured Writeups** — every accepted flag produces an on-disk markdown writeup with reproduction

---

## 🖥️ Local Web Viewer

Every run writes results to disk as it runs. Bring them up in a local dashboard:

```bash
binarypilot view                # open the most recent run
binarypilot view my-run-name    # ...or a specific run
```

The server binds to `127.0.0.1` on a random port and opens a private, tokened link. Nothing leaves your machine. The dashboard shows run status, per-challenge artifacts, the live agent graph, and past runs.

---

## Usage Examples

### Basic Usage

```bash
# Solve a challenge by URL (platform inferred)
binarypilot --challenge https://app.hackthebox.com/challenges/15
binarypilot --challenge https://ctf.flagyard.com/labs/12/challenges/34

# Solve by name (platform required)
binarypilot --challenge "Lame" --platform htb
binarypilot --challenge "Forensics 101" --platform flagyard
```

### Advanced Scenarios

```bash
# Run headlessly in CI or on a server
binarypilot -n --challenge https://app.hackthebox.com/challenges/15

# Steer the solve with a hint
binarypilot --challenge "Web 01" --platform flagyard \
  --instruction "Focus on JWT attacks before other vectors"

# Steer from a file
binarypilot --challenge "Lame" --platform htb --instruction-file ./instructions.md

# Resume a prior run
binarypilot --resume <run-name>

# Control intensity
binarypilot --challenge "Lame" --platform htb --scan-mode quick       # single-agent, first-obvious-vector
binarypilot --challenge "Lame" --platform htb --scan-mode deep        # default: full tree, heavy parallelism

# Budget + turn caps
binarypilot --challenge "Web 01" --platform flagyard --max-budget 5.00 --max-turns 400
```

### Headless Mode

`-n` / `--non-interactive`: prints progress + final report to stdout, no TUI. Exits non-zero on failure or when the flag was unaccepted. Designed for batch jobs and CI.

### CI/CD (GitHub Actions)

```yaml
name: binarypilot-ctf-check

on:
  push:
    branches: [main]

jobs:
  ctf-regression:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v6
      - name: Install BinaryPilot
        run: pipx install binarypilot-agent
      - name: Solve a smoke challenge
        env:
          BINARYPILOT_LLM: ${{ secrets.BINARYPILOT_LLM }}
          LLM_API_KEY: ${{ secrets.LLM_API_KEY }}
          HTB_TOKEN: ${{ secrets.HTB_TOKEN }}
        run: binarypilot -n --challenge https://app.hackthebox.com/challenges/15
```

### Configuration

```bash
# LLM
export BINARYPILOT_LLM="openai/gpt-5.4"         # or anthropic/*, litellm/*, ollama/* via LLM_API_BASE
export LLM_API_KEY="sk-..."
export LLM_API_BASE="your-api-base-url"          # local models (Ollama, LMStudio)
export LLM_REASONING_EFFORT="high"               # default high; quick mode: medium

# Platforms
export HTB_TOKEN="eyJhbGc..."                    # HackTheBox App Token
export FLAGYARD_USERNAME="you" FLAGYARD_PASSWORD="***"   # or FLAGYARD_ACCESS_TOKEN
export FLAGYARD_API_BASE="https://api.flagyard.com/api"

# Sandbox image (default is fine)
export BINARYPILOT_IMAGE="ghcr.io/0xida/binarypilot-sandbox:1.2.0"

# Optional
export PERPLEXITY_API_KEY="..."                  # web_search tool
```

> [!NOTE]
> BinaryPilot automatically saves your configuration to `~/.binarypilot/cli-config.json`, so you don't have to re-enter it on every run.

#### Sign in with a ChatGPT subscription

Instead of a metered API key, run BinaryPilot on your ChatGPT Plus/Pro subscription:

```bash
binarypilot auth login chatgpt
export BINARYPILOT_LLM="chatgpt/gpt-5.4"
binarypilot --challenge https://app.hackthebox.com/challenges/15

binarypilot auth status
binarypilot auth logout
```

**Recommended models for best results:**

- [OpenAI GPT-5.4](https://openai.com/api/) — `openai/gpt-5.4`
- [Anthropic Claude Sonnet 4.6](https://claude.com/platform/api) — `anthropic/claude-sonnet-4-6`
- [Google Gemini 3 Pro Preview](https://cloud.google.com/vertex-ai) — `vertex_ai/gemini-3-pro-preview`

See the [LiteLLM providers docs](https://docs.litellm.ai/docs/providers) for all supported providers, including Vertex AI, Bedrock, Azure, and local models.

## Enterprise CTF Solving

Get the same BinaryPilot experience with [enterprise-grade](https://github.com/0xIDA) controls: SSO (SAML/OIDC), custom compliance-ready writeups, dedicated support & SLA, custom deployment options (VPC/self-hosted), BYOK model support, and tailored solving agents optimized for your environment. [Contact us](https://github.com/0xIDA).

## Documentation

Full documentation lives in [`docs/`](docs/README.md):

- [`docs/cli.md`](docs/cli.md) — complete flag reference + URL shapes per platform
- [`docs/platforms.md`](docs/platforms.md) — HackTheBox and FlagYard setup, endpoint maps, flag discipline
- [`docs/architecture.md`](docs/architecture.md) — agent tree, prompt wiring, skills layout, debug-by-symptom table
- [`docs/docker.md`](docs/docker.md) — sandbox contents, build, publish
- [`binarypilot/skills/README.md`](binarypilot/skills/README.md) — skill categories + how to add one

## Contributing

We welcome contributions of code, docs, and new skills — check out our [Contributing Guide](docs/contributing.md) to get started, or open a [pull request](https://github.com/0xIDA/binarypilot/pulls)/[issue](https://github.com/0xIDA/binarypilot/issues).

## Join Our Community

Have questions? Found a bug? Want to contribute? **[Join our Discord!](https://discord.gg/binarypilot)**

## Support the Project

**Love BinaryPilot?** Give us a ⭐ on GitHub!

## Acknowledgements

BinaryPilot builds on the incredible work of open-source projects like [LiteLLM](https://github.com/BerriAI/litellm), [Caido](https://github.com/caido/caido), [Nuclei](https://github.com/projectdiscovery/nuclei), [Playwright](https://github.com/microsoft/playwright), [Textual](https://github.com/Textualize/textual), and the CTF community skill packs vendored into `binarypilot/skills/ctf/`. Huge thanks to their maintainers.

> [!WARNING]
> Only run BinaryPilot on challenges you own or have permission to solve. You are responsible for complying with each platform's rules of engagement.

</div>
