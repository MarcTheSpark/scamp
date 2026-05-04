#!/bin/bash
# Runs inside cibuildwheel's manylinux container (AlmaLinux 9 / manylinux_2_34)
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

# fluidsynth lives in EPEL on AlmaLinux 9 (newer than the EPEL 8 one we
# previously used: fluidsynth 2.3.x with PulseAudio/PipeWire/JACK backends
# compiled in, vs EPEL 8's 2.1.8 which was ALSA-only).
dnf install -y epel-release
dnf install -y fluidsynth

# Verify which audio backends this build of fluidsynth supports. The list
# `fluidsynth --help` prints under "audio.driver" reflects what was compiled
# in. We want to see at least pulseaudio/pipewire/jack in there; ALSA-only
# would mean we need to switch base image or build fluidsynth from source.
echo "=== fluidsynth audio backends available ==="
fluidsynth --help 2>&1 | grep -A2 -i 'audio\.driver\|valid values' || true
echo "==========================================="

# Discover whichever libfluidsynth.so.<N> EPEL gave us (e.g. .so.2 on EL8's
# fluidsynth 2.1.x, .so.3 on newer). Pick the SONAME (e.g. libfluidsynth.so.2),
# not the unversioned symlink or the fully-versioned real file.
SONAME=$(ls /usr/lib64/libfluidsynth.so.* 2>/dev/null \
         | grep -E 'libfluidsynth\.so\.[0-9]+$' \
         | head -1)
if [ -z "$SONAME" ]; then
    echo "ERROR: no libfluidsynth.so.<N> found in /usr/lib64" >&2
    ls -la /usr/lib64/libfluidsynth* >&2 || true
    exit 1
fi
LIBFLUIDSYNTH=$(readlink -f "$SONAME")
echo "SONAME: $SONAME"
echo "Real file: $LIBFLUIDSYNTH"

mkdir -p "$LINUX_LIBS"
rm -f "$LINUX_LIBS"/*.so*

# Copy under the SONAME filename so dlopen and auditwheel can both find it
# under the name libfluidsynth advertises in its DT_SONAME field.
cp -L "$LIBFLUIDSYNTH" "$LINUX_LIBS/$(basename "$SONAME")"
echo "Bundled:"
ls -la "$LINUX_LIBS"
