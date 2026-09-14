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

The topic structure comes from the examples directory tree (see regenerate_index.py): each
topic is a top-level folder, its sections are the sub-folders, and each folder's
docs_order.txt sets the order and any cross-listings. This writes docs/examples/index.rst
(an ordered Tutorial list, then a By-topic list of the topic pages), one topic page per
topic (inline section headings, each listing its examples as links), and one page per
example holding the description, source, media and download. The topic pages only link to
examples, so an example can appear on several of them without duplication, and the sidebar
stays flat (topic pages don't expand into examples). Each example page carries a "Topics:"
crossref to every section it appears in. Tutorial example pages sit in the Tutorial toctree
so they show in the sidebar; the rest are :orphan:, reached from the topic pages. Each page
links to the source on GitHub, offers a download (the .py, or a .zip when companion files
are needed), and embeds any captured media: an audio player, score images, and hand-authored
videos (example_media.toml).

A single-file example takes its description from the file's own docstring and gets one
unlabeled code box. A folder example takes its title/description from an about.txt if
present (else the folder-named script) and shows one code box per file captioned
"name: description". Any SuperCollider (.scd) scripts get code boxes after the Python ones,
labeled by filename. example_media.toml can pin a per-example ``order`` of media by filename
(leaving out anything not listed). The JunkDrawer is left out.

Run from anywhere: python3 build_examples_docs.py
"""

import re
import sys
import shutil
import tomllib
import zipfile
import pathlib
import urllib.parse

DOCS_DIR = pathlib.Path(__file__).parent
EXAMPLES_DIR = DOCS_DIR.parent / "examples"
OUT_DIR = DOCS_DIR / "examples"
MEDIA_DIR = DOCS_DIR / "_static" / "media"          # audio/scores, captured by render_example_media.py
MEDIA_MANIFEST_PATH = DOCS_DIR / "example_media.toml"  # hand-authored video links, media ordering

GITHUB_BASE = "https://github.com/MarcTheSpark/scamp"
GITHUB_BRANCH = "master"

sys.path.insert(0, str(EXAMPLES_DIR))
from regenerate_index import (  # noqa: E402
    slugify, title_of, parse_docstring, parse_about, ordered_items, iter_units,
    topic_dirs, example_locations, TUTORIAL_DIR)


def _load_manifest():
    if MEDIA_MANIFEST_PATH.exists():
        with open(MEDIA_MANIFEST_PATH, "rb") as f:
            return tomllib.load(f)
    return {}


MEDIA_MANIFEST = _load_manifest()

LICENSE_DELIM = re.compile(r"^#\s*\++\s*#\s*$")


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
    summary = parse_docstring(path) if lang == "python" else None
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
        rest = p.name[len(prefix):]
        if rest[:1] not in (".", "-"):
            continue  # a longer-named sibling (voices vs voices_with_octave_lines), not ours
        if rest.startswith(".plot"):
            continue  # an Envelope plot -> handled by plot_images, laid out inline
        score, page = index(p)
        scores.setdefault(score, []).append((page, p))
    return [[p for _, p in sorted(pages)] for _, pages in sorted(scores.items())]


def plot_images(script):
    """This script's captured Envelope plots (matplotlib SVGs), in call order. Files are
    <base>.plot.svg, <base>.plot-2.svg, ...; see render_example_media.py."""
    base = (MEDIA_DIR / script["rel"]).with_suffix("")
    prefix = base.name + ".plot"

    def num(p):
        m = re.match(r"^-(\d+)$", p.name[len(prefix):-len(".svg")])
        return int(m.group(1)) if m else 1

    return sorted(base.parent.glob(prefix + "*.svg"), key=num)


def _media_url(p):
    # relative to the built example page (examples/<slug>.html); media lives under _static/.
    # Topic/section dirs carry spaces and '&', so percent-encode the path for the src attr.
    rel = p.relative_to(MEDIA_DIR).as_posix()
    return "../_static/media/" + urllib.parse.quote(rel)


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


def plot_html(p):
    """One Envelope plot as an inline figure, so several flow side by side and wrap.
    No caption -- the plot's title is already drawn into the SVG."""
    return (f'<figure style="display:inline-block;vertical-align:top;margin:0.2em 0.4em">'
            f'<img src="{_media_url(p)}" alt="envelope plot" '
            f'style="max-width:100%;height:auto;display:block"></figure>')


def plot_gallery_html(plots):
    """A script's Envelope plots flowing inline, wrapping to the next row as needed."""
    return ('<div style="margin:0.4em 0">'
            + "".join(plot_html(p) for p in plots) + '</div>')


def video_html(vid):
    return (f'<iframe src="https://www.youtube-nocookie.com/embed/{vid}" '
            'style="width:100%;max-width:640px;aspect-ratio:16/9;border:0;'
            'display:block;margin:0.6em 0" allowfullscreen></iframe>')


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
        if ".plot" in token[:-len(".svg")]:
            return raw_block(plot_html(p))
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
        plots = plot_images(s)
        if plots:
            out += raw_block(plot_gallery_html(plots))
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
    """Every example unit, keyed by its path under examples/ (a script's .py path, or a
    folder example's directory). Walks the whole tree; JunkDrawer is excluded by iter_units."""
    units = {}
    for path in iter_units(EXAMPLES_DIR):
        u = folder_unit(path) if path.is_dir() else file_unit(path)
        units[u["key"]] = u
    return units


def _folder_pys(d):
    return sorted(p for p in d.rglob("*.py") if "__pycache__" not in p.parts)


def file_unit(path):
    rel = path.relative_to(EXAMPLES_DIR)
    summary = parse_docstring(path)
    return {
        "kind": "file", "name": slugify(rel.as_posix()[:-len(".py")]),
        "display": rel.as_posix(), "reldir": rel.parent.as_posix(),
        "media_dir": MEDIA_DIR / rel.parent, "key": rel.as_posix(),
        "is_tutorial": rel.parts[0] == TUTORIAL_DIR,
        "title": title_of(path), "summary": summary or "",
        "needs_ext": "scamp_extensions" in path.read_text(),
        "scripts": [script_entry(path)], "extra": scd_entries(companion_files(path)),
        "download": ("file", path),
    }


def folder_unit(d):
    """One page for a folder example (several scripts + companions): a code box per script,
    one folder zip. Title/summary come from about.txt if present, else the folder-named (or
    lone) script."""
    paths = _folder_pys(d)
    reldir = d.relative_to(EXAMPLES_DIR).as_posix()
    main = next((p for p in paths if p.stem == d.name), None)
    ordered = ([main] + [p for p in paths if p is not main]) if main else paths
    about = parse_about(d)
    if about:
        title, summary = about[0] or d.name.replace("_", " ").title(), about[1]
    elif len(paths) == 1:                       # a lone script keeps its own top description
        title, summary = title_of(ordered[0]), parse_docstring(ordered[0])
    elif main:                                  # multi w/o about.txt: descriptions ride the boxes
        title, summary = title_of(main), ""
    else:
        title, summary = d.name.replace("_", " ").title(), ""
    return {
        "kind": "folder", "name": slugify(reldir),
        "display": reldir + "/", "reldir": reldir, "media_dir": MEDIA_DIR / reldir,
        "key": reldir, "is_tutorial": reldir.split("/", 1)[0] == TUTORIAL_DIR,
        "title": title, "summary": summary,
        "needs_ext": any("scamp_extensions" in p.read_text() for p in paths),
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


# ---- topic structure ------------------------------------------------------
#
def first_sentence(text):
    """The description's first sentence -- the one-liner shown next to an index-page link.
    A leading parenthetical (e.g. a warning) is skipped so the preview is the real summary.
    The example's own page shows the full description."""
    text = re.sub(r"^\s*\([^)]*\)\s*", "", text)
    m = re.match(r"\s*(.+?[.!?])(\s|$)", text, re.DOTALL)
    return m.group(1).strip() if m else text.strip()


def _topic_entry(u):
    """A bullet for one example in a topic page: a link to its page plus its one-liner."""
    line = f"- :doc:`{u['title']} <{u['name']}>`"
    if u["summary"]:
        line += f" — {first_sentence(u['summary'])}"
    if u["needs_ext"]:
        line += " *(needs scamp_extensions)*"
    return line


HEAD_CHARS = {1: "=", 2: "-", 3: "~", 4: '"'}


def render_group(d, units, out, level):
    """Append a grouping dir's ordered body to ``out``: example bullets, and a heading +
    recursion for each sub-section."""
    for kind, node in ordered_items(d):
        if kind == "example":
            u = units.get(node)
            if u is None:
                print(f"  WARNING: docs_order example not found: {node}")
                continue
            out.append(_topic_entry(u))
        else:                                    # a sub-section
            out += ["", node.name, HEAD_CHARS[level] * len(node.name), ""]
            render_group(node, units, out, level + 1)
    out.append("")


def write_topic_page(topic_dir, units):
    """A topic page: inline section headings, each listing its examples as links. The
    examples' own pages hold the code and media."""
    title = topic_dir.name
    out = [title, "=" * len(title), ""]
    render_group(topic_dir, units, out, 2)
    (OUT_DIR / f"{slugify(title)}.rst").write_text("\n".join(out).rstrip("\n") + "\n")


def topics_line(unit, locations):
    """The '*Topics:*' crossref: each place this example appears, linking to its topic page."""
    crumbs = []
    for topic, section in locations.get(unit["key"], []):
        text = f"{topic} › {section}" if section else topic
        crumbs.append(f":doc:`{text} <{slugify(topic)}>`")
    return "*Topics:* " + ", ".join(crumbs) if crumbs else None


def write_example_page(unit, locations):
    """One page per example: description, source, media, download. Tutorial pages live in
    the Tutorial toctree; the rest are :orphan: (reached from the topic pages), so the
    sidebar stays flat. An example that needs scamp_extensions says so up top."""
    title = unit["title"]
    orphan = not unit["is_tutorial"]
    out = ([":orphan:", ""] if orphan else []) + [
        title, "=" * len(title), "", github_line(unit), "", write_download(unit), ""]
    if unit["needs_ext"]:
        out += ["**Requires the** ``scamp_extensions`` **package** "
                "(``pip install scamp_extensions``)**.**", ""]
    if unit["summary"]:
        out += [unit["summary"], ""]
    topics = topics_line(unit, locations)
    if topics:
        out += [topics, ""]
    out += body_lines(unit)
    (OUT_DIR / f"{unit['name']}.rst").write_text("\n".join(out) + "\n")


def tutorial_units(units):
    """The tutorial example units in teaching order (their numeric filename prefix sorts)."""
    return sorted((u for u in units.values() if u["is_tutorial"]), key=lambda u: u["name"])


def write_tutorial_page(units):
    """The Tutorial section page: an ordered, numbered list of the tutorial examples, plus a
    toctree that holds their pages -- so the sidebar shows a single 'Tutorial' node that
    expands into the examples, rather than listing every one flat."""
    out = ["Tutorial", "========", "",
           "Work through these in order for a guided tour of the framework.", ""]
    tutorial = tutorial_units(units)
    for u in tutorial:
        line = f"#. :doc:`{u['title']} <{u['name']}>`"
        if u["summary"]:
            line += f" — {first_sentence(u['summary'])}"
        out.append(line)
    out += ["", ".. toctree::", "   :hidden:", ""]
    out += [f"   {u['name']}" for u in tutorial]
    out.append("")
    (OUT_DIR / "tutorial.rst").write_text("\n".join(out) + "\n")


def write_index(units, topics):
    """The Examples landing page: a link into the Tutorial section, then a By-topic list of
    the topic pages and their sections. A single hidden toctree puts the Tutorial page and
    the topic pages in the sidebar as sibling section nodes."""
    out = [
        "Examples", "========", "",
        "A gallery of the example scripts that ship with SCAMP. The **tutorial** examples",
        "are a progressively-ordered teaching set; the **by-topic** pages collect every",
        "example (tutorial and beyond) by subject.",
        "",
        ".. rubric:: Tutorial", "",
        ":doc:`Work through the tutorial <tutorial>` in order for a guided tour of the "
        "framework.", "",
        ".. rubric:: By topic", "",
        "Each topic is one page, grouping its examples under headings.", "",
    ]
    for td in topics:
        secs = [node.name for kind, node in ordered_items(td) if kind == "group"]
        blurb = " · ".join(secs)
        line = f"- :doc:`{td.name} <{slugify(td.name)}>`"
        out.append(line + (f" — {blurb}" if blurb else ""))

    out += ["", ".. toctree::", "   :hidden:", "", "   tutorial"]
    out += [f"   {slugify(td.name)}" for td in topics]
    out.append("")
    (OUT_DIR / "index.rst").write_text("\n".join(out) + "\n")


def main():
    if OUT_DIR.exists():
        shutil.rmtree(OUT_DIR)
    OUT_DIR.mkdir()
    units = collect()
    topics = topic_dirs(EXAMPLES_DIR)
    locations = example_locations()
    for td in topics:
        write_topic_page(td, units)
    for unit in units.values():
        write_example_page(unit, locations)
    write_tutorial_page(units)
    write_index(units, topics)
    # A non-tutorial example in no topic still builds, but nothing links to it -- flag it.
    for key, u in units.items():
        if not u["is_tutorial"] and key not in locations:
            print(f"  NOTE: not in any topic (orphan page): {u['display']}")
    print(f"docs/examples/: {len(units)} example pages, {len(topics)} topics "
          f"({sum(1 for u in units.values() if u['is_tutorial'])} tutorial)")


if __name__ == "__main__":
    main()
