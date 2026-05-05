#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
SCAMP_DIR=$(dirname "$SCRIPT_DIR")
cd "$SCAMP_DIR"

python -m build --wheel
pipx run wheel tags --remove --platform-tag=macosx_12_0_x86_64 \
    dist/scamp-*-py3-none-linux_x86_64.whl
python3 "$SCRIPT_DIR/inject_mac_dylibs.py" \
    --wheel dist/scamp-*-py3-none-macosx_12_0_x86_64.whl \
    --stash "$SCRIPT_DIR/intel-mac-dylibs.tar.gz" \
    --output dist/
