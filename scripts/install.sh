#!/usr/bin/env bash
# BinaryPilot installer — curl | bash
#
#   curl -sSL https://idor.lol | bash
#
# What this does:
#   1. Locates or installs pipx, installs binarypilot-agent into it.
#   2. Ensures ~/.local/bin is on PATH going forward via your shell rc file.
#   3. Pulls the sandbox image (docker pull ghcr.io/0xida/binarypilot-sandbox:1.5.0).
#   4. Seeds ~/.binarypilot/cli-config.json from HTB_TOKEN / FLAGYARD_* / LLM env vars.
#
# Idempotent: re-running is safe.

set -euo pipefail

APP=binarypilot
PKG=binarypilot-agent
# Image tag tracks the package version — set both at once below so they never drift.
IMAGE=""
BINARYPILOT_VERSION=""
CONFIG_DIR="${BINARYPILOT_CONFIG_DIR:-$HOME/.binarypilot}"
CONFIG_FILE="${BINARYPILOT_CONFIG_FILE:-$CONFIG_DIR/cli-config.json}"
TOTAL_STEPS=5

# --- terminal capability ------------------------------------------------------
# Animate only on a real TTY with color support; stay plain in CI / pipes.
if [ -t 1 ] && [ -z "${NO_COLOR:-}" ] && [ "${TERM:-dumb}" != "dumb" ]; then
  FANCY=1
else
  FANCY=0
fi

if [ "$FANCY" = 1 ]; then
  BOLD=$'\033[1m';    DIM=$'\033[2m';    RESET=$'\033[0m'
  RED=$'\033[31m';    GREEN=$'\033[32m'; YELLOW=$'\033[33m'
  BLUE=$'\033[34m';   MAGENTA=$'\033[35m'; CYAN=$'\033[36m'
  GRAY=$'\033[90m'
else
  BOLD='' DIM='' RESET='' RED='' GREEN='' YELLOW='' BLUE='' MAGENTA='' CYAN='' GRAY=''
fi
CHECK="${GREEN}✓${RESET}"; CROSS="${RED}✗${RESET}"; WARN_I="${YELLOW}!${RESET}"
SPIN_PID=""

hide_cursor() { [ "$FANCY" = 1 ] && printf '\033[?25l' || true; }
show_cursor() { [ "$FANCY" = 1 ] && printf '\033[?25h' || true; return 0; }
cleanup()     { stop_spin; show_cursor; return 0; }
trap cleanup EXIT
trap 'stop_spin; show_cursor; echo; exit 130' INT

banner() {
  if [ "$FANCY" = 1 ]; then
    printf '%s\n' "${CYAN}${BOLD}"
    cat <<'EOF'
    ____  _                        ____  _ __      __
   / __ )(_)___  ____ ________  __/ __ \(_) /___  / /_
  / __  / / __ \/ __ `/ ___/ / / / /_/ / / / __ \/ __/
 / /_/ / / / / / /_/ / /  / /_/ / ____/ / / /_/ / /_
/_____/_/_/ /_/\__,_/_/   \__, /_/   /_/_/\____/\__/
                          /____/
EOF
    printf '%s' "$RESET"
    printf '         %s%sautonomous CTF solver%s  %s·%s  %s%sb0f.ru%s\n\n' \
      "$DIM" "$MAGENTA" "$RESET" "$GRAY" "$RESET" "$DIM" "$BLUE" "$RESET"
  else
    echo "== BinaryPilot installer =="
    echo ""
  fi
}

# spinner <text> — start; stop_spin [check|warn|cross] [text] — finish
spin() {
  [ "$FANCY" = 1 ] || return 0
  local text="$1" frames=('⠋' '⠙' '⠹' '⠸' '⠼' '⠴' '⠦' '⠧' '⠇' '⠏')
  hide_cursor
  (
    local i=0
    while :; do
      printf '\r  %s%s%s %s' "$CYAN" "${frames[$i]}" "$RESET" "$text"
      i=$(( (i + 1) % 10 ))
      sleep 0.08
    done
  ) &
  SPIN_PID=$!
}

stop_spin() {
  local sym="${1:-}" text="${2:-}"
  if [ -n "$SPIN_PID" ]; then
    kill "$SPIN_PID" 2>/dev/null || true
    wait "$SPIN_PID" 2>/dev/null || true
    SPIN_PID=""
    [ "$FANCY" = 1 ] && printf '\r\033[K'
  fi
  [ -n "$sym" ] && printf '  %b %s\n' "$sym" "$text"
  return 0
}

say()  { printf '     %s%s%s\n' "$DIM" "$1" "$RESET"; }
ok()   { printf '  %b %s\n' "$CHECK" "$1"; }
warn() { printf '  %b %s\n' "$WARN_I" "$1"; }
die()  { stop_spin; printf '\n  %b %s\n\n' "$CROSS" "$1" >&2; exit 1; }
step() {
  STEP_N=$((STEP_N + 1))
  printf '\n  %s%s[%d/%d]%s %s%s%s\n' "$GRAY" "$DIM" "$STEP_N" "$TOTAL_STEPS" "$RESET" "$BOLD" "$1" "$RESET"
}
hr()   { printf '  %s%s%s\n' "$GRAY" "────────────────────────────────────────────" "$RESET"; }

[ "$(uname -s)" = "Linux" ] || [ "$(uname -s)" = "Darwin" ] || die "Only Linux/macOS supported (Windows: use WSL)"
have() { command -v "$1" >/dev/null 2>&1; }

STEP_N=0
banner

# -----------------------------------------------------------------------------
# 1. pipx
# -----------------------------------------------------------------------------

step "pipx"
if have pipx; then
  ok "pipx $(pipx --version 2>/dev/null || echo found)"
else
  spin "installing pipx"
  if have python3; then
    python3 -m pip install --user --quiet pipx >/dev/null 2>&1 || { stop_spin; die "pip install --user pipx failed"; }
    python3 -m pipx ensurepath --quiet >/dev/null 2>&1 || true
  else
    stop_spin; die "python3 required. Install python3, then re-run."
  fi
  stop_spin "$CHECK" "pipx installed"
fi
# PATH for this session even if rc file hasn't been re-sourced
PIPX_BIN="${PIPX_BIN:-$HOME/.local/bin}"
export PATH="$PIPX_BIN:$PATH"
have pipx || die "pipx still not resolvable — open a new shell and re-run"

# -----------------------------------------------------------------------------
# 2. binarypilot
# -----------------------------------------------------------------------------

step "binarypilot agent"
INSTALL_SOURCE="${BINARYPILOT_SOURCE:-git+https://github.com/0xIDA/binarypilot.git}"   # override with a local path for dev: BINARYPILOT_SOURCE=/path/to/repo
if pipx list --short 2>/dev/null | grep -q "^${PKG} "; then
  spin "upgrading ${PKG}"
  pipx upgrade --quiet "${PKG}" >/dev/null 2>&1 || pipx install --force --quiet "${INSTALL_SOURCE}" >/dev/null 2>&1
  stop_spin "$CHECK" "upgraded"
else
  spin "installing ${PKG}"
  if pipx install --quiet "${INSTALL_SOURCE}" >/dev/null 2>&1; then
    stop_spin "$CHECK" "installed"
  else
    stop_spin
    die "pipx install failed — run manually: pipx install ${INSTALL_SOURCE}"
  fi
fi
ok "binarypilot $( "$HOME/.local/bin/$APP" --version 2>/dev/null | head -1 || echo installed)"

# Resolve the image tag from the actual installed version so the sandbox pull
# can never be out of sync with the CLI.
BINARYPILOT_VERSION=$("$HOME/.local/bin/$APP" --version 2>/dev/null | awk '{print $NF}' | tr -d '[:space:]')
if [ -z "$BINARYPILOT_VERSION" ]; then
  BINARYPILOT_VERSION="1.5.0"   # pre-upgrade fallback
  warn "could not resolve $(tput bold 2>/dev/null)binarypilot --version$(tput sgr0 2>/dev/null) — using image tag 1.5.0"
fi
IMAGE="ghcr.io/0xida/binarypilot-sandbox:${BINARYPILOT_VERSION}"

# -----------------------------------------------------------------------------
# 3. PATH (shell rc)
# -----------------------------------------------------------------------------

step "PATH"
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
ok "\$HOME/.local/bin on PATH"

# -----------------------------------------------------------------------------
# 4. Docker image
# -----------------------------------------------------------------------------

step "sandbox image"
if ! have docker; then
  warn "docker CLI not on PATH — install Docker and run: docker pull $IMAGE"
else
  if docker image inspect "$IMAGE" >/dev/null 2>&1; then
    spin "checking for image updates"
    docker pull -q "$IMAGE" >/dev/null 2>&1 || true
    stop_spin "$CHECK" "image up to date"
  else
    say "pulling ${DIM}$IMAGE${RESET} (~2 GB — grab coffee)"
    docker pull "$IMAGE" || warn "pull failed — retry: docker pull $IMAGE"
    hr
  fi
fi

# -----------------------------------------------------------------------------
# 5. cli-config.json (credentials)
# -----------------------------------------------------------------------------

step "config"
CONFIG_DIR=$(dirname "$CONFIG_FILE")
mkdir -p "$CONFIG_DIR"
have python3 || die "python3 required"

spin "seeding $CONFIG_FILE"
CONFIG_OUT=$(CONFIG_FILE="$CONFIG_FILE" BINARYPILOT_LLM="${BINARYPILOT_LLM:-}" LLM_API_KEY="${LLM_API_KEY:-}" LLM_API_BASE="${LLM_API_BASE:-}" LLM_REASONING_EFFORT="${LLM_REASONING_EFFORT:-}" HTB_TOKEN="${HTB_TOKEN:-}" FLAGYARD_USERNAME="${FLAGYARD_USERNAME:-}" FLAGYARD_PASSWORD="${FLAGYARD_PASSWORD:-}" FLAGYARD_ACCESS_TOKEN="${FLAGYARD_ACCESS_TOKEN:-}" FLAGYARD_API_BASE="${FLAGYARD_API_BASE:-}" PERPLEXITY_API_KEY="${PERPLEXITY_API_KEY:-}" python3 - <<'PY'
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
    print(f"OK|{len(captured)}|{', '.join(captured)}")
else:
    print("SKIP||")
PY
)
stop_spin
case "$CONFIG_OUT" in
  OK\|*) IFS='|' read -r _ n keys <<< "$CONFIG_OUT"
    ok "seeded $n env var(s): ${DIM}${keys}${RESET}" ;;
  *) say "no env vars set — skipping cli-config.json (configure later: binarypilot --help)" ;;
esac

# -----------------------------------------------------------------------------
# Done
# -----------------------------------------------------------------------------

echo ""
if [ "$FANCY" = 1 ]; then
  printf '  %s%s┌──────────────────────────────────────────┐%s\n' "$GREEN" "$BOLD" "$RESET"
  printf '  %s%s│%s   %s%s✓ BinaryPilot ready%s                    %s%s│%s\n' "$GREEN" "$BOLD" "$RESET" "$GREEN" "$BOLD" "$RESET" "$GREEN" "$BOLD" "$RESET"
  printf '  %s%s└──────────────────────────────────────────┘%s\n' "$GREEN" "$BOLD" "$RESET"
else
  echo "  ✓ BinaryPilot ready"
fi
echo ""
printf '  %stry it%s\n' "$DIM" "$RESET"
echo "    binarypilot --challenge https://app.hackthebox.com/challenges/15"
echo "    binarypilot --challenge \"Lame\" --platform htb"
echo "    binarypilot --challenge \"Web 01\" --platform flagyard"
echo ""
say "New shells load binarypilot automatically."
say "Current shell: source ~/.$(basename "${SHELL:-sh}")rc"
say "Docs: https://github.com/0xIDA/binarypilot"
echo ""
