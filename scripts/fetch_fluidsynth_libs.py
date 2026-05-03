#!/usr/bin/env python3
"""
Download official FluidSynth Windows release artifacts and extract the runtime
DLLs into src/scamp/_thirdparty/windows_libs/.

Usage:
    python3 scripts/fetch_fluidsynth_libs.py                 # fetch all windows targets
    python3 scripts/fetch_fluidsynth_libs.py windows-x64
    python3 scripts/fetch_fluidsynth_libs.py --version 2.5.4 --inspect

The script is stdlib-only.

Note on macOS / Linux:
    FluidSynth's GitHub releases ship Windows, iOS, and Android prebuilts only;
    there is no official macOS or Linux artifact. Those platforms require a
    build step:
      - macOS: build via cibuildwheel on a GitHub Actions macos runner, or pull
        Homebrew bottles (libfluidsynth + transitive deps) and run delocate.
      - Linux: build inside a manylinux container during cibuildwheel and let
        auditwheel bundle the result.
    This script intentionally does not try to handle those.
"""

from __future__ import annotations

import argparse
import io
import shutil
import sys
import tempfile
import urllib.error
import urllib.request
import zipfile
from pathlib import Path

DEFAULT_VERSION = "2.5.4"

REPO_ROOT = Path(__file__).resolve().parent.parent
THIRDPARTY = REPO_ROOT / "src" / "scamp" / "_thirdparty"


def asset_filename(version: str, arch: str) -> str:
    """
    FluidSynth's Windows asset naming changed between 2.4.x and 2.5.x:

      2.4.x: fluidsynth-{ver}-win10-x64.zip          (no 'v' prefix, no variant)
             fluidsynth-{ver}-winXP-x86.zip          (x86 used winXP target)
      2.5.x: fluidsynth-v{ver}-win10-{arch}-cpp11.zip   (cpp11 = lighter, no glib)
             fluidsynth-v{ver}-win10-{arch}-glib.zip    (legacy glib build)

    We use the cpp11 variant on 2.5+ — it has fewer transitive DLL deps.
    """
    major_minor = tuple(int(x) for x in version.split(".")[:2])
    if major_minor >= (2, 5):
        return f"fluidsynth-v{version}-win10-{arch}-cpp11.zip"
    # 2.4.x and older
    if arch == "x86":
        return f"fluidsynth-{version}-winXP-x86.zip"
    return f"fluidsynth-{version}-win10-{arch}.zip"


# Target name -> (arch within the asset, destination subdir under _thirdparty/)
TARGETS: dict[str, tuple[str, str]] = {
    "windows-x64": ("x64", "windows_libs"),
    "windows-x86": ("x86", "windows_libs"),
}


def asset_url(version: str, arch: str) -> str:
    return (
        f"https://github.com/FluidSynth/fluidsynth/releases/download/"
        f"v{version}/{asset_filename(version, arch)}"
    )


def download(url: str) -> bytes:
    print(f"  downloading {url}")
    with urllib.request.urlopen(url) as resp:
        return resp.read()


def list_zip(data: bytes) -> list[str]:
    with zipfile.ZipFile(io.BytesIO(data)) as zf:
        return zf.namelist()


def extract_dlls(data: bytes, dest: Path) -> list[Path]:
    """Extract all .dll files from the zip flat-into dest. Return list of written paths."""
    dest.mkdir(parents=True, exist_ok=True)
    written: list[Path] = []
    with zipfile.ZipFile(io.BytesIO(data)) as zf:
        for name in zf.namelist():
            if name.endswith("/") or not name.lower().endswith(".dll"):
                continue
            out = dest / Path(name).name
            with zf.open(name) as src, open(out, "wb") as dst:
                shutil.copyfileobj(src, dst)
            written.append(out)
    return written


def stage_target(target: str, version: str, inspect: bool) -> None:
    arch, dest_subdir = TARGETS[target]
    url = asset_url(version, arch)
    dest_dir = THIRDPARTY / dest_subdir

    print(f"\n[{target}] FluidSynth {version}")
    data = download(url)

    if inspect:
        names = list_zip(data)
        dlls = [n for n in names if n.lower().endswith(".dll")]
        print(f"  archive contains {len(names)} entries, {len(dlls)} DLLs:")
        for n in dlls:
            print(f"    {n}")
        return

    written = extract_dlls(data, dest_dir)
    if not written:
        print("  WARNING: no DLLs found in archive")
        return
    print(f"  wrote {len(written)} DLLs -> {dest_dir.relative_to(REPO_ROOT)}/")
    for p in written:
        print(f"    {p.name}")


def main() -> int:
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "targets", nargs="*", choices=list(TARGETS) + [[]], default=[],
        help="targets to fetch (default: all)",
    )
    parser.add_argument("--version", default=DEFAULT_VERSION,
                        help=f"FluidSynth version (default: {DEFAULT_VERSION})")
    parser.add_argument("--inspect", action="store_true",
                        help="report what's in the archive without copying anything")
    args = parser.parse_args()

    targets = args.targets or list(TARGETS)
    print(f"Targets: {targets}")
    print(f"Destination: {THIRDPARTY.relative_to(REPO_ROOT)}/")

    for target in targets:
        try:
            stage_target(target, args.version, args.inspect)
        except urllib.error.HTTPError as e:
            print(f"  ERROR fetching {target}: {e}")
            return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
