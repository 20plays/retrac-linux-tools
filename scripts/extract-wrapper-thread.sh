#!/usr/bin/env bash
set -euo pipefail

TRACE="${1:-$HOME/retrac-debug/wrapper-relay.log}"
OUT="${2:-$HOME/retrac-debug/wrapper-thread-all.txt}"

M="$(grep -aEn 'Call user32\.MessageBoxW' "$TRACE" | tail -1 || true)"

if [[ -z "$M" ]]; then
  echo "No MessageBoxW call found in $TRACE" >&2
  exit 1
fi

N="$(printf '%s\n' "$M" | cut -d: -f1)"
TID="$(printf '%s\n' "$M" | sed -E 's/^[0-9]+:([0-9a-fA-F]{4}):.*/\1/')"

echo "MessageBox line: $N"
echo "Wrapper thread:  $TID"

sed -n "1,${N}p" "$TRACE" |
  grep -a "^${TID}:" > "$OUT"

echo "Wrote $OUT"
