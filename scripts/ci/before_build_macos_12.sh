#!/bin/bash
# Variant of before_build_macos.sh for use on a local macOS 12 (Monterey) box
# that already has fluidsynth installed. Homebrew on macOS 12 is no longer
# supported for prebuilt bottles, so `brew install fluidsynth` triggers a
# build-from-source of cmake + glib + libsndfile + libomp + ... which can take
# hours or hang. This script skips that and uses a pre-installed fluidsynth
# from MacPorts or a manual install.
#
# Resolution order:
#   1. $FLUIDSYNTH_PREFIX  (manual override; expects $FLUIDSYNTH_PREFIX/lib/libfluidsynth*.dylib)
#   2. /opt/local          (MacPorts)
#   3. /usr/local          (Homebrew on Intel — works if it had bottles)
#   4. /opt/homebrew       (Homebrew on Apple Silicon — unlikely on Monterey but tried last)
#
# Set MACOSX_DEPLOYMENT_TARGET=12.0 when invoking cibuildwheel so the wheel
# tag, delocate's check, and pip's install logic all agree.
#
# Usage from the repo root:
#     export CIBW_BEFORE_BUILD_MACOS="bash {project}/scripts/ci/before_build_macos_12.sh"
#     MACOSX_DEPLOYMENT_TARGET=12.0 pipx run cibuildwheel --platform macos --archs x86_64
#
# Or to bypass cibuildwheel and call this directly:
#     bash scripts/ci/before_build_macos_12.sh
set -euo pipefail

THIRDPARTY_DIR="$(cd "$(dirname "$0")/../../src/scamp/_thirdparty" && pwd)"
MAC_LIBS="$THIRDPARTY_DIR/mac_libs"

# Wipe other platforms' libs (parallel to before_build_macos.sh)
rm -f "$THIRDPARTY_DIR/linux_libs"/*.so* 2>/dev/null || true
rm -f "$THIRDPARTY_DIR/windows_libs"/*.dll 2>/dev/null || true

# Find the prefix that contains a usable fluidsynth.
find_prefix() {
    local candidates=()
    if [ -n "${FLUIDSYNTH_PREFIX:-}" ]; then
        candidates+=("$FLUIDSYNTH_PREFIX")
    fi
    candidates+=("/opt/local" "/usr/local" "/opt/homebrew")

    for p in "${candidates[@]}"; do
        if compgen -G "$p/lib/libfluidsynth*.dylib" >/dev/null; then
            echo "$p"
            return 0
        fi
    done
    return 1
}

PREFIX=$(find_prefix) || {
    echo "ERROR: could not find libfluidsynth*.dylib in /opt/local, /usr/local, /opt/homebrew, or \$FLUIDSYNTH_PREFIX/lib" >&2
    echo "Install fluidsynth via MacPorts ('sudo port install fluidsynth') or set FLUIDSYNTH_PREFIX to point at an install root." >&2
    exit 1
}
echo "Using fluidsynth from: $PREFIX"
ls -la "$PREFIX/lib/libfluidsynth"*.dylib

mkdir -p "$MAC_LIBS"
rm -f "$MAC_LIBS"/*.dylib

# Copy the resolved real files (cp -L follows symlinks). delocate will discover
# and bundle the transitive deps (glib, libsndfile, etc.) automatically during
# cibuildwheel's post-build step.
cp -L "$PREFIX/lib/libfluidsynth"*.dylib "$MAC_LIBS/"

echo "Bundled into mac_libs/:"
ls -la "$MAC_LIBS"
