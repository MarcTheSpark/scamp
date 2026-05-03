"""
Runs on the Windows GH Actions runner before each wheel is built.

Wipes the macOS and Linux lib dirs (so the resulting Windows wheel doesn't
ship dylibs and .so files as dead weight) and then downloads the FluidSynth
Windows DLL bundle into windows_libs/.

Pure Python (cross-platform invocable) so we don't have to worry about
cmd vs PowerShell vs Git Bash on the Windows runner.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
THIRDPARTY = REPO_ROOT / "src" / "scamp" / "_thirdparty"


def wipe(directory: Path, suffixes: tuple[str, ...]) -> None:
    if not directory.exists():
        return
    for child in directory.iterdir():
        if child.is_file() and any(child.name.endswith(s) for s in suffixes):
            child.unlink()


def main() -> int:
    wipe(THIRDPARTY / "mac_libs", (".dylib",))
    # On Linux the SOs may be named libfluidsynth.so.3 etc, so match by ".so" anywhere
    linux_dir = THIRDPARTY / "linux_libs"
    if linux_dir.exists():
        for child in linux_dir.iterdir():
            if child.is_file() and ".so" in child.name and child.name != ".gitkeep":
                child.unlink()

    fetch = REPO_ROOT / "scripts" / "fetch_fluidsynth_libs.py"
    return subprocess.call([sys.executable, str(fetch), "windows-x64"])


if __name__ == "__main__":
    sys.exit(main())
