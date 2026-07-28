#!/usr/bin/env python3
"""
Publish a GitHub Release for an already-pushed tag, with the release body taken
from this package's CHANGELOG.md.

The GitHub release body is the canonical copy of the release notes: the
sourcehut mirror has no notion of a release body, so the CHANGELOG section is
duplicated onto GitHub. This script does that mechanically instead of by hand.

    python3 scripts/publish_github_release.py v1.1.0 --dry-run   # inspect first
    python3 scripts/publish_github_release.py v1.1.0             # actually publish

Everything is derived from the repo, so this file is identical in every package:

  * package name / version  -> pyproject.toml
  * release notes           -> the matching section of CHANGELOG.md
  * GitHub owner/repo       -> the `origin` remote
  * assets                  -> dist-<version>/ if present, else dist/

It does NOT build, upload to PyPI, or push anything — the tag must already be
on origin, and the artifacts must already be built. Run it last.

Checks before publishing (each one is a mistake actually worth catching):

  * the tag's version matches pyproject.toml, so a stale version bump can't
    ship under the wrong tag
  * the tag exists locally *and* on origin, so `gh` can't silently invent a tag
    pointing at the default branch
  * every asset filename carries this exact version — dist/ accumulates wheels
    from past releases, and uploading those is the easy mistake here
  * the CHANGELOG section exists and isn't empty

Pure stdlib.
"""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
import tomllib
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent


def run(args: list[str], **kwargs) -> subprocess.CompletedProcess:
    """Run a command in the repo root, capturing output as text."""
    return subprocess.run(args, cwd=REPO_ROOT, capture_output=True, text=True, **kwargs)


def read_project_metadata() -> tuple[str, str]:
    """Return (package name, version) from pyproject.toml."""
    with (REPO_ROOT / "pyproject.toml").open("rb") as f:
        project = tomllib.load(f)["project"]
    return project["name"], project["version"]


def extract_changelog_section(version: str) -> str:
    """
    Return the body of CHANGELOG.md's section for `version`, without its heading.

    The heading itself is dropped because GitHub already shows the version as the
    release title; repeating it would print the version twice at the top.
    """
    changelog = (REPO_ROOT / "CHANGELOG.md").read_text(encoding="utf-8")
    match = re.search(
        rf"^## \[{re.escape(version)}\][^\n]*\n(.*?)(?=^## )",
        changelog, re.S | re.M,
    )
    if match is None:
        sys.exit(f"No '## [{version}]' section found in CHANGELOG.md")
    body = match.group(1).strip()
    if not body:
        sys.exit(f"The '## [{version}]' section of CHANGELOG.md is empty")
    return body


def resolve_assets_dir(version: str, override: str | None) -> Path | None:
    """
    Pick the directory holding the built artifacts.

    Prefers the version-suffixed `dist-<version>/` (where scamp collects wheels
    downloaded from the CI build) and falls back to plain `dist/`.
    """
    if override is not None:
        path = REPO_ROOT / override
        if not path.is_dir():
            sys.exit(f"assets directory not found: {path}")
        return path
    for candidate in (REPO_ROOT / f"dist-{version}", REPO_ROOT / "dist"):
        if candidate.is_dir() and any(p.is_file() for p in candidate.iterdir()):
            return candidate
    return None


def collect_assets(assets_dir: Path, version: str) -> list[Path]:
    """
    Return the files in `assets_dir`, aborting if any belongs to another version.

    dist/ is not self-cleaning, so it tends to accumulate wheels from previous
    releases; uploading those to the wrong release is the mistake this prevents.
    """
    assets = sorted(p for p in assets_dir.iterdir() if p.is_file())
    strays = [p for p in assets if f"-{version}-" not in p.name and f"-{version}." not in p.name]
    if strays:
        listing = "\n".join(f"    {p.name}" for p in strays)
        sys.exit(
            f"{assets_dir.name}/ contains files that are not version {version}:\n{listing}\n"
            f"Remove them (or pass --no-assets) so a past release's artifacts don't get "
            f"attached to this one."
        )
    return assets


def github_repo_slug() -> str:
    """Return 'owner/name' parsed from the origin remote."""
    result = run(["git", "remote", "get-url", "origin"])
    if result.returncode != 0:
        sys.exit("could not read the 'origin' remote — is this a git repo with a GitHub origin?")
    url = result.stdout.strip()
    match = re.search(r"github\.com[:/](?P<owner>[^/]+)/(?P<name>[^/]+?)(?:\.git)?$", url)
    if match is None:
        sys.exit(f"origin does not look like a GitHub remote: {url}")
    return f"{match['owner']}/{match['name']}"


def verify_tag(tag: str) -> None:
    """Abort unless `tag` exists both locally and on origin."""
    if run(["git", "rev-parse", "-q", "--verify", f"refs/tags/{tag}"]).returncode != 0:
        sys.exit(f"tag {tag} does not exist locally")
    result = run(["git", "ls-remote", "--tags", "origin", f"refs/tags/{tag}"])
    if result.returncode != 0:
        sys.exit(f"could not reach origin to check for {tag}:\n{result.stderr.strip()}")
    if not result.stdout.strip():
        sys.exit(f"tag {tag} is not on origin yet — push it first (git push origin {tag})")


def main() -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("tag", help="the release tag, e.g. v1.1.0 (must already be pushed)")
    parser.add_argument("--dry-run", action="store_true",
                        help="print the release notes and the assets that would be attached, "
                             "then exit without touching GitHub")
    parser.add_argument("--assets-dir",
                        help="directory of built artifacts to attach "
                             "(default: dist-<version>/ if it exists, else dist/)")
    parser.add_argument("--no-assets", action="store_true",
                        help="publish notes only, attaching no files")
    args = parser.parse_args()

    name, project_version = read_project_metadata()
    tag_version = args.tag[1:] if args.tag.startswith("v") else args.tag
    if tag_version != project_version:
        sys.exit(f"tag {args.tag} implies version {tag_version}, but pyproject.toml says "
                 f"{project_version}. Fix one or the other before releasing.")

    notes = extract_changelog_section(project_version)

    assets: list[Path] = []
    assets_dir = None
    if not args.no_assets:
        assets_dir = resolve_assets_dir(project_version, args.assets_dir)
        if assets_dir is not None:
            assets = collect_assets(assets_dir, project_version)

    title = f"{name} {project_version}"

    if args.dry_run:
        print(f"tag:     {args.tag}")
        print(f"repo:    {github_repo_slug()}")
        print(f"title:   {title}")
        if assets:
            print(f"assets:  {len(assets)} file(s) from {assets_dir}")
            for path in assets:
                print(f"    {path}")
        else:
            print("assets:  (none)")
        print(f"\n--- release notes ({len(notes.splitlines())} lines) "
              f"{'-' * 40}\n{notes}\n{'-' * 60}")
        print("\nDry run: nothing was published.")
        return 0

    verify_tag(args.tag)
    command = ["gh", "release", "create", args.tag,
               "--repo", github_repo_slug(),
               "--verify-tag",
               "--title", title,
               "--notes", notes,
               *(str(p) for p in assets)]
    result = subprocess.run(command, cwd=REPO_ROOT)
    if result.returncode != 0:
        return result.returncode
    print(f"Published {title} with {len(assets)} asset(s).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
