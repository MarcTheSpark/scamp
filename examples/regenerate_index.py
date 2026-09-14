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
Regenerate INDEX.md from the examples directory tree.

The directory layout *is* the organization: each top-level folder (besides Tutorial and the
JunkDrawer) is a topic; the folders inside it are its sections. A ``docs_order.txt`` in a
folder lists the order of its children -- sub-folders and/or examples -- and may cross-list
an example that lives elsewhere by giving its path from ``examples/`` (anything with a "/").
Children not listed follow, sorted by name. An example is one script, or one sub-folder of
scripts (a folder with no docs_order.txt of its own); its title/summary come from the
script docstring, or an about.txt for a folder.

This module also exposes the tree walk (iter_units, ordered_items, topic_dirs,
example_locations) that the docs build shares. Run from anywhere:
    python3 regenerate_index.py     (requires scamp importable, for the public-API list)
"""

import re
import pathlib
from pathlib import PurePosixPath

EXAMPLES_DIR = pathlib.Path(__file__).parent
INDEX_PATH = EXAMPLES_DIR / "INDEX.md"

TUTORIAL_DIR = "Tutorial"            # the curated teaching sequence, shown first, in order
EXCLUDE_TOPLEVEL = {"JunkDrawer"}    # scratch scripts, left out of the index entirely

DOCSTRING_RE = re.compile(r'"""(.*?)"""', re.DOTALL)
TITLE_RE = re.compile(r"SCAMP Example:\s*(.+)", re.IGNORECASE)


def slugify(text):
    """A flat, URL-safe token from a path or title."""
    return re.sub(r"[^0-9a-z]+", "_", text.lower()).strip("_")


def parse_docstring(path):
    """The summary from a script's first docstring (its 'SCAMP Example:' title line
    dropped), or '' if there is none."""
    m = DOCSTRING_RE.search(path.read_text())
    if not m:
        return ""
    body = [ln.strip() for ln in m.group(1).strip().splitlines()
            if not ln.strip().startswith(("SCAMP Example:", "SCAMP EXAMPLE:"))]
    return " ".join(ln for ln in body if ln).strip()


def title_of(path):
    """The 'SCAMP Example: ...' title if present, else a de-underscored file stem, with any
    trailing 'Example' dropped ('TimeVaryingParameter Example' -> 'TimeVaryingParameter')."""
    m = TITLE_RE.search(path.read_text())
    title = m.group(1).strip() if m else path.stem.replace("_", " ")
    return re.sub(r"\s+example$", "", title, flags=re.IGNORECASE)


def parse_about(folder):
    """(title, summary) from a folder's about.txt, or None if absent. The title is its
    'SCAMP Example:' line (or None); the summary is the rest of the body."""
    about = folder / "about.txt"
    if not about.exists():
        return None
    title, body = None, []
    for ln in (ln.strip() for ln in about.read_text().splitlines()):
        if ln.startswith("SCAMP Example:"):
            title = ln[len("SCAMP Example:"):].strip()
        else:
            body.append(ln)
    return title, " ".join(ln for ln in body if ln).strip()


# ---- directory-tree walk (shared with the docs build) ---------------------

def read_order(d):
    """The docs_order.txt entries of a grouping dir (comments and blanks dropped)."""
    f = d / "docs_order.txt"
    if not f.exists():
        return []
    return [ln.strip() for ln in f.read_text().splitlines()
            if ln.strip() and not ln.strip().startswith("#")]


def is_grouping(d):
    """A dir that groups examples/sections (has a docs_order.txt), rather than being one
    folder example itself."""
    return (d / "docs_order.txt").exists()


def _has_py(d):
    return any("__pycache__" not in p.parts for p in d.rglob("*.py"))


def _folder_pys(d):
    return sorted(p for p in d.rglob("*.py") if "__pycache__" not in p.parts)


def resolve_entry(entry, base):
    """A docs_order.txt line -> ('group', dir) or ('example', 'relpath'), or None if it
    doesn't resolve. A line containing '/' is a path from examples/ (a cross-reference); a
    bare name is a child of ``base``."""
    target = (EXAMPLES_DIR / entry) if "/" in entry else (base / entry)
    if not target.exists():
        return None
    if target.is_dir() and is_grouping(target):
        return ("group", target)
    return ("example", target.relative_to(EXAMPLES_DIR).as_posix())


def ordered_items(d):
    """Ordered ('group', dir) / ('example', relpath) for a grouping dir: docs_order.txt
    entries first, then any local children not already listed (sorted)."""
    def key(kind, node):
        return node if kind == "example" else node.relative_to(EXAMPLES_DIR).as_posix()

    items, seen = [], set()
    for entry in read_order(d):
        r = resolve_entry(entry, d)
        if r is None:
            print(f"  WARNING: docs_order entry not found in {d.relative_to(EXAMPLES_DIR)}: {entry}")
            continue
        items.append(r)
        seen.add(key(*r))
    for child in sorted(d.iterdir(), key=lambda p: p.name):
        if child.name in ("__pycache__", "docs_order.txt", "about.txt"):
            continue
        if child.is_file() and child.suffix == ".py":
            k = child.relative_to(EXAMPLES_DIR).as_posix()
            if k not in seen:
                items.append(("example", k)); seen.add(k)
        elif child.is_dir() and (is_grouping(child) or _has_py(child)):
            k = child.relative_to(EXAMPLES_DIR).as_posix()
            if k not in seen:
                items.append(("group" if is_grouping(child) else "example", child if is_grouping(child) else k))
                seen.add(k)
    return items


def iter_units(root):
    """Yield each example's path (a script .py, or a folder-example directory) in root's
    tree, excluding JunkDrawer. Recurses through grouping dirs (and Tutorial); a non-grouping
    dir with .py is one folder example."""
    for child in sorted(root.iterdir(), key=lambda p: p.name):
        if child.name == "__pycache__":
            continue
        if root == EXAMPLES_DIR and child.name in EXCLUDE_TOPLEVEL:
            continue
        if child.is_file() and child.suffix == ".py":
            if root != EXAMPLES_DIR:             # loose scripts at the root (this one) aren't examples
                yield child
        elif child.is_dir():
            if is_grouping(child) or (root == EXAMPLES_DIR and child.name == TUTORIAL_DIR):
                yield from iter_units(child)
            elif _has_py(child):
                yield child


def topic_dirs(root=EXAMPLES_DIR):
    """The topic directories in display order: root docs_order.txt first, then any other
    top-level dirs, excluding Tutorial and JunkDrawer."""
    skip = EXCLUDE_TOPLEVEL | {TUTORIAL_DIR, "__pycache__"}
    dirs, seen = [], set()
    for name in read_order(root):
        d = root / name
        if d.is_dir() and name not in skip:
            dirs.append(d); seen.add(name)
    for child in sorted(root.iterdir(), key=lambda p: p.name):
        if child.is_dir() and child.name not in skip and child.name not in seen:
            dirs.append(child); seen.add(child.name)
    return dirs


def example_locations():
    """{example relpath: [(topic, section_or_None), ...]} -- every place an example appears
    across the topic pages (its home listing included), in walk order."""
    loc = {}

    def walk(d, topic):
        for kind, node in ordered_items(d):
            if kind == "example":
                loc.setdefault(node, []).append((topic, d.name if d.name != topic else None))
            else:
                walk(node, topic)

    for td in topic_dirs():
        walk(td, td.name)
    return loc


# ---- example metadata + API scan ------------------------------------------

def unit_meta(rel):
    """(title, summary, script_paths) for the example at path ``rel`` (file or folder)."""
    p = EXAMPLES_DIR / rel
    if p.is_file():
        return title_of(p), parse_docstring(p), [p]
    pys = _folder_pys(p)
    main = next((q for q in pys if q.stem == p.name), None)
    about = parse_about(p)
    if about:
        return (about[0] or p.name.replace("_", " ").title()), about[1], pys
    if len(pys) == 1:
        return title_of(pys[0]), parse_docstring(pys[0]), pys
    if main:
        return title_of(main), "", pys
    return p.name.replace("_", " ").title(), "", pys


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
    """Public scamp API names used across the given file(s), capped at ``limit``."""
    text = "\n".join(p.read_text() for p in paths)
    used = {n for n in callables if re.search(rf"\b{re.escape(n)}\s*\(", text)}
    used |= {n for n in classes if re.search(rf"\b{re.escape(n)}\b", text)}
    listed = sorted(used)
    return listed[:limit] + ["..."] if len(listed) > limit else listed


HEADER = """\
# SCAMP Examples Index

<!-- GENERATED FILE - do not edit. Regenerate with: python3 regenerate_index.py -->

A map of every example in this folder, for humans and AI assistants alike. The directory
layout is the organization: each top-level folder (besides `Tutorial/`) is a topic, and the
folders within it are sections. An example is one script, or one sub-folder of scripts.
Order within a folder is set by its `docs_order.txt`; an example may be cross-listed under
several sections by referencing its path there. Paths are relative to `scamp/examples/`.

**To add an example:** drop the script (or folder) into the right section folder. To place
or order it, add its name to that folder's `docs_order.txt` (unlisted examples sort to the
end); to cross-list it elsewhere, add its path to another section's `docs_order.txt`.
"""


def main():
    callables, classes = collect_api_names()
    locations = example_locations()
    out = [HEADER]

    def emit_example(out, rel, homed):
        title, summary, pys = unit_meta(rel)
        if not homed:                            # a cross-reference: one line, points home
            out.append(f"- {title} — *(home: `{rel}`)*")
            return
        out.append(f"- **{title}** — `{rel}`")
        details = [summary] if summary else []
        api = scan_api(pys, callables, classes)
        if api:
            details.append("*API:* " + ", ".join(f"`{a}`" for a in api))
        elsewhere = [f"{t} › {s}" if s else t for t, s in locations.get(rel, [])
                     if PurePosixPath(rel).parent.name != (s or t)]
        if elsewhere:
            details.append("*also under:* " + ", ".join(elsewhere))
        if details:
            out.append("  <br>" + " — ".join(details))

    def walk(out, d, depth):
        drel = d.relative_to(EXAMPLES_DIR).as_posix()
        for kind, node in ordered_items(d):
            if kind == "group":
                out.append(f"\n{'#' * min(depth, 6)} {node.name}\n")
                walk(out, node, depth + 1)
            else:
                emit_example(out, node, PurePosixPath(node).parent.as_posix() == drel)

    # Tutorial: the teaching sequence, in order.
    out.append("\n## Tutorial\n")
    out.append("The curated teaching set -- work through it in order.\n")
    for path in iter_units(EXAMPLES_DIR / TUTORIAL_DIR):
        rel = path.relative_to(EXAMPLES_DIR).as_posix()
        emit_example(out, rel, True)

    # Topics, each with its sections.
    for td in topic_dirs():
        out.append(f"\n## {td.name}\n")
        walk(out, td, 3)

    companions = [p for p in sorted(EXAMPLES_DIR.rglob("*"))
                  if p.is_file() and p.suffix in (".scd", ".maxpat", ".json", ".mid")
                  and "__pycache__" not in p.parts and "SavedFiles" not in p.parts
                  and EXCLUDE_TOPLEVEL.isdisjoint(p.parts)]
    if companions:
        out.append("\n## Non-Python companion files\n")
        out.append("SuperCollider scripts, Max patches, and saved data used by the examples above:\n")
        for p in companions:
            out.append(f"- `{p.relative_to(EXAMPLES_DIR).as_posix()}`")

    INDEX_PATH.write_text("\n".join(out) + "\n")
    n_units = sum(1 for _ in iter_units(EXAMPLES_DIR))
    print(f"INDEX.md: {n_units} examples across {len(topic_dirs())} topics")


if __name__ == "__main__":
    main()
