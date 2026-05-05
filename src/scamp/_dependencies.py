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

from .settings import playback_settings, engraving_settings
import importlib.metadata
import logging
import os
import platform
import re
from pathlib import Path

# ---------------------------------------------------------------------------
# fluidsynth
# ---------------------------------------------------------------------------
# Two possible sources for the pyfluidsynth Python wrapper: a system-wide
# pip-installed pyfluidsynth, or the tweaked copy bundled inside
# scamp/_thirdparty/. The bundled wrapper additionally knows how to dlopen
# either the system libfluidsynth or scamp's bundled libfluidsynth — that
# library-level choice is governed separately by
# playback_settings.try_system_fluidsynth_first.
#
# Wrapper choice is governed by playback_settings.use_bundled_pyfluidsynth
# (default True everywhere). Either source can fail (not installed; partially
# installed; underlying lib missing); we try the preferred one first and fall
# back to the other.


def _import_fluidsynth(strategy: str):
    if strategy == "system":
        import fluidsynth
        return fluidsynth
    if strategy == "bundled":
        from ._thirdparty import fluidsynth
        return fluidsynth
    raise ValueError(strategy)


_first = "bundled" if playback_settings.use_bundled_pyfluidsynth else "system"
_second = "system" if _first == "bundled" else "bundled"
fluidsynth = None
_FLUIDSYNTH_SOURCE: str | None = None  # which strategy actually loaded ('system' or 'bundled')
for _strategy in (_first, _second):
    try:
        _candidate = _import_fluidsynth(_strategy)
    except ImportError as e:
        logging.debug(f"Loading {_strategy} pyfluidsynth failed: {e}")
        continue
    # pyfluidsynth occasionally imports as a near-empty module (partial
    # install, namespace conflict). Treat that as a failed load and try the
    # next strategy.
    if not hasattr(_candidate, 'Synth'):
        logging.debug(f"{_strategy} pyfluidsynth loaded but is missing 'Synth' attribute")
        continue
    fluidsynth = _candidate
    _FLUIDSYNTH_SOURCE = _strategy
    logging.debug(f"Loaded {_strategy} pyfluidsynth.")
    break

if fluidsynth is None:
    logging.warning("Fluidsynth could not be loaded; synth output will not be available.")


def auto_detect_audio_driver_if_needed() -> None:
    """
    If the saved default audio driver is "auto", probe each backend until one
    starts successfully, then save it as the new default. Idempotent: once a
    real driver has been written to settings, this function is a no-op.

    Called lazily from SoundfontHost.__init__ rather than at import time so
    that simply `import scamp` doesn't block on audio probing or write to the
    user's persistent settings file as a side effect.
    """
    if fluidsynth is None or playback_settings.default_audio_driver != "auto":
        return
    logging.info("Testing for working audio driver...")
    drivers = ['pipewire', 'pulseaudio', 'alsa', 'coreaudio', 'dsound',
               'Direct Sound', 'oss', 'jack', 'portaudio', 'sndmgr']
    for driver in drivers:
        test_synth = fluidsynth.Synth()
        test_synth.start(driver=driver)
        if test_synth.audio_driver is not None:
            playback_settings.default_audio_driver = driver
            playback_settings.make_persistent()
            test_synth.delete()
            logging.info(f"Found audio driver '{driver}'. Saved as default; "
                         f"override via playback_settings if needed.")
            return
        test_synth.delete()
    logging.warning("No working audio driver was found; synth output will not be available.")


# ---------------------------------------------------------------------------
# Optional Python deps. Each one can be missing without breaking scamp; users
# get a clear ImportError at the call site if they actually try to use the
# corresponding feature. These are logged at debug level (not warning) so
# routine `import scamp` doesn't pester users about features they don't use.
# ---------------------------------------------------------------------------

try:
    from ._thirdparty.sf2or3utils.sf2parse import Sf2File
except ImportError:
    Sf2File = None
    logging.debug("sf2utils not available; soundfont preset introspection disabled.")

try:
    import pythonosc
    import pythonosc.udp_client
    import pythonosc.dispatcher
    import pythonosc.osc_server
except ImportError:
    pythonosc = None
    logging.debug("pythonosc not available; OSCScampInstrument disabled.")

try:
    import rtmidi
except ImportError:
    rtmidi = None
    logging.debug("python-rtmidi not available; streaming MIDI I/O disabled.")

try:
    import pynput
except ImportError:
    pynput = None
    logging.debug("pynput not available; mouse and keyboard input disabled.")


# ---------------------------------------------------------------------------
# LilyPond binary discovery (Mac and Windows only — Linux uses distro packaging)
# ---------------------------------------------------------------------------

def find_lilypond():
    """
    Return the directory containing the lilypond binary, or None if not found.
    Searches the platform-specific paths defined in
    engraving_settings.lilypond_search_paths.
    """
    if platform.system() not in engraving_settings.lilypond_search_paths:
        return None
    logging.warning("Searching for LilyPond binary (this may take a while and is normal on first run)")
    for lilypond_search_path in engraving_settings.lilypond_search_paths[platform.system()]:
        lsp = Path(lilypond_search_path).expanduser()
        if not lsp.exists():
            continue
        binary_name = "lilypond.exe" if platform.system() == "Windows" else "lilypond"
        for potential_lp_binary in lsp.rglob(binary_name):
            if potential_lp_binary.is_file():
                logging.warning(f"LilyPond binary found at {potential_lp_binary.parent.resolve()}")
                return str(potential_lp_binary.parent.resolve())
    return None


def _should_search_for_lilypond() -> bool:
    """Decide whether to (re)scan for a lilypond binary on this platform."""
    if platform.system() not in ("Darwin", "Windows"):
        # Linux users get lilypond from their distro; PATH handles it.
        return False
    if engraving_settings.lilypond_dir is None:
        # Mac/Windows with no remembered location: search.
        return True
    # Have a remembered location, but verify the binary is still there.
    binary_name = "lilypond.exe" if platform.system() == "Windows" else "lilypond"
    return not (Path(engraving_settings.lilypond_dir) / binary_name).exists()


# ---------------------------------------------------------------------------
# abjad — kept lazy because importing abjad is slow
# ---------------------------------------------------------------------------

def _abjad_version_to_tuple(version):
    return tuple(int(x) for x in version.split("."))


# Determine the abjad version range scamp expects by parsing scamp's own
# package metadata. This keeps the version constraint declared in one place
# (pyproject.toml). Falls back to a hardcoded pin if metadata is unavailable
# (e.g. running from a source checkout that wasn't installed).
_ABJAD_PIN_FALLBACK = "3.31"


def _parse_abjad_pins() -> tuple[str, str]:
    try:
        for requirement in importlib.metadata.requires('scamp') or []:
            req = requirement.split(";")[0]  # strip env marker like "; extra=='all'"
            if "abjad" not in req:
                continue
            versions = re.findall(r'(\d+\.\d+)', req)
            if versions:
                return (min(versions, key=_abjad_version_to_tuple),
                        max(versions, key=_abjad_version_to_tuple))
    except importlib.metadata.PackageNotFoundError:
        pass
    return (_ABJAD_PIN_FALLBACK, _ABJAD_PIN_FALLBACK)


ABJAD_MIN_VERSION, ABJAD_VERSION = _parse_abjad_pins()


_abjad_library = None


def get_abjad():
    """
    Return the abjad module, importing it lazily on first call. abjad is slow
    to import (a few seconds), so we don't want to pay that cost unless the
    caller actually needs LilyPond output.
    """
    global _abjad_library

    if _abjad_library:
        return _abjad_library

    try:
        import abjad as abjad_library
    except ImportError:
        raise ImportError("abjad was not found; LilyPond output is not available.")

    if not hasattr(abjad_library, '__version__'):
        logging.warning(
            f"abjad library is present, but its version could not be identified. "
            f"Note that scamp requires abjad version {ABJAD_VERSION}."
        )
    elif _abjad_version_to_tuple(abjad_library.__version__) < _abjad_version_to_tuple(ABJAD_MIN_VERSION):
        raise ImportError(
            f"abjad version {abjad_library.__version__} found, but SCAMP is built for "
            f"version {ABJAD_VERSION}. Run `pip3 install abjad=={ABJAD_VERSION}` to upgrade."
        )
    elif _abjad_version_to_tuple(abjad_library.__version__) > _abjad_version_to_tuple(ABJAD_VERSION):
        logging.warning(
            f"abjad version {abjad_library.__version__} found, but SCAMP is built for "
            f"earlier version {ABJAD_VERSION}. The newer version may not be backwards "
            f"compatible. If errors occur, run `pip3 install abjad=={ABJAD_VERSION}` to downgrade."
        )

    if _should_search_for_lilypond():
        engraving_settings.lilypond_dir = find_lilypond()
        engraving_settings.make_persistent()

    if engraving_settings.lilypond_dir is not None:
        os.environ["PATH"] += os.pathsep + engraving_settings.lilypond_dir

    _abjad_library = abjad_library
    return abjad_library


# ---------------------------------------------------------------------------
# Optional-dependency status reporting
# ---------------------------------------------------------------------------
# Useful for debugging "why doesn't feature X work in my install?" without
# having to walk the user through inspecting each import.

# (state, detail) — state is one of 'ok', 'warn', 'missing'.
_DepStatus = tuple[str, str]


def _fluidsynth_status() -> _DepStatus:
    if fluidsynth is None:
        return ("missing", "not loaded — synth playback unavailable")
    wrapper = _FLUIDSYNTH_SOURCE  # 'system' or 'bundled' pyfluidsynth wrapper

    # The bundled wrapper sets _LIB_SOURCE explicitly to "system" or "bundled"
    # to tell us which libfluidsynth binary it dlopened. The upstream system
    # wrapper doesn't, but both wrappers store the loaded library handle at
    # module-level `_fl`, and CDLL._name records the path/name it was opened
    # with — so we can usually report the binary path even for the system
    # wrapper, just without classifying it as system vs bundled.
    lib_source = getattr(fluidsynth, '_LIB_SOURCE', None)
    lib_path = getattr(fluidsynth, '_LIB_PATH', None)
    if lib_path is None:
        _fl = getattr(fluidsynth, '_fl', None)
        if _fl is not None:
            lib_path = getattr(_fl, '_name', None)

    parts = [f"{wrapper} wrapper"]
    if lib_source and lib_path:
        parts.append(f"{lib_source} libfluidsynth ({lib_path})")
    elif lib_source:
        parts.append(f"{lib_source} libfluidsynth")
    elif lib_path:
        parts.append(f"binary: {lib_path}")
    else:
        parts.append("libfluidsynth location not tracked")
    return ("ok", ", ".join(parts))


def _abjad_status() -> _DepStatus:
    """Check abjad availability and version match without importing it."""
    try:
        installed = importlib.metadata.version('abjad')
    except importlib.metadata.PackageNotFoundError:
        return ("missing", f"not installed (need {ABJAD_VERSION})")
    iv = _abjad_version_to_tuple(installed)
    if iv < _abjad_version_to_tuple(ABJAD_MIN_VERSION):
        return ("missing", f"installed {installed}, need >={ABJAD_MIN_VERSION}")
    if iv > _abjad_version_to_tuple(ABJAD_VERSION):
        return ("warn", f"installed {installed} (newer than tested {ABJAD_VERSION}; may be incompatible)")
    return ("ok", f"installed {installed}")


def _present_status(module, what_it_does: str) -> _DepStatus:
    if module is None:
        return ("missing", what_it_does)
    return ("ok", what_it_does)


def dependency_status() -> list[tuple[str, str, str]]:
    """
    Return a list of (name, state, detail) tuples describing the status of
    each optional dependency. State is 'ok', 'warn', or 'missing'.
    """
    return [
        ("FluidSynth",      *_fluidsynth_status()),
        ("sf2utils",        *_present_status(Sf2File, "soundfont preset introspection")),
        ("python-osc",      *_present_status(pythonosc, "OSC instruments")),
        ("python-rtmidi",   *_present_status(rtmidi, "streaming MIDI I/O")),
        ("pynput",          *_present_status(pynput, "mouse/keyboard input")),
        ("abjad",           *_abjad_status()),
    ]


def print_dependency_status() -> None:
    """Print which optional features are available in this scamp install."""
    glyphs = {"ok": "✓", "warn": "~", "missing": "✗"}
    rows = dependency_status()
    width = max(len(name) for name, _, _ in rows)
    for name, state, detail in rows:
        print(f"  {glyphs[state]} {name:<{width}}  {detail}")
