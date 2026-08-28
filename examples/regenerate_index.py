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

An example is one script, or one subfolder (several files making a single example). Its
summary and "Tags:" line come from the script's docstring, or -- for a subfolder -- from
its about.txt. Tags are nested "domain/facet" (e.g. notation/spanners); a bare tag with no
slash is its own top-level domain. This script collects them, scans each example's source
for usage of scamp's public API, and writes INDEX.md: a feature -> examples section
(grouped by domain, inverted from the tags) followed by per-folder entries. Adding an
example therefore means writing one script (or about.txt) -- never editing the index by hand.

Run from anywhere: python3 regenerate_index.py
(Requires scamp importable, for the public-API name list.)
"""

import re
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

# Domain presentation order for the feature section; unlisted domains follow, alphabetized.
DOMAIN_ORDER = ["basics", "time", "pitch", "envelopes", "notation", "playback",
                "interactive", "composition", "scamp_extensions",
                "save and load", "visualization"]


def split_tag(tag):
    """"domain/facet" -> ("domain", "facet"); a bare tag -> ("domain", None)."""
    domain, _, facet = tag.partition("/")
    return domain.strip(), (facet.strip() or None)


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


def parse_about(folder):
    """(summary, tags) from a folder's about.txt, or None if absent. Same shape as a
    docstring: an optional 'SCAMP Example:' title line, a body, and a 'Tags:' line."""
    about = folder / "about.txt"
    if not about.exists():
        return None
    tags, body = [], []
    for ln in (ln.strip() for ln in about.read_text().splitlines()):
        if ln.startswith("Tags:"):
            tags = [t.strip() for t in ln[len("Tags:"):].split(",") if t.strip()]
        elif ln.startswith("SCAMP Example:"):
            continue
        else:
            body.append(ln)
    return " ".join(ln for ln in body if ln).strip(), tags


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


def scan_api(paths, callables, classes, limit=12):
    """Public scamp API names used across the given file(s), capped at `limit`."""
    text = "\n".join(p.read_text() for p in paths)
    used = {n for n in callables if re.search(rf"\b{re.escape(n)}\s*\(", text)}
    used |= {n for n in classes if re.search(rf"\b{re.escape(n)}\b", text)}
    listed = sorted(used)
    if len(listed) > limit:
        listed = listed[:limit] + ["..."]
    return listed


def collect_units(catroot):
    """Example units under a category folder: a standalone script, or a subfolder (one
    example spanning several files). Returns (display, pyfiles, summary, tags) tuples,
    sorted by path -- a subfolder's display path ends in '/'."""
    files, subfolders = [], {}
    for path in sorted(catroot.rglob("*.py")):
        if "__pycache__" in path.parts:
            continue
        if path.parent == catroot:
            files.append(path)
        else:
            subfolders.setdefault(path.parent, []).append(path)

    units = []
    for path in files:
        summary, tags = parse_docstring(path)
        units.append((path.relative_to(EXAMPLES_DIR).as_posix(), [path], summary or "", tags))
    for d in sorted(subfolders):
        pys = sorted(subfolders[d])
        summary, tags = folder_meta(d, pys)
        units.append((d.relative_to(EXAMPLES_DIR).as_posix() + "/", pys, summary, tags))
    return sorted(units, key=lambda u: u[0])


def folder_meta(d, pys):
    """(summary, tags) for a subfolder unit: about.txt is authoritative when present,
    else the folder-named (or lone) script supplies them; tags fall back to the union
    across scripts."""
    def merged_tags():
        merged = []
        for p in pys:
            for t in parse_docstring(p)[1]:
                if t not in merged:
                    merged.append(t)
        return merged

    about = parse_about(d)
    if about is not None:
        summary, tags = about
        return summary, (tags or merged_tags())
    main = next((p for p in pys if p.stem == d.name), None) or (pys[0] if len(pys) == 1 else None)
    if main is not None:
        summary, tags = parse_docstring(main)
        return summary or "", tags
    return "", merged_tags()


HEADER = """\
# SCAMP Examples Index

<!-- GENERATED FILE - do not edit. Regenerate with: python3 regenerate_index.py -->

A map of every example in this folder, for humans and AI assistants alike. Each entry
gives a one-line summary, its feature tags, and the scamp API it exercises. An example is
one script, or one subfolder (several files making a single example). Paths are relative
to `scamp/examples/`.

**How to use it:** scan the *Feature -> examples* section (grouped by domain) to jump to
a topic, then read the per-folder entries for detail. `Tutorial/` is the curated teaching
set -- prefer it for canonical, minimal usage.

**To add an example:** add a script whose docstring ends in a `Tags: comma, separated`
line (nested as `domain/facet`); for a multi-file example, put the summary and tags in the
folder's `about.txt` instead. Then rerun `regenerate_index.py`.
"""


def main():
    callables, classes = collect_api_names()

    entries = {}   # folder -> list of (display, summary, tags, api)
    tag_map = {}   # tag -> list of display, in folder-priority order
    for folder in FOLDERS:
        entries[folder] = []
        if folder == UNINDEXED:
            # Scratch drawer: list every script on its own, no feature table, no API scan.
            for path in sorted((EXAMPLES_DIR / folder).rglob("*.py")):
                if "__pycache__" in path.parts:
                    continue
                summary, tags = parse_docstring(path)
                entries[folder].append((path.relative_to(EXAMPLES_DIR).as_posix(),
                                        summary or "", tags, []))
            continue
        for display, pyfiles, summary, tags in collect_units(EXAMPLES_DIR / folder):
            api = scan_api(pyfiles, callables, classes)
            entries[folder].append((display, summary, tags, api))
            for tag in tags:
                tag_map.setdefault(tag, []).append(display)

    # Invert the flat tag map into domain -> {facet -> files} (plus files on bare domains).
    domains = {}
    for tag, files in tag_map.items():
        domain, facet = split_tag(tag)
        node = domains.setdefault(domain, {"files": [], "facets": {}})
        if facet is None:
            node["files"] = files
        else:
            node["facets"][facet] = files

    def domain_key(d):
        return (DOMAIN_ORDER.index(d) if d in DOMAIN_ORDER else len(DOMAIN_ORDER), d)

    out = [HEADER]

    out.append("\n## Feature -> examples\n")
    out.append("Grouped by domain. Within each entry, `Tutorial/` examples come first.\n")
    for domain in sorted(domains, key=domain_key):
        node = domains[domain]
        out.append(f"### {domain}\n")
        if node["files"]:
            out.append(", ".join(f"`{f}`" for f in node["files"]) + "\n")
        for facet in sorted(node["facets"], key=str.lower):
            files = ", ".join(f"`{f}`" for f in node["facets"][facet])
            out.append(f"- **{facet}** — {files}")
        if node["facets"]:
            out.append("")

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
