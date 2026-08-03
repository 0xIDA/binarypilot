# Integrations

BinaryPilot integrates with your workflow through env-var credentials and on-disk artifacts. There's no MCP server hop: the platform REST shims live inside `binarypilot/tools/{flagyard,htb}/` and are invoked as function-tools by the solving agents.

## Environment integration

Platform credentials live in env (or `~/.binarypilot/cli-config.json`); they're forwarded into the sandbox container so in-sandbox tooling sees them too:

- `HTB_TOKEN` → HackTheBox API v4/v5 Bearer.
- `FLAGYARD_USERNAME` / `FLAGYARD_PASSWORD`, or `FLAGYARD_ACCESS_TOKEN` (+ optional `FLAGYARD_REFRESH_TOKEN`).

Set these through your shell, a `.env` file (process env only — BinaryPilot does not parse `.env` itself), or `~/.binarypilot/cli-config.json`.

## CI/CD

Headless mode (`-n`) runs in any CI runner with Docker. Standard pattern:

```yaml
- env:
    BINARYPILOT_LLM: ${{ secrets.BINARYPILOT_LLM }}
    LLM_API_KEY: ${{ secrets.LLM_API_KEY }}
    HTB_TOKEN: ${{ secrets.HTB_TOKEN }}
  run: binarypilot -n --challenge <url>
```

See [`README.md`](../README.md#cicd) for a working workflow snippet.

## Local viewer

`binarypilot view` (or a specific run name) binds the local dashboard at `127.0.0.1` on a random port with a URL token. Nothing leaves your machine.

## Caido proxy

Web traffic in the sandbox flows through a Caido MITM proxy by default. For CTF-web challenges you generally don't notice it, but it's available to the agents via `caido_api` in sandbox Python. CA materials live under `/app/certs`.

## HTB VPN

Machines and some Fortress/Endgame targets require the HTB VPN reachable from the sandbox network. Attach the host to HTB's OpenVPN before starting the run — the sandbox bridges to the host's network for VPN-reachable targets. Docker-instance challenges don't need it.
