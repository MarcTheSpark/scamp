#!/bin/bash
# Runs on the macOS GH Actions runner before each wheel is built.
#
# Strategy: use Homebrew to install fluidsynth (and its transitive deps) on
# the runner, then copy the dylibs into _thirdparty/mac_libs/ so they get
# packaged into the wheel. cibuildwheel's post-build step (delocate-wheel)
# then rewrites the load paths and bundles any further deps it discovers.
#
# Each runner is single-arch (macos-13 = x86_64, macos-14 = arm64), so the
# Homebrew install matches the wheel arch we're building. We never cross-build.
set -euo pipefail

THIRDPARTY_DIR="$(cd "$(dirname "$0")/../../src/scamp/_thirdparty" && pwd)"
MAC_LIBS="$THIRDPARTY_DIR/mac_libs"

# Wipe the other platforms' lib dirs so this macOS wheel doesn't ship
# Windows DLLs or Linux .so files as dead weight.
rm -f "$THIRDPARTY_DIR/linux_libs"/*.so*
rm -f "$THIRDPARTY_DIR/windows_libs"/*.dll

brew update
brew install fluidsynth

# Find the install prefix Homebrew chose (differs between Intel and arm)
BREW_PREFIX="$(brew --prefix)"
echo "Homebrew prefix: $BREW_PREFIX"

mkdir -p "$MAC_LIBS"
# Wipe any previously-bundled dylibs so we don't ship stale x86_64 files in
# an arm64 wheel (or vice versa).
rm -f "$MAC_LIBS"/*.dylib

# Copy libfluidsynth itself. We grab the versioned dylib (e.g. libfluidsynth.3.dylib)
# rather than the symlink so that delocate sees a real file.
cp -L "$BREW_PREFIX/lib/libfluidsynth"*.dylib "$MAC_LIBS/" 2>/dev/null || true

# delocate-wheel will discover and bundle the transitive deps automatically
# during the post-build step, so we don't need to copy glib, libsndfile, etc.
# manually here.

ls -la "$MAC_LIBS"
