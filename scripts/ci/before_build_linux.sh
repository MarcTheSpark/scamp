#!/bin/bash
# Runs inside cibuildwheel's manylinux container (AlmaLinux 8 / manylinux_2_28)
# once before each wheel is built.
#
# Strategy: install fluidsynth via the package manager, then copy the resulting
# libfluidsynth.so.3 (the *real* file, not a symlink) into _thirdparty/linux_libs/.
# That copy gets included in the wheel via package_data. cibuildwheel's post-
# build step (`auditwheel repair`) then inspects libfluidsynth.so.3, walks its
# DT_NEEDED chain (libsndfile, libglib, libgthread, libreadline, etc.), copies
# those deps into scamp.libs/ alongside the package, and patches RPATHs so
# everything resolves via $ORIGIN at load time.
#
# Audio-driver libraries (libasound, libpulse, libjack) are intentionally NOT
# bundled — fluidsynth dlopens its audio backend at runtime based on the
# audio.driver setting, so it has no hard DT_NEEDED reference to them. They
# come from the user's system, which is correct: only the user knows whether
# they want ALSA, Pulse, JACK, or PipeWire output.
set -euo pipefail

THIRDPARTY_DIR="$(cd "$(dirname "$0")/../../src/scamp/_thirdparty" && pwd)"
LINUX_LIBS="$THIRDPARTY_DIR/linux_libs"

# Wipe the other platforms' lib dirs so this Linux wheel doesn't ship
# Windows DLLs or macOS dylibs as dead weight.
rm -f "$THIRDPARTY_DIR/mac_libs"/*.dylib
rm -f "$THIRDPARTY_DIR/windows_libs"/*.dll

# fluidsynth lives in EPEL on AlmaLinux 8
dnf install -y epel-release
dnf install -y fluidsynth

# Find the real .so file (resolve symlinks like libfluidsynth.so -> .so.3 -> .so.3.x.y)
LIBFLUIDSYNTH=$(readlink -f /usr/lib64/libfluidsynth.so.3)
echo "Resolved libfluidsynth to: $LIBFLUIDSYNTH"

mkdir -p "$LINUX_LIBS"
rm -f "$LINUX_LIBS"/*.so*

# Copy as libfluidsynth.so.3 (the SONAME) so dlopen finds it under that name.
cp -L "$LIBFLUIDSYNTH" "$LINUX_LIBS/libfluidsynth.so.3"
echo "Bundled:"
ls -la "$LINUX_LIBS"
