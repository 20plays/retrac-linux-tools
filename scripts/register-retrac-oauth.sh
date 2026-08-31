#!/usr/bin/env bash
set -euo pipefail

P="${WINEPREFIX:-$HOME/Games/retrac-wine}"
EXE="$P/drive_c/Program Files/Retrac/retrac.exe"
BIN_DIR="$HOME/.local/bin"
APP_DIR="$HOME/.local/share/applications"
WRAPPER="$BIN_DIR/retrac-wine-uri"
DESKTOP="$APP_DIR/retrac-wine.desktop"

command -v xdg-mime >/dev/null || {
  echo "Missing required command: xdg-mime" >&2
  exit 1
}

[[ -f "$EXE" ]] || {
  echo "Retrac launcher not found: $EXE" >&2
  echo "Run scripts/setup-prefix.sh first." >&2
  exit 1
}

mkdir -p "$BIN_DIR" "$APP_DIR"

printf -v P_Q '%q' "$P"
printf -v EXE_Q '%q' "$EXE"

cat > "$WRAPPER" <<EOF
#!/usr/bin/env bash
set -euo pipefail
exec env WINEPREFIX=$P_Q wine $EXE_Q "\$@"
EOF
chmod 0755 "$WRAPPER"

cat > "$DESKTOP" <<EOF
[Desktop Entry]
Name=Retrac
Type=Application
NoDisplay=true
Terminal=false
Exec="$WRAPPER" %u
MimeType=x-scheme-handler/retrac;
EOF

xdg-mime default retrac-wine.desktop x-scheme-handler/retrac

if command -v kbuildsycoca6 >/dev/null; then
  kbuildsycoca6 >/dev/null
elif command -v update-desktop-database >/dev/null; then
  update-desktop-database "$APP_DIR" >/dev/null 2>&1 || true
fi

handler="$(xdg-mime query default x-scheme-handler/retrac || true)"
if [[ "$handler" != "retrac-wine.desktop" ]]; then
  echo "URI handler registration did not stick; current handler: ${handler:-<none>}" >&2
  exit 1
fi

echo "Registered retrac: URI handler -> $DESKTOP"
