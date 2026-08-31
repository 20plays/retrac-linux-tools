#!/usr/bin/env bash
set -euo pipefail

P="${WINEPREFIX:-/home/sprite/Games/retrac-wine}"
EXE="$P/drive_c/Program Files/Retrac/retrac.exe"

exec env WINEPREFIX="$P" wine "$EXE"
