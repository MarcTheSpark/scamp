#  ++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++  #
#  This file is part of SCAMP (Suite for Computer-Assisted Music in Python)                      #
#  Copyright © 2020 Marc Evanstein <marc@marcevanstein.com>.                                     #
#                                                                                                #
#  This program is free software: you can redistribute it and/or modify it under the terms of    #
#  the GNU General Public License as published by the Free Software Foundation, either version   #
#  3 of the License, or (at your option) any later version.                                      #
#                                                                                                #
#  This program is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY;     #
#  without even the implied warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.     #
#  See the GNU General Public License for more details.                                          #
#                                                                                                #
#  You should have received a copy of the GNU General Public License along with this program.    #
#  If not, see <http://www.gnu.org/licenses/>.                                                   #
#  ++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++  #
"""
Regenerate INDEX.md from the examples' own docstrings.

Each example carries a short docstring (summary, plus an optional "Tags:" line of
comma-separated feature tags). This script collects them, scans each file for usage of
scamp's public API, and writes INDEX.md: a feature -> examples table (inverted from the
tags) followed by per-folder entries. Adding an example therefore means writing one file
with its docstring -- never editing the index by hand.

Run from anywhere: python3 regenerate_index.py
(Requires scamp importable, for the public-API name list.)
"""

import re
import sys
import pathlib

EXAMPLES_DIR = pathlib.Path(__file__).parent
INDEX_PATH = EXAMPLES_DIR / "INDEX.md"

# Folders in presentation order, each with a one-line blurb for its section heading.
FOLDERS = {
    "Tutorial": "A curated, teaching set introducing the key features of SCAMP.",
    "Assorted": "A grab bag of scripts showing idiomatic patterns, and methods of connecting SCAMP with "
                "other frameworks and software (MIDI input/output, PyQt, Max, SuperCollider).",
    "ScampExtensions": "Examples exercising the optional `scamp_extensions` package "
                       "(scales, playback utilities, algorithmic power tools).",
    "Compositions": "Full pieces and reconstructions of existing works.",
    "JunkDrawer": "Uncurated scratch scripts, kept for reference only. Not indexed by feature.",
}

# Folder whose scripts are listed but left out of the feature table and API scan.
UNINDEXED = "JunkDrawer"

DOCSTRING_RE = re.compile(r'"""(.*?)"""', re.DOTALL)


def parse_docstring(path):
    """Return (summary, tags) from the file's first docstring; tags is a possibly-empty list."""
    m = DOCSTRING_RE.search(path.read_text())
    if not m:
        return None, []
    lines = [ln.strip() for ln in m.group(1).strip().splitlines()]
    tags = []
    body = []
    for ln in lines:
        if ln.startswith("Tags:"):
            tags = [t.strip() for t in ln[len("Tags:"):].split(",") if t.strip()]
        elif ln.startswith("SCAMP Example:") or ln.startswith("SCAMP EXAMPLE:"):
            continue  # title line; the filename already conveys it
        else:
            body.append(ln)
    summary = " ".join(ln for ln in body if ln).strip()
    return summary, tags


def collect_api_names():
    """Public scamp API surface: module-level names plus public methods of the main classes."""
    import scamp
    callables, classes = set(), set()
    for name in dir(scamp):
        if name.startswith("_"):
            continue
        obj = getattr(scamp, name)
        if isinstance(obj, type):
            classes.add(name)
        elif callable(obj):
            callables.add(name)
    for cls_name in ("Session", "ScampInstrument", "Ensemble", "Clock", "Performance",
                     "PerformancePart", "Score", "Envelope", "NoteHandle", "ChordHandle"):
        cls = getattr(scamp, cls_name, None)
        if cls is not None:
            callables.update(n for n in vars(cls) if not n.startswith("_"))
    return callables, classes


def scan_api(path, callables, classes, limit=12):
    """Names of public scamp API actually used in the file, capped at `limit`."""
    text = path.read_text()
    used = {n for n in callables if re.search(rf"\b{re.escape(n)}\s*\(", text)}
    used |= {n for n in classes if re.search(rf"\b{re.escape(n)}\b", text)}
    listed = sorted(used)
    if len(listed) > limit:
        listed = listed[:limit] + ["..."]
    return listed


HEADER = """\
# SCAMP Examples Index

<!-- GENERATED FILE - do not edit. Regenerate with: python3 regenerate_index.py -->

A map of every example script in this folder, for humans and AI assistants alike.
Each entry gives a one-line summary (from the example's own docstring), its feature
tags, and the scamp API it exercises. Paths are relative to `scamp/examples/`.

**How to use it:** scan the *Feature -> examples* table to jump to a topic, then read
the per-folder entries for detail. `Tutorial/` is the curated teaching set -- prefer it
for canonical, minimal usage.

**To add an example:** just add the file, with a short docstring ending in a
`Tags: comma, separated, features` line -- then rerun `regenerate_index.py`.
"""


def main():
    callables, classes = collect_api_names()

    entries = {}   # folder -> list of (relpath, summary, tags, api)
    tag_map = {}   # tag -> list of relpath, in folder-priority order
    for folder in FOLDERS:
        folder_path = EXAMPLES_DIR / folder
        entries[folder] = []
        for path in sorted(folder_path.rglob("*.py")):
            if "__pycache__" in path.parts:
                continue
            rel = path.relative_to(EXAMPLES_DIR).as_posix()
            summary, tags = parse_docstring(path)
            if summary is None:
                print(f"WARNING: {rel} has no docstring; skipping", file=sys.stderr)
                continue
            api = scan_api(path, callables, classes) if folder != UNINDEXED else []
            entries[folder].append((rel, summary, tags, api))
            if folder != UNINDEXED:
                for tag in tags:
                    tag_map.setdefault(tag, []).append(rel)

    out = [HEADER]

    out.append("\n## Feature -> examples\n")
    out.append("| Feature | Examples |")
    out.append("| --- | --- |")
    for tag in sorted(tag_map, key=str.lower):
        files = ", ".join(f"`{f}`" for f in tag_map[tag])
        out.append(f"| {tag} | {files} |")

    for folder, blurb in FOLDERS.items():
        out.append(f"\n## `{folder}/`\n")
        out.append(blurb + "\n")
        for rel, summary, tags, api in entries[folder]:
            out.append(f"- **`{rel}`** — {summary}")
            details = []
            if tags:
                details.append("*tags:* " + ", ".join(tags))
            if api:
                details.append("*API:* " + ", ".join(f"`{a}`" for a in api))
            if details:
                out.append("  <br>" + " — ".join(details))

    companions = [p for p in sorted(EXAMPLES_DIR.rglob("*"))
                  if p.is_file() and p.suffix in (".scd", ".maxpat", ".json", ".mid")
                  and "__pycache__" not in p.parts and "SavedFiles" not in p.parts]
    if companions:
        out.append("\n## Non-Python companion files\n")
        out.append("SuperCollider scripts, Max patches, and saved data used by the examples above:\n")
        for p in companions:
            out.append(f"- `{p.relative_to(EXAMPLES_DIR).as_posix()}`")

    INDEX_PATH.write_text("\n".join(out) + "\n")

    n = sum(len(v) for v in entries.values())
    print(f"INDEX.md: {n} examples, {len(tag_map)} feature tags")
    singletons = [t for t, fs in tag_map.items() if len(fs) == 1]
    if singletons:
        print("tags used only once (typo check): " + ", ".join(sorted(singletons)))


if __name__ == "__main__":
    main()
