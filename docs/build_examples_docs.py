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
Generate the docs "Examples" section from the example scripts.

Writes docs/examples/index.rst (a Tutorial list in order, plus alphabetical, collapsible
tag groups) and one page per unit: a standalone script, or a dedicated subfolder shown as
a code box per script with a single folder-zip download. Each page offers a download (the
.py, or a .zip when companion files are needed) and embeds any captured media: an audio
player (_static/media/<rel>.mp3), score images (<rel>*.svg), and hand-authored YouTube
videos (example_media.toml). The JunkDrawer is left out. Reuses the docstring/tag parsing
from examples/regenerate_index.py.

Run from anywhere: python3 build_examples_docs.py
"""

import re
import sys
import shutil
import tomllib
import zipfile
import pathlib

DOCS_DIR = pathlib.Path(__file__).parent
EXAMPLES_DIR = DOCS_DIR.parent / "examples"
OUT_DIR = DOCS_DIR / "examples"
MEDIA_DIR = DOCS_DIR / "_static" / "media"          # audio/scores, captured by render_example_media.py
MEDIA_MANIFEST_PATH = DOCS_DIR / "example_media.toml"  # hand-authored video (YouTube) entries

sys.path.insert(0, str(EXAMPLES_DIR))
from regenerate_index import parse_docstring, FOLDERS  # noqa: E402


def _load_manifest():
    if MEDIA_MANIFEST_PATH.exists():
        with open(MEDIA_MANIFEST_PATH, "rb") as f:
            return tomllib.load(f)
    return {}


MEDIA_MANIFEST = _load_manifest()

# Folders to surface, in presentation order; the JunkDrawer is deliberately excluded.
INCLUDED = [f for f in FOLDERS if f != "JunkDrawer"]

LICENSE_DELIM = re.compile(r"^#\s*\++\s*#\s*$")
TITLE_RE = re.compile(r"SCAMP Example:\s*(.+)", re.IGNORECASE)


def slugify(text):
    """A flat, unique doc name from a path (with any .py suffix already removed)."""
    return re.sub(r"[^0-9a-z]+", "_", text.lower()).strip("_")


def title_of(path):
    """The 'SCAMP Example: ...' title if present, else a title-cased file stem."""
    m = TITLE_RE.search(path.read_text())
    return m.group(1).strip() if m else path.stem.replace("_", " ")


def source_body(path):
    """The example source with its docstring and GPL license block stripped."""
    text = path.read_text()
    text = re.sub(r'^\s*"""(.*?)"""', "", text, count=1, flags=re.DOTALL)
    lines = text.splitlines()
    delims = [i for i, ln in enumerate(lines) if LICENSE_DELIM.match(ln)]
    if len(delims) >= 2:
        del lines[delims[0]:delims[1] + 1]
    return "\n".join(lines).strip("\n")


def script_entry(path):
    """The per-script bits shown in a code box: filename, summary, source, rel path."""
    summary, _ = parse_docstring(path)
    return {"name": path.name, "summary": summary or "", "body": source_body(path),
            "rel": path.relative_to(EXAMPLES_DIR)}


def media_html(rel):
    """Raw-HTML rst embedding a script's audio (.mp3), score (.svg) and/or YouTube
    video for the docs page, or [] if it has none. Paths are relative to the built
    example page (examples/<slug>.html); media lives under the site's _static/."""
    mp3 = MEDIA_DIR / rel.with_suffix(".mp3")
    svgs = sorted((MEDIA_DIR / rel).parent.glob(rel.with_suffix("").name + "*.svg"))
    video = MEDIA_MANIFEST.get(rel.as_posix(), {}).get("youtube")
    if not (mp3.exists() or svgs or video):
        return []

    def url(p):
        return "../_static/media/" + p.relative_to(MEDIA_DIR).as_posix()

    # audio first on its own line, then any score stacked underneath it in a thin box
    out = [".. raw:: html", ""]
    if mp3.exists():
        out.append(f'   <div style="margin:0.6em 0"><audio controls preload="none" '
                   f'src="{url(mp3)}" style="width:100%;max-width:520px"></audio></div>')
    for vid in ([video] if isinstance(video, str) else (video or [])):
        out.append('   <div style="position:relative;padding-bottom:56.25%;height:0;'
                   'max-width:640px;margin:0.6em 0">'
                   f'<iframe src="https://www.youtube-nocookie.com/embed/{vid}" '
                   'style="position:absolute;top:0;left:0;width:100%;height:100%;border:0" '
                   'allowfullscreen></iframe></div>')
    for svg in svgs:
        out.append(f'   <div style="border:1px solid #ccc;padding:8px;margin:0.6em 0;'
                   f'display:inline-block;max-width:100%">'
                   f'<img src="{url(svg)}" alt="score" '
                   f'style="max-width:100%;height:auto;display:block"></div>')
    out.append("")
    return out


def companion_files(path):
    """Non-.py siblings a root-level script needs: a same-named sidecar, or a file /
    directory it references by name (e.g. leaf_loops.py -> LeafPoints/)."""
    src = path.read_text()
    out = []
    for sib in sorted(path.parent.iterdir()):
        if sib.name == path.name or "__pycache__" in sib.name:
            continue
        if sib.is_file() and sib.suffix == ".py":
            continue  # a separate example, not a companion
        if sib.is_dir() and any(sib.rglob("*.py")):
            continue  # another example's folder, not a companion
        if sib.stem == path.stem or sib.name in src:
            out.append(sib)
    return out


def collect():
    """Group the example scripts into units: a standalone script, or a dedicated
    subfolder holding one or more scripts plus its companion files."""
    units = []
    for folder in INCLUDED:
        catroot = EXAMPLES_DIR / folder
        subfolders = {}  # dir -> [script paths]
        for path in sorted(catroot.rglob("*.py")):
            if "__pycache__" in path.parts:
                continue
            if path.parent == catroot:
                units.append(file_unit(folder, path))
            else:
                subfolders.setdefault(path.parent, []).append(path)
        for d in sorted(subfolders):
            units.append(folder_unit(folder, d, sorted(subfolders[d])))
    return units


def file_unit(folder, path):
    rel = path.relative_to(EXAMPLES_DIR).as_posix()
    summary, tags = parse_docstring(path)
    if summary is None:
        summary = ""
    return {
        "folder": folder, "name": slugify(rel[:-len(".py")]), "display": rel,
        "title": title_of(path), "summary": summary, "tags": tags,
        "scripts": [script_entry(path)], "download": ("file", path),
    }


def folder_unit(folder, d, paths):
    """A subfolder shown as one page: a code box per script, one folder zip."""
    reldir = d.relative_to(EXAMPLES_DIR).as_posix()
    main = next((p for p in paths if p.stem == d.name), None)
    ordered = ([main] + [p for p in paths if p is not main]) if main else paths
    lead = ordered[0]  # the script whose docstring heads the page
    tags = []
    for p in ordered:
        for t in parse_docstring(p)[1]:
            if t not in tags:
                tags.append(t)
    if len(paths) == 1:
        title, summary = title_of(lead), (parse_docstring(lead)[0] or "")
    elif main:
        title, summary = title_of(main), (parse_docstring(main)[0] or "")
    else:
        title, summary = d.name.replace("_", " ").title(), ""
    return {
        "folder": folder, "name": slugify(reldir), "display": reldir + "/",
        "title": title, "summary": summary, "tags": tags,
        "scripts": [script_entry(p) for p in ordered], "download": ("folder", d),
    }


def write_download(unit):
    """Stage the unit's download asset under downloads/<name>/ and return the
    reStructuredText ``:download:`` line pointing at it."""
    dl_dir = OUT_DIR / "downloads" / unit["name"]
    dl_dir.mkdir(parents=True, exist_ok=True)
    kind, payload = unit["download"]

    if kind == "file" and not companion_files(payload):
        shutil.copyfile(payload, dl_dir / payload.name)
        target, label = f"downloads/{unit['name']}/{payload.name}", payload.name
    else:
        if kind == "folder":
            stem = payload.name
            members = [(p, p.relative_to(payload.parent).as_posix())
                       for p in sorted(payload.rglob("*"))
                       if p.is_file() and "__pycache__" not in p.parts]
        else:  # a script with companion data files
            stem = payload.stem
            members = [(payload, f"{stem}/{payload.name}")]
            for c in companion_files(payload):
                if c.is_file():
                    members.append((c, f"{stem}/{c.name}"))
                else:
                    for p in sorted(c.rglob("*")):
                        if p.is_file() and "__pycache__" not in p.parts:
                            members.append((p, f"{stem}/{c.name}/{p.relative_to(c).as_posix()}"))
        with zipfile.ZipFile(dl_dir / f"{stem}.zip", "w", zipfile.ZIP_DEFLATED) as zf:
            for source, arcname in members:
                zf.write(source, arcname)
        target, label = f"downloads/{unit['name']}/{stem}.zip", f"{stem}.zip"
    return f"*Download:* :download:`{label} <{target}>`"


def write_example_page(unit):
    title = unit["title"]
    out = [title, "=" * len(title), ""]
    out.append(f"*Example script:* ``examples/{unit['display']}``")
    out.append("")
    out.append(write_download(unit))
    out.append("")
    multi = len(unit["scripts"]) > 1
    if not multi:                                   # single script: media under the header
        out += media_html(unit["scripts"][0]["rel"])
    if unit["summary"] and not multi:
        out += [unit["summary"], ""]
    if unit["tags"]:
        out += ["*Tags:* " + ", ".join(unit["tags"]), ""]
    for script in unit["scripts"]:
        if multi and script["summary"]:
            out += [script["summary"], ""]
        if multi:                                   # folder page: each script's media by its box
            out += media_html(script["rel"])
        out.append(".. code-block:: python")
        out.append(f"   :caption: {script['name']}")
        out.append("")
        for ln in script["body"].splitlines():
            out.append("   " + ln if ln else "")
        out.append("")
    (OUT_DIR / f"{unit['name']}.rst").write_text("\n".join(out) + "\n")


def write_index(units):
    tutorial = [u for u in units if u["folder"] == "Tutorial"]
    tag_map = {}
    for u in units:
        for tag in u["tags"]:
            tag_map.setdefault(tag, []).append(u)

    out = [
        "Examples",
        "========",
        "",
        "A gallery of the example scripts that ship with SCAMP. The **tutorial** examples below",
        "are a progressively-ordered teaching set; the **by-tag** groups underneath collect every",
        "example (tutorial and beyond) by feature. Each links to a page showing its description and",
        "full source.",
        "",
        "Tutorial",
        "--------",
        "",
        "Work through these in order for a guided tour of the framework.",
        "",
    ]
    for u in tutorial:
        line = f"#. :doc:`{u['title']} <{u['name']}>`"
        if u["summary"]:
            line += f" — {u['summary']}"
        out.append(line)
    out += ["", "By tag", "------", "",
            "Click a tag to expand the examples that demonstrate it.", ""]
    out += [".. raw:: html", "",
            "   <style>",
            "   details.example-tag { margin: 0.2em 0; }",
            "   details.example-tag > summary { cursor: pointer; font-weight: bold; }",
            "   details.example-tag ul { margin: 0.3em 0 0.6em 1.2em; }",
            "   </style>", ""]
    for tag in sorted(tag_map, key=str.lower):
        entries = tag_map[tag]
        out.append(".. raw:: html")
        out.append("")
        out.append(f'   <details class="example-tag"><summary>{tag} '
                   f'({len(entries)})</summary><ul>')
        for u in entries:
            out.append(f'   <li><a href="{u["name"]}.html">{u["display"]}</a></li>')
        out.append("   </ul></details>")
        out.append("")

    # Hidden toctree so Sphinx builds every example page and the sidebar works.
    out += [".. toctree::", "   :hidden:", ""]
    for u in units:
        out.append(f"   {u['name']}")
    out.append("")
    (OUT_DIR / "index.rst").write_text("\n".join(out) + "\n")


def main():
    if OUT_DIR.exists():
        shutil.rmtree(OUT_DIR)
    OUT_DIR.mkdir()
    units = collect()
    for unit in units:
        write_example_page(unit)
    write_index(units)
    print(f"docs/examples/: {len(units)} example pages "
          f"({sum(1 for u in units if u['folder'] == 'Tutorial')} tutorial)")


if __name__ == "__main__":
    main()
