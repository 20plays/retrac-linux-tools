#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
# shellcheck source=../repro/versions.env
source "$ROOT/repro/versions.env"

P="${WINEPREFIX:-$HOME/Games/retrac-wine}"
CACHE_DIR="${CACHE_DIR:-$HOME/.cache/retrac-linux-tools}"
MSI="$CACHE_DIR/Retrac_${RETRAC_VERSION}_x64_en-US.msi"
EXPECTED_EXE="$P/drive_c/Program Files/Retrac/retrac.exe"

for cmd in wine wineserver curl sha256sum; do
  command -v "$cmd" >/dev/null || {
    echo "Missing required command: $cmd" >&2
    exit 1
  }
done

mkdir -p "$CACHE_DIR" "$(dirname "$P")"

verify_msi() {
  printf '%s  %s\n' "$RETRAC_MSI_SHA256" "$MSI" | sha256sum -c - >/dev/null 2>&1
}

if [[ -f "$MSI" ]] && ! verify_msi; then
  echo "Cached Retrac MSI hash mismatch; removing it." >&2
  rm -f "$MSI"
fi

if [[ ! -f "$MSI" ]]; then
  echo "==> Downloading Retrac $RETRAC_VERSION"
  tmp="$MSI.part"
  rm -f "$tmp"
  curl --fail --location --proto '=https' --tlsv1.2        --output "$tmp" "$RETRAC_MSI_URL"
  mv "$tmp" "$MSI"
fi

if ! verify_msi; then
  echo "Retrac MSI SHA-256 does not match repro/versions.env" >&2
  echo "Refusing to install an unpinned installer." >&2
  exit 1
fi

echo "==> Retrac installer hash verified"
echo "==> Initializing Wine prefix: $P"
WINEPREFIX="$P" wineboot -u

echo "==> Starting interactive Retrac MSI install"
WINEPREFIX="$P" wine msiexec /i "$MSI"

if [[ ! -f "$EXPECTED_EXE" ]]; then
  echo >&2
  echo "Installer returned, but the expected launcher was not found:" >&2
  echo "  $EXPECTED_EXE" >&2
  echo "Do not guess a replacement path; inspect the installer result and update" >&2
  echo "the repository if Retrac changed its install layout." >&2
  exit 1
fi

echo
echo "Retrac is installed at:"
echo "  $EXPECTED_EXE"
echo
echo "Next:"
echo "  WINEPREFIX="$P" bash "$ROOT/scripts/register-retrac-oauth.sh""
echo "  WINEPREFIX="$P" bash "$ROOT/scripts/launch-retrac.sh""
echo
echo "Complete sign-in interactively and allow Retrac's normal Alea setup flow."
