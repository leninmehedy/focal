#!/usr/bin/env bash
# Focal installer — installs the `focal` CLI via pipx.
# Usage: bash <(curl -fsSL https://raw.githubusercontent.com/leninmehedy/focal/main/install.sh)
set -euo pipefail

RED='\033[0;31m'; YELLOW='\033[1;33m'; GREEN='\033[0;32m'; CYAN='\033[0;36m'; NC='\033[0m'
ok()   { echo -e "${GREEN}✔${NC}  $*"; }
warn() { echo -e "${YELLOW}⚠${NC}  $*"; }
die()  { echo -e "${RED}✖${NC}  $*" >&2; exit 1; }

echo -e "\n${CYAN}  ◎  Focal installer${NC}\n"

# ── Python 3.10+ ──────────────────────────────────────────────────────────────
if ! command -v python3 &>/dev/null; then
  die "Python 3 not found. Install it from https://python.org and re-run."
fi
PY_VER=$(python3 -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')
PY_MAJOR=$(echo "$PY_VER" | cut -d. -f1)
PY_MINOR=$(echo "$PY_VER" | cut -d. -f2)
if [[ "$PY_MAJOR" -lt 3 || ("$PY_MAJOR" -eq 3 && "$PY_MINOR" -lt 10) ]]; then
  die "Python 3.10+ required (found $PY_VER). Upgrade and re-run."
fi
ok "Python $PY_VER"

# ── gh CLI ────────────────────────────────────────────────────────────────────
if ! command -v gh &>/dev/null; then
  die "gh CLI not found. Install it from https://cli.github.com then re-run."
fi
ok "gh $(gh --version | head -1 | awk '{print $3}')"

GH_STATUS=$(gh auth status 2>&1 || true)
if ! echo "$GH_STATUS" | grep -q "Logged in"; then
  die "gh is not authenticated. Run: gh auth login"
fi
if ! echo "$GH_STATUS" | grep -q "project"; then
  warn "'project' scope may be missing. Run: gh auth refresh -s project"
else
  ok "gh authenticated with project scope"
fi

# ── pipx ─────────────────────────────────────────────────────────────────────
if ! command -v pipx &>/dev/null; then
  echo "  pipx not found — installing..."
  python3 -m pip install --user -q pipx
  python3 -m pipx ensurepath --quiet || true
  export PATH="$HOME/.local/bin:$PATH"
fi
ok "pipx $(pipx --version 2>/dev/null || echo '(installed)')"

# ── focal-cli ─────────────────────────────────────────────────────────────────
echo "  Installing focal-cli..."
if command -v focal &>/dev/null; then
  pipx upgrade focal-cli --quiet
  ok "focal upgraded to $(focal --version)"
else
  pipx install focal-cli --quiet
  ok "focal $(focal --version) installed"
fi

# ── Done ─────────────────────────────────────────────────────────────────────
echo -e "\n${GREEN}Installation complete!${NC}\n"
echo "Next step — run the setup wizard:"
echo -e "  ${CYAN}focal board setup${NC}\n"
echo "The wizard will:"
echo "  • Create a GitHub Projects board for you automatically (or use an existing one)"
echo "  • Ask which repos to watch for assigned issues"
echo "  • Write ~/.focal/config.json"
echo ""
echo "Then sync your board:"
echo -e "  ${CYAN}focal board sync${NC}\n"
echo "Full guide: https://github.com/leninmehedy/focal/blob/main/docs/user-guide.md"
echo ""
