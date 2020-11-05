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

from .settings import playback_settings
import logging
import os
import platform

ABJAD_MINIMUM_VERSION = "3.1"


try:
    if playback_settings.try_system_fluidsynth_first:
        # first choice: import using an installed version of pyfluidsynth
        logging.debug("Trying to load system copy of pyfluidsynth.")
        import fluidsynth
    else:
        # first choice: use the use the local, tweaked copy of pyfluidsynth (which will also try to
        # load up a local copy of the fluidsynth dll on Windows or dylib on MacOS)
        logging.debug("Trying to load copy of pyfluidsynth from within SCAMP package.")
        from ._thirdparty import fluidsynth
    logging.debug("Loading of pyfluidsynth succeeded.")
except (ImportError, AttributeError):
    logging.debug("Loading of pyfluidsynth failed.")
    try:
        if playback_settings.try_system_fluidsynth_first:
            # second choice: use the use the local, tweaked copy of pyfluidsynth (which will also try to
            # load up a local copy of the fluidsynth dll on Windows or dylib on MacOS)
            logging.debug("Trying to copy of pyfluidsynth from within SCAMP package.")
            from ._thirdparty import fluidsynth
        else:
            # second choice: import using an installed version of pyfluidsynth
            logging.debug("Trying to load system copy of pyfluidsynth.")
            import fluidsynth
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
    from sf2utils.sf2parse import Sf2File
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


# On Mac and Windows, try to add LilyPond to PATH, if it is installed, so that abjad can just work.
# This is hardly fool-proof, but should work if the user just installed LilyPond in the standard way
if platform.system() == "Darwin":
    if "/usr/local/bin" not in os.environ["PATH"]:
        os.environ["PATH"] += ":/usr/local/bin"
    if os.path.exists("/Applications/LilyPond.app/Contents/Resources/bin"):
        os.environ["PATH"] += ":/Applications/LilyPond.app/Contents/Resources/bin"
elif platform.system() == "Windows":
    if os.path.exists(r"C:\Program Files (x86)\LilyPond\usr\bin"):
        if not os.environ["PATH"].endswith(";"):
            os.environ["PATH"] += ";"
        os.environ["PATH"] += r"C:\Program Files (x86)\LilyPond\usr\bin;"
    elif os.path.exists(r"C:\Program Files\LilyPond\usr\bin"):
        if not os.environ["PATH"].endswith(";"):
            os.environ["PATH"] += ";"
        os.environ["PATH"] += r"C:\Program Files\LilyPond\usr\bin;"


def abjad():
    # we make this a function that returns the abjad module so that we don't have to load it unless we need it
    # (since it's kinda slow to load)
    try:
        import abjad as abjad_library
        if abjad_library.__version__ < ABJAD_MINIMUM_VERSION:
            logging.warning(
                "abjad version {} found, but version must be at least {}. "
                "Lilypond output will not be available".format(abjad_library.__version__, ABJAD_MINIMUM_VERSION)
            )
            abjad_library = None
    except ImportError:
        abjad_library = None
        logging.warning("abjad was not found; lilypond output will not be available.")
    return abjad_library


try:
    import pynput
except ImportError:
    pynput = None
    logging.warning("pynput was not found; mouse and keyboard input will not be available.")
