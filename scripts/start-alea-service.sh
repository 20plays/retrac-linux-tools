#!/usr/bin/env bash
set -euo pipefail

P="${WINEPREFIX:-/home/sprite/Games/retrac-wine}"

WINEPREFIX="$P" wineserver -k || true
sleep 2
WINEPREFIX="$P" wineserver -p
WINEPREFIX="$P" wine sc start AleaAntiCheat
