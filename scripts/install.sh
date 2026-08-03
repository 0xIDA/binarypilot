#!/usr/bin/env bash
# BinaryPilot installer — curl | bash
#
#   curl -sSL https://raw.githubusercontent.com/0xIDA/binarypilot/main/scripts/install.sh | bash
#
# What this does:
#   1. Locates or installs pipx, installs binarypilot-agent into it.
#   2. Ensures ~/.local/bin (or your platform equivalent) is on PATH going forward
#      via your shell rc file.
#   3. Pulls the sandbox image (docker pull ghcr.io/0xida/binarypilot-sandbox:1.2.0).
#   4. Seeds ~/.binarypilot/cli-config.json if you set HTB_TOKEN / FLAGYARD_USERNAME /
#      FLAGYARD_PASSWORD / FLAGYARD_ACCESS_TOKEN / BINARYPILOT_LLM / LLM_API_KEY in env.
#
# Idempotent: re-running is safe.

set -euo pipefail

APP=binarypilot
PKG=binarypilot-agent
IMAGE="ghcr.io/0xida/binarypilot-sandbox:1.2.0"
CONFIG_DIR="${BINARYPILOT_CONFIG_DIR:-$HOME/.binarypilot}"
CONFIG_FILE="${BINARYPILOT_CONFIG_FILE:-$CONFIG_DIR/cli-config.json}"

MUTED='\033[0;2m'
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m'

say()  { echo -e "${MUTED}$1${NC}"; }
ok()   { echo -e "${GREEN}✓ $1${NC}"; }
warn() { echo -e "${YELLOW}⚠ $1${NC}"; }
die()  { echo -e "${RED}✗ $1${NC}" >&2; exit 1; }
step() { echo -e "\n${CYAN}$1${NC}"; }

[ "$(uname -s)" = "Linux" ] || [ "$(uname -s)" = "Darwin" ] || die "Only Linux/macOS supported (Windows: use WSL)"

have() { command -v "$1" >/dev/null 2>&1; }

# -----------------------------------------------------------------------------
# 1. pipx
# -----------------------------------------------------------------------------

step "1. pipx"
if ! have pipx; then
  say "pipx not found — installing..."
  if have python3; then
    python3 -m pip install --user --quiet pipx || die "pip install --user pipx failed"
    python3 -m pipx ensurepath --quiet || true
  else
    die "python3 required. Install python3, then re-run."
  fi
fi
# PATH for this session even if rc file hasn't been re-sourced
PIPX_BIN="${PIPX_BIN:-$HOME/.local/bin}"
export PATH="$PIPX_BIN:$PATH"
have pipx || die "pipx still not resolvable — open a new shell and re-run"

# -----------------------------------------------------------------------------
# 2. binarypilot
# -----------------------------------------------------------------------------

step "2. binarypilot"
INSTALL_SOURCE="${BINARYPILOT_SOURCE:-$PKG}"   # override for local repo: BINARYPILOT_SOURCE=/path/to/repo
if pipx list --short 2>/dev/null | grep -q "^${PKG} "; then
  say "upgrading existing ${PKG}"
  pipx upgrade --quiet "${PKG}" || pipx install --force --quiet "${INSTALL_SOURCE}"
else
  say "installing ${INSTALL_SOURCE}"
  pipx install --quiet "${INSTALL_SOURCE}"
fi
ok "binarypilot $( "$HOME/.local/bin/$APP" --version 2>/dev/null | head -1 || echo installed)"

# -----------------------------------------------------------------------------
# 3. PATH (shell rc)
# -----------------------------------------------------------------------------

step "3. PATH"
write_path_to_rc() {
  local rc="$1" line="$2"
  if [ -f "$rc" ] && grep -Fxq "$line" "$rc"; then
    return 0
  fi
  printf '\n# binarypilot\n%s\n' "$line" >> "$rc"
  say "appended to $rc"
}
case "$(basename "${SHELL:-sh}")" in
  zsh)  write_path_to_rc "$HOME/.zshrc"   'export PATH="$HOME/.local/bin:$PATH"' ;;
  fish) write_path_to_rc "$HOME/.config/fish/config.fish" 'fish_add_path $HOME/.local/bin' ;;
  *)    write_path_to_rc "$HOME/.bashrc"  'export PATH="$HOME/.local/bin:$PATH"' ;;
esac

# -----------------------------------------------------------------------------
# 4. Docker image
# -----------------------------------------------------------------------------

step "4. Sandbox image"
if ! have docker; then
  warn "docker CLI not on PATH — install Docker and run: docker pull $IMAGE"
else
  if docker image inspect "$IMAGE" >/dev/null 2>&1; then
    say "image already present, checking for updates"
    docker pull -q "$IMAGE" >/dev/null || warn "pull failed (still have a local copy)"
  else
    say "pulling $IMAGE (~2 GB — grab coffee)"
    docker pull "$IMAGE" || warn "pull failed — try: docker pull $IMAGE"
  fi
fi

# -----------------------------------------------------------------------------
# 5. cli-config.json (credentials)
# -----------------------------------------------------------------------------

step "5. Config (optional — env vars seed ~/.binarypilot/cli-config.json)"
CONFIG_DIR=$(dirname "$CONFIG_FILE")
mkdir -p "$CONFIG_DIR"
have python3 || die "python3 required"

CONFIG_FILE="$CONFIG_FILE" BINARYPILOT_LLM="${BINARYPILOT_LLM:-}" LLM_API_KEY="${LLM_API_KEY:-}" LLM_API_BASE="${LLM_API_BASE:-}" LLM_REASONING_EFFORT="${LLM_REASONING_EFFORT:-}" HTB_TOKEN="${HTB_TOKEN:-}" FLAGYARD_USERNAME="${FLAGYARD_USERNAME:-}" FLAGYARD_PASSWORD="${FLAGYARD_PASSWORD:-}" FLAGYARD_ACCESS_TOKEN="${FLAGYARD_ACCESS_TOKEN:-}" FLAGYARD_API_BASE="${FLAGYARD_API_BASE:-}" PERPLEXITY_API_KEY="${PERPLEXITY_API_KEY:-}" python3 - <<'PY'
import json, os, pathlib

path = pathlib.Path(os.environ["CONFIG_FILE"])
existing = {}
if path.exists():
    try:
        existing = json.loads(path.read_text())
    except json.JSONDecodeError:
        path.unlink()

env_block = existing.get("env", {})
candidates = [
    "BINARYPILOT_LLM",
    "LLM_API_KEY",
    "LLM_API_BASE",
    "LLM_REASONING_EFFORT",
    "HTB_TOKEN",
    "FLAGYARD_USERNAME",
    "FLAGYARD_PASSWORD",
    "FLAGYARD_ACCESS_TOKEN",
    "FLAGYARD_API_BASE",
    "PERPLEXITY_API_KEY",
]
for key in candidates:
    v = os.environ.get(key)
    if v:
        env_block[key] = v

captured = [k for k in candidates if k in env_block]
if captured:
    existing["env"] = env_block
    path.write_text(json.dumps(existing, indent=2))
    path.chmod(0o600)
    print(f"wrote {len(captured)} env var(s) to {path}: {', '.join(captured)}")
else:
    print("no env vars to capture — skipping cli-config.json")
PY

# -----------------------------------------------------------------------------
# Done
# -----------------------------------------------------------------------------

echo ""
step "✅ BinaryPilot ready"
echo "  binarypilot --challenge https://app.hackthebox.com/challenges/15"
echo "  binarypilot --challenge \"Lame\" --platform htb"
echo "  binarypilot --challenge \"Web 01\" --platform flagyard"
echo ""
say "New shells load binarypilot automatically. Current shell: run"
say "  source ~/.$(basename "${SHELL:-sh}")rc"
say "Docs: https://github.com/0xIDA/binarypilot"
