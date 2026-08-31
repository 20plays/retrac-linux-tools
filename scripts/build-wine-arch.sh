#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
# shellcheck source=../repro/versions.env
source "$ROOT/repro/versions.env"

WORKDIR="${WORKDIR:-$HOME/retrac-wine-build/wine-staging}"
SYNCDEPS=0

usage() {
  cat <<EOF
Usage: $0 [--syncdeps]

Build the pinned Arch wine-staging 11.16 package with the Retrac compatibility
changes documented by this repository.

Environment:
  WORKDIR   packaging/build directory
            default: $HOME/retrac-wine-build/wine-staging
  MAKEFLAGS default: -j$(nproc)

--syncdeps asks makepkg/pacman to install missing build dependencies.
The script NEVER installs the completed Wine package.
EOF
}

while (($#)); do
  case "$1" in
    --syncdeps) SYNCDEPS=1 ;;
    -h|--help) usage; exit 0 ;;
    *) echo "Unknown argument: $1" >&2; usage >&2; exit 2 ;;
  esac
  shift
done

for cmd in git makepkg python sha256sum; do
  command -v "$cmd" >/dev/null || { echo "Missing required command: $cmd" >&2; exit 1; }
done

mkdir -p "$(dirname "$WORKDIR")"

if [[ ! -d "$WORKDIR/.git" ]]; then
  if [[ -e "$WORKDIR" ]]; then
    echo "WORKDIR exists but is not a git checkout: $WORKDIR" >&2
    exit 1
  fi
  git clone "$ARCH_WINE_STAGING_REPO" "$WORKDIR"
fi

git -C "$WORKDIR" fetch --all --tags
git -C "$WORKDIR" checkout --detach "$ARCH_WINE_STAGING_PACKAGING_COMMIT"

ACTUAL_PACKAGING_COMMIT="$(git -C "$WORKDIR" rev-parse HEAD)"
[[ "$ACTUAL_PACKAGING_COMMIT" == "$ARCH_WINE_STAGING_PACKAGING_COMMIT" ]] || {
  echo "Packaging commit mismatch." >&2
  exit 1
}

echo "==> Preparing pinned Arch wine-staging sources"
if ((SYNCDEPS)); then
  (cd "$WORKDIR" && makepkg -so --noconfirm)
else
  (cd "$WORKDIR" && makepkg -o)
fi

WINE_SRC="$WORKDIR/src/wine"
[[ -d "$WINE_SRC/.git" ]] || {
  echo "Prepared Wine source was not found at $WINE_SRC" >&2
  exit 1
}

ACTUAL_WINE_HEAD="$(git -C "$WINE_SRC" rev-parse HEAD)"
if [[ "$ACTUAL_WINE_HEAD" != "$WINE_UPSTREAM_COMMIT" ]]; then
  echo "Wrong Wine source revision." >&2
  echo "expected: $WINE_UPSTREAM_COMMIT" >&2
  echo "actual:   $ACTUAL_WINE_HEAD" >&2
  exit 1
fi

echo "==> Applying Retrac compatibility source transformations"
python "$ROOT/scripts/apply-retrac-wine-11.16.py" "$WINE_SRC"

echo "==> Regenerating Wine server request protocol"
(cd "$WINE_SRC" && ./tools/make_requests)

echo "==> Checking resulting source diff"
git -C "$WINE_SRC" diff --check
git -C "$WINE_SRC" diff --binary > "$WORKDIR/retrac-wine-11.16-prebuild.diff"
sha256sum "$WORKDIR/retrac-wine-11.16-prebuild.diff" |
  tee "$WORKDIR/retrac-wine-11.16-prebuild.diff.sha256"

echo "==> Building package"
export MAKEFLAGS="${MAKEFLAGS:--j$(nproc)}"
(cd "$WORKDIR" && makepkg -e -f --nocheck)

echo
echo "Build completed. Package candidates:"
find "$WORKDIR" -maxdepth 1 -type f \( -name 'wine-staging-*.pkg.tar.zst' -o -name 'wine-staging-*.pkg.tar.xz' \) -print
echo
echo "Nothing was installed. Review the package, then install explicitly with:"
echo "  sudo pacman -U <package>"
