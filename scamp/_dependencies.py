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
from ._package_info import ABJAD_VERSION, ABJAD_MIN_VERSION
import logging
import os
import platform
from pathlib import Path

try:
    if playback_settings.try_system_fluidsynth_first:
        # first choice: import using an installed version of pyfluidsynth
        logging.debug("Trying to load system copy of pyfluidsynth.")
        import fluidsynth
    else:
        # first choice: use the local, tweaked copy of pyfluidsynth (which will also try to
        # load up a local copy of the fluidsynth dll on Windows or dylib on MacOS)
        logging.debug("Trying to load copy of pyfluidsynth from within SCAMP package.")
        from ._thirdparty import fluidsynth
    # Sometimes fluidsynth seems to load, but it's empty and doesn't have the Synth attribute.
    # this line will cause an AttributeError to be thrown and handled in that case
    fluidsynth.Synth
    logging.debug("Loading of pyfluidsynth succeeded.")
except (ImportError, AttributeError):
    logging.debug("Loading of pyfluidsynth failed.")
    try:
        if playback_settings.try_system_fluidsynth_first:
            # second choice: use the local, tweaked copy of pyfluidsynth (which will also try to
            # load up a local copy of the fluidsynth dll on Windows or dylib on MacOS)
            logging.debug("Trying to copy of pyfluidsynth from within SCAMP package.")
            from ._thirdparty import fluidsynth
        else:
            # second choice: import using an installed version of pyfluidsynth
            logging.debug("Trying to load system copy of pyfluidsynth.")
            import fluidsynth
        fluidsynth.Synth  # See note above
        logging.debug("Loading of pyfluidsynth succeeded.")
    except (ImportError, AttributeError):
        # if we're here, it's probably because fluidsynth wasn't installed
        logging.debug("Loading of pyfluidsynth failed again.")
        fluidsynth = None
        logging.warning("Fluidsynth could not be loaded; synth output will not be available.")

if fluidsynth is not None and playback_settings.default_audio_driver == "auto":
    print("Testing for working audio driver...")
    found_driver = False
    for driver in ['alsa', 'coreaudio', 'dsound', 'Direct Sound', 'oss', 'pulseaudio', 'jack', 'portaudio', 'sndmgr']:
        test_synth = fluidsynth.Synth()
        test_synth.start(driver=driver)
        if test_synth.audio_driver is not None:
            playback_settings.default_audio_driver = driver
            playback_settings.make_persistent()
            found_driver = True
            test_synth.delete()
            print("Found audio driver '{}'. This has been made the default, but it can be altered via "
                  "the playback settings.".format(driver))
            break
        test_synth.delete()
    if not found_driver:
        logging.warning("No working audio driver was found; synth output will not be available.")

try:
    from ._thirdparty.sf2or3utils.sf2parse import Sf2File
except ImportError:
    Sf2File = None
    logging.warning("sf2utils was not found; info about soundfont presets will not be available.")

try:
    import pythonosc
    import pythonosc.udp_client
    import pythonosc.dispatcher
    import pythonosc.osc_server
except ImportError:
    pythonosc = None
    logging.warning("pythonosc was not found; OSCScampInstrument will not function.")

try:
    import rtmidi
except ImportError:
    rtmidi = None
    logging.warning("python-rtmidi was not found; streaming midi input / output will not be available.")


def find_lilypond():
    # Look for the lilypond binary and return the directory in which it resides
    # searches in the platform-specific paths defined in engraving_settings.lilypond_search_paths, and returns
    # the first match
    if platform.system() not in engraving_settings.lilypond_search_paths:
        return None
    logging.warning("Searching for LilyPond binary (this may take a while and is normal on first run)")
    for lilypond_search_path in engraving_settings.lilypond_search_paths[platform.system()]:
        lsp = Path(lilypond_search_path).expanduser()
        if not lsp.exists():
            continue
        for potential_lp_binary in lsp.rglob("lilypond.exe" if platform.system() == "Windows" else "lilypond"):
            if not potential_lp_binary.is_file():
                continue
            logging.warning(f"LilyPond binary found at {str(potential_lp_binary.parent.resolve())}")
            return str(potential_lp_binary.parent.resolve())


# The first time we see that abjad is the wrong version, show a warning, but then set this flag and don't show it again
_abjad_warning_given = False

# Will need to search for lilypond binary if:
# - On Mac or Windows and we don't have a saved engraving_settings.lilypond_dir
# - We're on Windows and there is a saved engraving_settings.lilypond_dir, but no lilypond.exe is found there
# - We're on Mac and there is a saved engraving_settings.lilypond_dir, but no lilypond binary is found there
_perform_lilypond_search = \
    platform.system() in ("Darwin", "Windows") and engraving_settings.lilypond_dir is None or \
    platform.system() == "Windows" and not (Path(engraving_settings.lilypond_dir) / "lilypond.exe").exists() or \
    platform.system() == "Darwin" and not (Path(engraving_settings.lilypond_dir) / "lilypond").exists()


def abjad():
    # we make this a function that returns the abjad module so that we don't have to load it unless we need it
    # (since it's kinda slow to load)
    global _abjad_warning_given, _perform_lilypond_search
    try:
        import abjad as abjad_library
    except ImportError:
        raise ImportError("abjad was not found; LilyPond output is not available.")

    if not hasattr(abjad_library, '__version__'):
        if not _abjad_warning_given:
            logging.warning(
                f"abjad library is present, but its version could not be identified. Note that scamp requires abjad "
                f"version {ABJAD_MIN_VERSION}{ABJAD_VERSION}"
            )
            _abjad_warning_given = True
    elif abjad_library.__version__ < ABJAD_MIN_VERSION:
        raise ImportError(
            "abjad version {} found, but SCAMP is built for {}. "
            "Run `pip3 install abjad=={}` to upgrade."
            .format(abjad_library.__version__,
                    "version {}".format(ABJAD_VERSION) if ABJAD_MIN_VERSION == ABJAD_VERSION
                    else "versions {}-{}".format(ABJAD_MIN_VERSION, ABJAD_VERSION), ABJAD_VERSION,
                    ABJAD_VERSION)
        )
    elif abjad_library.__version__ > ABJAD_VERSION:
        if not _abjad_warning_given:
            logging.warning(
                "abjad version {} found, but SCAMP is built for earlier version {}. The newer version may not be "
                "backwards compatible. If errors occur, run `pip3 install abjad=={}` to downgrade."
                .format(abjad_library.__version__, ABJAD_VERSION, ABJAD_VERSION)
            )
            _abjad_warning_given = True


    if _perform_lilypond_search:
        # need to perform a lilypond search
        engraving_settings.lilypond_dir = find_lilypond()
        engraving_settings.make_persistent()
        # don't search again, since we already searched
        _perform_lilypond_search = False

    # add lilypond to PATH if needed
    if engraving_settings.lilypond_dir is not None:
        if platform.system() == "Windows":
            if not os.environ["PATH"].endswith(";"):
                os.environ["PATH"] += ";"
            os.environ["PATH"] += f"{engraving_settings.lilypond_dir}"
        else:
            os.environ["PATH"] += f":{engraving_settings.lilypond_dir}"

    return abjad_library


try:
    import pynput
except ImportError:
    pynput = None
    logging.warning("pynput was not found; mouse and keyboard input will not be available.")
