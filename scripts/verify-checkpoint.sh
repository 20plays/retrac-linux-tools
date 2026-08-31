#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
# shellcheck source=../repro/versions.env
source "$ROOT/repro/versions.env"

P="${WINEPREFIX:-$HOME/Games/retrac-wine}"
WORKDIR="${WORKDIR:-$HOME/retrac-wine-build/wine-staging}"
SRC="$WORKDIR/src/wine"
LOGROOT="$P/drive_c/ProgramData/Alea/Logs"

fail=0
warn=0

pass() { printf 'PASS  %s\n' "$*"; }
fail_check() { printf 'FAIL  %s\n' "$*"; fail=1; }
warn_check() { printf 'WARN  %s\n' "$*"; warn=1; }

if [[ -d "$SRC/.git" ]]; then
  if bash "$ROOT/scripts/verify-wine-source.sh" "$SRC" >/dev/null; then
    pass "pinned Wine source checkpoint"
  else
    fail_check "pinned Wine source checkpoint"
  fi
else
  warn_check "prepared Wine source tree not present; source verification skipped"
fi

if command -v wine >/dev/null; then
  wine_version="$(wine --version 2>/dev/null || true)"
  if [[ "$wine_version" == *"$WINE_VERSION"* ]]; then
    pass "installed Wine reports $wine_version"
  else
    fail_check "installed Wine does not report expected version $WINE_VERSION (got: ${wine_version:-<none>})"
  fi
else
  fail_check "wine command is unavailable"
fi

RETRAC_EXE="$P/drive_c/Program Files/Retrac/retrac.exe"
if [[ -f "$RETRAC_EXE" ]]; then
  pass "Retrac launcher installed"
else
  fail_check "Retrac launcher missing at expected path"
fi

sc_out="$(WINEPREFIX="$P" WINEDEBUG=-all wine sc query AleaAntiCheat 2>/dev/null || true)"
if grep -Eq 'STATE[[:space:]]*:[[:space:]]*4[[:space:]]+RUNNING' <<<"$sc_out"; then
  pass "AleaAntiCheat service is RUNNING"
else
  fail_check "AleaAntiCheat service is not RUNNING"
fi

logs_have() {
  local needle="$1"
  [[ -d "$LOGROOT" ]] || return 1
  grep -RaqF -- "$needle" "$LOGROOT" 2>/dev/null
}

if logs_have "Alea client signaled ready"; then
  pass "AleaClient ready marker present"
else
  fail_check "AleaClient ready marker not found"
fi

if logs_have "Launch succeeded"; then
  pass "AleaService launch-success marker present"
else
  fail_check "AleaService launch-success marker not found"
fi

if logs_have "Request completed successfully"; then
  pass "AleaService request-completed marker present"
else
  warn_check "AleaService request-completed marker not found"
fi

task_out="$(WINEPREFIX="$P" WINEDEBUG=-all wine tasklist 2>/dev/null || true)"
if grep -qi 'FortniteClient-Win64-Shipping.exe' <<<"$task_out"; then
  pass "protected Fortnite wrapper process is present"
else
  fail_check "protected Fortnite wrapper process not found (run while the current fatal dialog is open)"
fi

echo
if ((fail)); then
  echo "CHECKPOINT NOT REPRODUCED"
  echo "Fix the reproduction path before beginning new compatibility investigation."
  exit 1
fi

echo "CHECKPOINT REPRODUCED"
if ((warn)); then
  echo "One or more non-fatal verifier checks were skipped or unavailable."
fi
echo "Manual final observation: confirm the same later timeout/fatal dialog described in docs/current-status.md."
