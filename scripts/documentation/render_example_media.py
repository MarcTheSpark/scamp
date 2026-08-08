#!/usr/bin/env python3
"""
Render each example script to media the docs can embed: an .mp3 of its SoundFont
playback, and an .svg of any score it shows.

Each example runs in a subprocess with ``playback_settings.recording_file_path``
pointed at a temporary .wav (transcoded to .mp3 with ffmpeg), while ``Score.show``
is redirected to export MusicXML and render it to SVG with verovio. Playback is
real time, so this is a slow batch job.

Non-terminating scripts that play on their own (``wait_forever`` loops, servers)
are recorded and cut off at the timeout; cut recordings are faded out. Scripts
that wait on live input (keyboard, mouse, MIDI, OSC, stdin) or run a GUI event
loop are skipped. A long piece only shows its score at the end, so if the real-time audio
pass is cut off before then (or skip_audio means there's no audio pass), the score is
captured in a second, fast-forwarded pass -- fast-forward transcribes silently, so a long
piece renders its score in seconds. Per-example timeout/fade/scale overrides, and
skip_audio/skip_score flags for examples whose audio or score is made by hand, live in
render_overrides.toml.
Output goes to docs/_static/media/, mirroring the example paths, and is picked up
by the docs build (html_static_path). Re-running only renders what's missing
unless --force.

    python3 scripts/documentation/render_example_media.py            # render all
    python3 scripts/documentation/render_example_media.py hello      # only paths containing "hello"
    python3 scripts/documentation/render_example_media.py --force --timeout 300

Needs ffmpeg on PATH, and scamp + verovio importable.
"""

import argparse
import os
import shutil
import signal
import subprocess
import sys
import tempfile
import tomllib
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
EXAMPLES_DIR = REPO_ROOT / "examples"
MEDIA_DIR = REPO_ROOT / "docs" / "_static" / "media"
OVERRIDES_PATH = Path(__file__).with_name("render_overrides.toml")

# Example folders to render, in order. JunkDrawer is left out.
CATEGORIES = ["Tutorial", "Assorted", "ScampExtensions", "Compositions"]

# A script mentioning any of these can't be batch-recorded: it grabs the local
# keyboard/mouse (would lock up the machine for the whole timeout), waits on live
# input we can't supply (MIDI/OSC/stdin -- it would just record silence), or runs a
# GUI event loop that makes no SoundFont sound. Scripts that play on their own but
# never return (wait_forever loops, servers) are fine -- recorded and cut off.
UNRECORDABLE_MARKERS = (
    "register_keyboard_listener", "register_mouse_listener", "KeyPlane",
    "register_midi_listener", "register_osc_listener", "input(",
    "QtWidgets", "QApplication", "pygame",
)

# Runs in the subprocess: point recording at the wav, render any shown Score to SVG
# via verovio, suppress other notation/plot popups, then run the example as __main__.
RUNNER = r"""
import sys, os, runpy, tempfile, warnings
warnings.filterwarnings("ignore")
example, wav, score_base, scale = sys.argv[1], sys.argv[2], sys.argv[3], int(sys.argv[4])
fast = sys.argv[5] == "1"
sys.path.insert(0, os.path.dirname(example))
import scamp
if wav:
    scamp.playback_settings.recording_file_path = wav
if fast:
    # Score-only pass: put every Session this example builds into fast-forward, so a long
    # piece runs as fast as the CPU allows and still reaches its final Score.show(). scamp
    # transcribes silently while fast-forwarding, so the score is unchanged but no audio plays.
    _orig_session_init = scamp.Session.__init__
    def _fast_forward_init(self, *a, **k):
        _orig_session_init(self, *a, **k)
        self.fast_forward(True)
    scamp.Session.__init__ = _fast_forward_init

_score_count = [0]
def _capture_score(self, *a, **k):
    try:
        import verovio
        xml = tempfile.mktemp(suffix=".musicxml")
        self.export_music_xml(xml)
        tk = verovio.toolkit()
        tk.setOptions({"adjustPageHeight": True, "footer": "none", "header": "none",
                       "scale": scale, "pageMarginTop": 10, "pageMarginBottom": 10,
                       "pageMarginLeft": 10, "pageMarginRight": 10})
        # An explicitly-given title (not one of the random default-pool ones) is written
        # to a .title sidecar, so the docs can label it when a script shows several scores.
        title = getattr(self, "title", None)
        defaults = scamp.engraving_settings.default_titles
        defaults = [defaults] if isinstance(defaults, str) else (defaults or [])
        given_title = title if title and title not in defaults else None
        if tk.loadFile(xml):
            _score_count[0] += 1
            # Each show() call is one score; the pages verovio split it across share a
            # filename stem (-p2, -p3 ...) so the docs group them into one arrow-key pager.
            # Separate scores from separate show() calls keep the -2, -3 ... numbering.
            score_suffix = "" if _score_count[0] == 1 else "-%d" % _score_count[0]
            for page in range(1, tk.getPageCount() + 1):
                page_suffix = "" if page == 1 else "-p%d" % page
                out = score_base + score_suffix + page_suffix + ".svg"
                open(out, "w").write(tk.renderToSVG(page))
                if given_title:
                    open(out[:-4] + ".title", "w").write(given_title)
    except Exception as e:
        sys.stderr.write("score capture failed: %r\n" % e)

_Score = getattr(scamp, "Score", None)
if _Score is not None:
    _Score.show = _capture_score if score_base else (lambda self, *a, **k: None)
    _Score.show_xml = _Score.show
_Performance = getattr(scamp, "Performance", None)
if _Performance is not None and hasattr(_Performance, "show"):
    _Performance.show = lambda self, *a, **k: None
if "abjad" in open(example).read():          # don't pop a PDF viewer / hang on lilypond
    try:
        import abjad
        abjad.show = lambda *a, **k: None
    except Exception:
        pass
runpy.run_path(example, run_name="__main__")
"""


def load_overrides():
    """Per-example {timeout, fade} from render_overrides.toml, keyed by path
    relative to examples/."""
    if OVERRIDES_PATH.exists():
        with open(OVERRIDES_PATH, "rb") as f:
            return tomllib.load(f)
    return {}


def wav_duration(path):
    out = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "default=nk=1:nw=1", str(path)],
        capture_output=True, text=True,
    )
    try:
        return float(out.stdout.strip())
    except ValueError:
        return 0.0


def examples_to_render(name_filter):
    for category in CATEGORIES:
        for path in sorted((EXAMPLES_DIR / category).rglob("*.py")):
            if "__pycache__" in path.parts:
                continue
            if name_filter and name_filter not in path.relative_to(EXAMPLES_DIR).as_posix():
                continue
            yield path


def render(path, timeout, fade, scale, skip_audio=False, skip_score=False):
    """Render one example to mp3/svg. Returns a status string for the summary.
    skip_audio/skip_score leave the audio/score to be made by hand instead.

    Up to two subprocess passes: a real-time one for the audio (which also grabs the score if
    the piece finishes in time), then -- only when a score was wanted but not captured (a long
    piece cut at the timeout, or skip_audio) -- a fast-forwarded pass just for the score."""
    src = path.read_text()
    if any(marker in src for marker in UNRECORDABLE_MARKERS):
        return "skipped (needs input/GUI)"
    # Non-terminating and makes neither SoundFont sound nor a score -> nothing to capture.
    if ("wait_forever" in src or "run_as_server" in src) \
            and "new_part(" not in src and "to_score(" not in src:
        return "skipped (no SoundFont/score)"

    rel = path.relative_to(EXAMPLES_DIR)
    mp3 = MEDIA_DIR / rel.with_suffix(".mp3")
    wav = mp3.with_suffix(".wav")
    score_base = "" if skip_score else str(mp3.with_suffix(""))  # empty -> capture no score
    want_score = not skip_score and "to_score(" in src
    mp3.parent.mkdir(parents=True, exist_ok=True)
    if not skip_score:
        for pat in (mp3.stem + "*.svg", mp3.stem + "*.title"):  # drop scores from a previous run
            for stale in mp3.parent.glob(pat):
                stale.unlink()

    env = {**os.environ, "MPLBACKEND": "Agg"}  # keep matplotlib from opening windows
    # Run in a throwaway copy of the example's folder, so examples that export files
    # (midi/xml/json) write into the copy rather than dirtying examples/. Siblings they
    # read (e.g. a saved performance) are copied along, so those examples still work.
    tmp_cwd = tempfile.mkdtemp(prefix="scamp_example_")
    shutil.copytree(path.parent, tmp_cwd, dirs_exist_ok=True)

    def run_pass(wav_arg, fast):
        """One subprocess pass. fast -> run the example fast-forwarded (score only, no audio).
        Returns (cut, returncode, stderr)."""
        proc = subprocess.Popen(
            [sys.executable, "-c", RUNNER, str(path), wav_arg, score_base,
             str(scale), "1" if fast else "0"],
            cwd=tmp_cwd, env=env, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE,
        )
        try:
            _, err = proc.communicate(timeout=timeout)
            return False, proc.returncode, err
        except subprocess.TimeoutExpired:
            proc.send_signal(signal.SIGINT)  # let the atexit hook flush/close the wav, then escalate
            try:
                _, err = proc.communicate(timeout=15)
            except subprocess.TimeoutExpired:
                proc.kill()
                _, err = proc.communicate()
            return True, proc.returncode, err

    def captured():
        return [] if skip_score else sorted(mp3.parent.glob(mp3.stem + "*.svg"))

    try:
        cut = audio = fast_score = False
        # Real-time pass for the audio (also grabs the score if the piece finishes in time).
        if not skip_audio:
            cut, rc, err = run_pass(str(wav), fast=False)
            if not cut and rc != 0:
                wav.unlink(missing_ok=True)
                tail = err.decode(errors="replace").strip().splitlines()
                return "error: " + (tail[-1] if tail else f"exit {rc}")
            if wav.exists():
                cmd = ["ffmpeg", "-y", "-loglevel", "error", "-i", str(wav)]
                if cut and fade > 0:  # ease the abrupt cut with a fade-out over the last `fade` seconds
                    start = max(0.0, wav_duration(wav) - fade)
                    cmd += ["-af", f"afade=t=out:st={start:.3f}:d={fade}"]
                cmd += ["-codec:a", "libmp3lame", "-q:a", "2", str(mp3)]
                audio = subprocess.run(cmd).returncode == 0
                wav.unlink(missing_ok=True)

        # Fast-forwarded score pass, when a score was wanted but not captured above.
        if want_score and not captured():
            fast_score = True
            _, rc, err = run_pass("", fast=True)
            if not captured():
                tail = err.decode(errors="replace").strip().splitlines()
                return "score error: " + (tail[-1] if tail else f"exit {rc}")

        scores = captured()
        if skip_audio:
            status = "audio skipped"
        elif audio:
            status = f"rendered (cut {timeout}s)" if cut else "rendered"
        else:
            status = "no audio"
        if scores:
            status += f" +{len(scores)} score" + ("s" if len(scores) > 1 else "")
            if fast_score:
                status += " (ff)"
        if skip_score:
            status += " (score manual)"
        return status
    finally:
        shutil.rmtree(tmp_cwd, ignore_errors=True)


def main():
    parser = argparse.ArgumentParser(description="Render example scripts to mp3 + score svg.")
    parser.add_argument("filter", nargs="?", default="",
                        help="only render examples whose path contains this substring")
    parser.add_argument("--timeout", type=int, default=60,
                        help="default per-example cutoff in seconds (default: 60)")
    parser.add_argument("--fade", type=float, default=5.0,
                        help="default fade-out (seconds) applied to cut recordings (default: 5)")
    parser.add_argument("--scale", type=int, default=60,
                        help="default verovio score scale, i.e. notation size (default: 60)")
    parser.add_argument("--force", action="store_true",
                        help="re-render even if the outputs already exist")
    args = parser.parse_args()

    if shutil.which("ffmpeg") is None:
        sys.exit("ffmpeg not found on PATH.")

    overrides = load_overrides()
    counts = {}
    for path in examples_to_render(args.filter):
        rel = path.relative_to(EXAMPLES_DIR)
        mp3 = MEDIA_DIR / rel.with_suffix(".mp3")
        override = overrides.get(rel.as_posix(), {})
        skip_audio = override.get("skip_audio", False)
        skip_score = override.get("skip_score", False)
        # The primary artifact existing means we've already rendered it (the score, when the
        # audio is hand-made; else the mp3). Scores are (re)captured on that run or with --force.
        primary = mp3.with_suffix(".svg") if skip_audio else mp3
        if skip_audio and skip_score:       # nothing to render here -- both made by hand
            status = "skipped (manual)"
        elif primary.exists() and not args.force:
            status = "exists"
        else:
            status = render(path, override.get("timeout", args.timeout),
                            override.get("fade", args.fade),
                            override.get("scale", args.scale),
                            skip_audio, skip_score)
        key = status.split(":")[0].split(" (")[0].split(" +")[0]
        counts[key] = counts.get(key, 0) + 1
        print(f"  {status:<30} {rel.as_posix()}")

    print("\n" + ", ".join(f"{n} {k}" for k, n in sorted(counts.items())))


if __name__ == "__main__":
    main()
