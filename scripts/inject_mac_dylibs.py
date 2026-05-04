#!/usr/bin/env python3
"""
Inject pre-delocated macOS dylibs (extracted from a prior cibuildwheel run on
a real Mac) into a freshly-built wheel, producing a self-contained mac wheel
without needing a Mac for this build.

Background: when cibuildwheel runs on an Intel Mac, delocate-wheel rewrites
the bundled dylibs' load paths to be self-contained (@loader_path-relative)
and ad-hoc signs them. Those dylibs are then "frozen" — they'll keep working
when copied into any future wheel, as long as their relative paths inside the
wheel are preserved. So once you've done one Intel-Mac build, you can stash
the dylib tree and reuse it on Linux for subsequent releases.

Workflow:

  1. ONE TIME, on your Intel Mac:
        pipx run cibuildwheel --platform macos --archs x86_64
        # → wheelhouse/scamp-X.Y.Z-py3-none-macosx_12_0_x86_64.whl
        #   (exact platform tag depends on MACOSX_DEPLOYMENT_TARGET)
        unzip -d /tmp/wheel wheelhouse/scamp-*-x86_64.whl
        tar czf intel-mac-dylibs.tar.gz -C /tmp/wheel/scamp _thirdparty/mac_libs .dylibs
        # Stash intel-mac-dylibs.tar.gz somewhere durable.

  2. ON LINUX, for each subsequent release:
        # a) Build the wheel locally (tagged py3-none-linux_x86_64
        #    because of setup.py's BinaryDistribution + bdist_wheel shim):
        python -m build --wheel
        # b) Retag to claim macOS compatibility (use the same platform tag
        #    your Intel-Mac stash was built against):
        pipx run wheel tags --remove --platform-tag=macosx_12_0_x86_64 dist/scamp-*-py3-none-linux_x86_64.whl
        # c) Inject the stashed dylibs:
        python3 scripts/inject_mac_dylibs.py \
            --wheel dist/scamp-*-py3-none-macosx_12_0_x86_64.whl \
            --stash scripts/intel-mac-dylibs.tar.gz \
            --output dist/

The script extracts the wheel, lays the stash on top, recomputes the
dist-info/RECORD checksums, and repacks. RECORD is required to be accurate
per PEP 376 — pip refuses to install a wheel with mismatched hashes.

Pure stdlib. Re-run any time without changing the source tree.
"""

from __future__ import annotations

import argparse
import base64
import hashlib
import sys
import tarfile
import tempfile
import zipfile
from pathlib import Path


def find_record_path(wheel_dir: Path) -> Path:
    """Return the path of the RECORD file inside the unpacked wheel."""
    matches = list(wheel_dir.glob("*.dist-info/RECORD"))
    if len(matches) != 1:
        raise RuntimeError(f"expected exactly one .dist-info/RECORD; found {matches}")
    return matches[0]


def hash_file(path: Path) -> tuple[str, int]:
    """Return (PEP-376-style sha256 hash string, file size)."""
    h = hashlib.sha256()
    size = 0
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
            size += len(chunk)
    digest = base64.urlsafe_b64encode(h.digest()).rstrip(b"=").decode("ascii")
    return f"sha256={digest}", size


def rewrite_record(wheel_dir: Path) -> None:
    """Regenerate the RECORD file with hashes/sizes for every file in the wheel."""
    record_path = find_record_path(wheel_dir)
    record_rel = record_path.relative_to(wheel_dir).as_posix()

    lines: list[str] = []
    for path in sorted(wheel_dir.rglob("*")):
        if not path.is_file():
            continue
        rel = path.relative_to(wheel_dir).as_posix()
        if rel == record_rel:
            # RECORD records itself with empty hash and size, per PEP 376.
            lines.append(f"{rel},,\n")
        else:
            digest, size = hash_file(path)
            lines.append(f"{rel},{digest},{size}\n")

    with record_path.open("w", encoding="utf-8", newline="\n") as f:
        f.writelines(lines)


def repack_wheel(wheel_dir: Path, output_path: Path) -> None:
    """Zip the contents of wheel_dir into output_path."""
    with zipfile.ZipFile(output_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for path in sorted(wheel_dir.rglob("*")):
            if path.is_file():
                zf.write(path, path.relative_to(wheel_dir).as_posix())


def main() -> int:
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--wheel", required=True, type=Path,
                        help="freshly-built wheel to inject dylibs into")
    parser.add_argument("--stash", required=True, type=Path,
                        help=".tar.gz of pre-delocated mac dylibs (_thirdparty/mac_libs/ + .dylibs/, "
                             "relative to the scamp/ package dir)")
    parser.add_argument("--output", required=True, type=Path,
                        help="output directory for the resulting wheel")
    args = parser.parse_args()

    if not args.wheel.is_file():
        sys.exit(f"wheel not found: {args.wheel}")
    if not args.stash.is_file():
        sys.exit(f"stash not found: {args.stash}")
    args.output.mkdir(parents=True, exist_ok=True)

    out_path = args.output / args.wheel.name

    with tempfile.TemporaryDirectory() as tmp:
        wheel_dir = Path(tmp) / "wheel"
        wheel_dir.mkdir()

        with zipfile.ZipFile(args.wheel) as zf:
            zf.extractall(wheel_dir)
        before = sum(1 for p in wheel_dir.rglob("*") if p.is_file())

        # The stash paths are relative to the scamp/ package dir, not the wheel
        # root, so extract into wheel_dir/scamp/.
        pkg_dir = wheel_dir / "scamp"
        if not pkg_dir.is_dir():
            sys.exit(f"expected scamp/ package directory inside wheel; not found at {pkg_dir}")
        with tarfile.open(args.stash, "r:gz") as tf:
            tf.extractall(pkg_dir)
        after = sum(1 for p in wheel_dir.rglob("*") if p.is_file())
        print(f"injected {after - before} files from {args.stash.name}")

        rewrite_record(wheel_dir)
        repack_wheel(wheel_dir, out_path)
        print(f"wrote {out_path}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
