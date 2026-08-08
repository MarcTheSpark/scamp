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
a code box per script with a single folder-zip download. Each page links to the source on
GitHub, offers a download (the .py, or a .zip when companion files are needed), and embeds
any captured media: an audio player (_static/media/<rel>.mp3), score images (<rel>*.svg),
and hand-authored videos (example_media.toml).

A single-file example takes its description from the file's own docstring and gets one
unlabeled code box. A folder example takes its title/description from an about.txt if
present (else the folder-named script), merges tags across every file, and shows one code
box per file captioned "name: description". Any SuperCollider (.scd) scripts get code
boxes after the Python ones, labeled by filename. example_media.toml can pin a per-example
``order`` of media by filename (leaving out anything not listed). The JunkDrawer is left
out. Reuses the docstring/tag parsing from examples/regenerate_index.py.

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
MEDIA_MANIFEST_PATH = DOCS_DIR / "example_media.toml"  # hand-authored video links, media ordering

GITHUB_BASE = "https://github.com/MarcTheSpark/scamp"
GITHUB_BRANCH = "master"

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


def parse_about(folder):
    """(title, description, tags) from a folder's about.txt, or None if absent.
    Same shape as an example docstring: a 'SCAMP Example:' title line, a body, and a
    'Tags:' line, in any order."""
    about = folder / "about.txt"
    if not about.exists():
        return None
    title, tags, body = None, [], []
    for ln in (ln.strip() for ln in about.read_text().splitlines()):
        if ln.startswith("Tags:"):
            tags = [t.strip() for t in ln[len("Tags:"):].split(",") if t.strip()]
        elif ln.startswith("SCAMP Example:"):
            title = ln[len("SCAMP Example:"):].strip()
        else:
            body.append(ln)
    return title, " ".join(ln for ln in body if ln).strip(), tags


def source_body(path):
    """The example source with its docstring and GPL license block stripped."""
    text = path.read_text()
    text = re.sub(r'^\s*"""(.*?)"""', "", text, count=1, flags=re.DOTALL)
    lines = text.splitlines()
    delims = [i for i, ln in enumerate(lines) if LICENSE_DELIM.match(ln)]
    if len(delims) >= 2:
        del lines[delims[0]:delims[1] + 1]
    return "\n".join(lines).strip("\n")


def script_entry(path, lang="python"):
    """The per-script bits shown in a code box: filename, summary, source, rel path, lexer.
    Only Python scripts carry a docstring summary."""
    summary = parse_docstring(path)[0] if lang == "python" else None
    return {"name": path.name, "summary": summary or "", "body": source_body(path),
            "rel": path.relative_to(EXAMPLES_DIR), "lang": lang}


def scd_entries(paths):
    """Code-box entries for any SuperCollider (.scd) files among paths, sorted by name."""
    return [script_entry(p, "supercollider")
            for p in sorted(paths) if p.is_file() and p.suffix == ".scd"]


# ---- media rendering -------------------------------------------------------

def _yt_id(url):
    """The video id from a YouTube URL (watch?v=, youtu.be/, embed/), or url unchanged
    if it already looks like a bare id."""
    for marker in ("watch?v=", "youtu.be/", "embed/"):
        if marker in url:
            url = url.split(marker, 1)[1]
            break
    return re.split(r"[&?/]", url)[0]


def unit_videos(unit):
    """Video ids declared for this unit in example_media.toml (video= / youtube=)."""
    entry = MEDIA_MANIFEST.get(unit["key"], {})
    vids = entry.get("video", entry.get("youtube", []))
    if isinstance(vids, str):
        vids = [vids]
    return [_yt_id(v) for v in vids]


def audio_path(script):
    return (MEDIA_DIR / script["rel"]).with_suffix(".mp3")


def score_pages(script):
    """This script's captured score SVGs, grouped by score. Returns a list of scores, each
    a list of its page SVGs in order; a long score verovio split across pages has more than
    one. Files are <base>.svg (score 1 page 1), <base>-p2.svg (score 1 page 2), <base>-2.svg
    (score 2 page 1), <base>-2-p3.svg ...; see render_example_media.py."""
    base = (MEDIA_DIR / script["rel"]).with_suffix("")
    prefix = base.name

    def index(p):
        # suffix between the shared stem and .svg -> (score, page), each defaulting to 1
        m = re.match(r"^(?:-(\d+))?(?:-p(\d+))?$", p.name[len(prefix):-len(".svg")])
        score = int(m.group(1)) if m and m.group(1) else 1
        page = int(m.group(2)) if m and m.group(2) else 1
        return score, page

    scores = {}
    for p in base.parent.glob(prefix + "*.svg"):
        score, page = index(p)
        scores.setdefault(score, []).append((page, p))
    return [[p for _, p in sorted(pages)] for _, pages in sorted(scores.items())]


def _media_url(p):
    # relative to the built example page (examples/<slug>.html); media lives under _static/
    return "../_static/media/" + p.relative_to(MEDIA_DIR).as_posix()


def audio_html(p):
    return (f'<div style="margin:0.6em 0"><audio controls preload="none" '
            f'src="{_media_url(p)}" style="width:100%;max-width:520px"></audio></div>')


def score_label(p):
    """An explicit score title, written to a .title sidecar at render time, or ''."""
    sidecar = p.with_suffix(".title")
    return sidecar.read_text().strip() if sidecar.exists() else ""


def _score_label_html(label):
    return (f'<div style="font-weight:bold;margin:0.6em 0 0.2em">{label}</div>'
            if label else "")


def score_html(p, label=""):
    return (_score_label_html(label) +
            f'<div style="border:1px solid #ccc;padding:8px;margin:0.2em 0 0.6em;'
            f'display:inline-block;max-width:100%">'
            f'<img src="{_media_url(p)}" alt="score" '
            f'style="max-width:100%;height:auto;display:block"></div>')


def score_pager_html(pages, label=""):
    """A multi-page score as a pager: one page shown at a time, switched with the prev/next
    buttons or the left/right arrow keys (see _static/js/score_pager.js)."""
    imgs = "".join(
        f'<img src="{_media_url(p)}" alt="score page {i + 1}" class="score-page" '
        f'style="max-width:100%;height:auto;'
        f'{"display:block" if i == 0 else "display:none"}">'
        for i, p in enumerate(pages))
    return (_score_label_html(label) +
            f'<div class="score-pager" tabindex="0">'
            f'<div class="score-pager-frame">{imgs}</div>'
            f'<div class="score-pager-controls">'
            f'<button type="button" class="score-pager-prev" aria-label="Previous page">'
            f'&#9664;</button>'
            f'<span class="score-pager-status">1 / {len(pages)}</span>'
            f'<button type="button" class="score-pager-next" aria-label="Next page">'
            f'&#9654;</button>'
            f'</div></div>')


def score_block_html(pages, label=""):
    """One captured score: a plain image, or an arrow-key pager when it spans several pages."""
    return score_html(pages[0], label) if len(pages) == 1 else score_pager_html(pages, label)


def video_html(vid):
    return ('<div style="position:relative;padding-bottom:56.25%;height:0;'
            'max-width:640px;margin:0.6em 0">'
            f'<iframe src="https://www.youtube-nocookie.com/embed/{vid}" '
            'style="position:absolute;top:0;left:0;width:100%;height:100%;border:0" '
            'allowfullscreen></iframe></div>')


def raw_block(html):
    return [".. raw:: html", "", "   " + html, ""]


def code_block(script, caption):
    out = [f".. code-block:: {script['lang']}"]
    if caption:
        out.append(f"   :caption: {caption}")
    out.append("")
    for ln in script["body"].splitlines():
        out.append("   " + ln if ln else "")
    out.append("")
    return out


def caption_for(script, multi):
    """Multi-file pages caption each box 'name: description'; single-file pages don't."""
    if not multi:
        return None
    return f"{script['name']}: {script['summary']}" if script["summary"] else script["name"]


def code_caption(script, multi):
    """SuperCollider boxes are labeled by filename; Python boxes follow caption_for."""
    return caption_for(script, multi) if script["lang"] == "python" else script["name"]


def order_item(token, unit, by_name, vids, multi):
    """One entry from a manifest ``order`` list -> its rst lines. A ``*.py`` / ``*.scd``
    token is that script's code box; ``*.mp3`` / ``*.svg`` a media file in the unit's
    media dir; ``video`` all declared videos; anything else a bare video id/url."""
    if token in ("video", "videos"):
        return [ln for v in vids for ln in raw_block(video_html(v))]
    s = by_name.get(token)
    if s is not None:
        return code_block(s, code_caption(s, multi))
    p = unit["media_dir"] / token
    if token.endswith(".mp3") and p.exists():
        return raw_block(audio_html(p))
    if token.endswith(".svg") and p.exists():
        return raw_block(score_html(p))
    return raw_block(video_html(_yt_id(token)))


def body_lines(unit):
    """The media + code body below the header, honoring a manifest ``order`` if given,
    else the default: videos, then each Python script's scores, audio, and code box,
    then any SuperCollider scripts as code boxes at the end."""
    scripts, extra = unit["scripts"], unit.get("extra", [])
    multi = len(scripts) > 1                         # captions kick in with >1 Python script
    vids = unit_videos(unit)
    order = MEDIA_MANIFEST.get(unit["key"], {}).get("order")
    if order:
        by_name = {s["name"]: s for s in scripts + extra}
        return [ln for token in order
                for ln in order_item(token, unit, by_name, vids, multi)]

    out = [ln for v in vids for ln in raw_block(video_html(v))]
    for s in scripts:
        for pages in score_pages(s):            # explicit score titles are labeled, singular or not
            out += raw_block(score_block_html(pages, score_label(pages[0])))
        if audio_path(s).exists():
            out += raw_block(audio_html(audio_path(s)))
        out += code_block(s, caption_for(s, multi))
    for s in extra:
        out += code_block(s, s["name"])
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
    rel = path.relative_to(EXAMPLES_DIR)
    summary, tags = parse_docstring(path)
    return {
        "folder": folder, "kind": "file", "name": slugify(rel.as_posix()[:-len(".py")]),
        "display": rel.as_posix(), "reldir": rel.parent.as_posix(),
        "media_dir": MEDIA_DIR / rel.parent, "key": rel.as_posix(),
        "title": title_of(path), "summary": summary or "", "tags": tags,
        "scripts": [script_entry(path)], "extra": scd_entries(companion_files(path)),
        "download": ("file", path),
    }


def folder_unit(folder, d, paths):
    """A subfolder shown as one page: a code box per script, one folder zip. Title and
    top description come from an about.txt if present, else the folder-named script; tags
    are merged across every script (and about.txt)."""
    reldir = d.relative_to(EXAMPLES_DIR).as_posix()
    main = next((p for p in paths if p.stem == d.name), None)
    ordered = ([main] + [p for p in paths if p is not main]) if main else paths
    about = parse_about(d)

    tags = []
    for source in ([p for p in ordered] + ([None] if about else [])):
        source_tags = about[2] if source is None else parse_docstring(source)[1]
        for t in source_tags:
            if t not in tags:
                tags.append(t)

    if about:
        title, summary = about[0] or d.name.replace("_", " ").title(), about[1]
    elif len(paths) == 1:                       # a lone script keeps its own top description
        title, summary = title_of(ordered[0]), (parse_docstring(ordered[0])[0] or "")
    elif main:                                  # multi w/o about.txt: descriptions ride the boxes
        title, summary = title_of(main), ""
    else:
        title, summary = d.name.replace("_", " ").title(), ""
    return {
        "folder": folder, "kind": "folder", "name": slugify(reldir),
        "display": reldir + "/", "reldir": reldir, "media_dir": MEDIA_DIR / reldir,
        "key": reldir, "title": title, "summary": summary, "tags": tags,
        "scripts": [script_entry(p) for p in ordered],
        "extra": scd_entries(d.rglob("*.scd")), "download": ("folder", d),
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


def github_line(unit):
    """The '*Example script/directory:*' line, linking to the source on GitHub."""
    if unit["kind"] == "folder":
        url = f"{GITHUB_BASE}/tree/{GITHUB_BRANCH}/examples/{unit['reldir']}"
        return f"*Example directory:* `examples/{unit['reldir']} <{url}>`__"
    url = f"{GITHUB_BASE}/blob/{GITHUB_BRANCH}/examples/{unit['display']}"
    return f"*Example script:* `examples/{unit['display']} <{url}>`__"


def write_example_page(unit):
    title = unit["title"]
    out = [title, "=" * len(title), "", github_line(unit), "", write_download(unit), ""]
    if unit["summary"]:
        out += [unit["summary"], ""]
    if unit["tags"]:
        out += ["*Tags:* " + ", ".join(unit["tags"]), ""]
    out += body_lines(unit)
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
