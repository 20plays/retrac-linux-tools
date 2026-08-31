#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
# shellcheck source=../repro/versions.env
source "$ROOT/repro/versions.env"

SRC="${1:-$HOME/retrac-wine-build/wine-staging/src/wine}"

[[ -d "$SRC/.git" ]] || { echo "Not a Wine git checkout: $SRC" >&2; exit 1; }

fail=0

check_literal() {
  local rel="$1" literal="$2" label="$3"
  if grep -Fq "$literal" "$SRC/$rel"; then
    printf 'PASS  %s\n' "$label"
  else
    printf 'FAIL  %s\n' "$label"
    fail=1
  fi
}

head="$(git -C "$SRC" rev-parse HEAD)"
if [[ "$head" == "$WINE_UPSTREAM_COMMIT" ]]; then
  echo "PASS  Wine base commit $head"
else
  echo "FAIL  Wine base commit expected $WINE_UPSTREAM_COMMIT, got $head"
  fail=1
fi

check_literal dlls/wintrust/softpub.c   'FILE_SHARE_READ | FILE_SHARE_WRITE | FILE_SHARE_DELETE'   'WinTrust allows delete-sharing while preserving verification'

check_literal server/token.c   'SeAssignPrimaryTokenPrivilege = { 3, 0 }'   'SeAssignPrimaryTokenPrivilege LUID 3 exists'

check_literal dlls/ole32/ole2.c   'GetWindowThreadProcessId(hwnd, &pid);'   'RevokeDragDrop foreign-window guard exists'

check_literal dlls/ntdll/unix/security.c   'SERVER_START_REQ( set_token_session_id )'   'TokenSessionId setter is implemented'

check_literal server/user.h   'session id this winstation belongs to'   'winstations carry session IDs'

check_literal dlls/wtsapi32/wtsapi32.c   'static const WCHAR services_name[] = L"Services";'   'WTS enumerates service and console sessions'

check_literal programs/services/services.c   'service_session_id = 0'   'services start in session 0'

check_literal server/winstation.c   'CreateProcessAsUserW into another session'   'cross-session process winstation reset exists'

check_literal dlls/ntdll/unix/system.c   'case SystemBootEnvironmentInformation:  /* 90 */'   'SystemBootEnvironmentInformation is implemented'

# make_requests should have generated a request opcode/handler declaration.
if grep -Rqs 'set_token_session_id' "$SRC/server" "$SRC/include/wine"; then
  echo "PASS  generated server protocol contains set_token_session_id"
else
  echo "FAIL  generated server protocol does not contain set_token_session_id"
  fail=1
fi

echo
if ((fail)); then
  echo "Source checkpoint verification FAILED."
  exit 1
fi

echo "Source checkpoint verification PASSED."
