"""
SCAMP: A Suite for Computer-Assisted Music in Python. SCAMP is an computer-assisted composition framework in Python
designed to act as a hub, flexibly connecting the composer-programmer to a wide variety of resources for playback and
notation.
"""

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

from clockblocks import Clock, TempoEnvelope, MetricPhaseTarget, wait, fork_unsynchronized, fork, current_clock, \
    wait_forever, wait_for_children_to_finish
from expenvelope import Envelope, EnvelopeSegment
from .session import Session
from .instruments import Ensemble, ScampInstrument, NoteHandle, ChordHandle
from .playback_implementations import PlaybackImplementation, OSCPlaybackImplementation, \
    MIDIStreamPlaybackImplementation, SoundfontPlaybackImplementation
from .transcriber import Transcriber
from .performance import Performance, PerformancePart
from .spelling import SpellingPolicy
from .score import Score, StaffGroup, Staff, Measure, Voice, Tuplet, NoteLike
from .text import StaffText
from .quantization import TimeSignature, QuantizationScheme, MeasureQuantizationScheme, BeatQuantizationScheme
from .settings import playback_settings, quantization_settings, engraving_settings
from ._midi import get_available_midi_input_devices, get_available_midi_output_devices, \
    print_available_midi_input_devices, print_available_midi_output_devices, get_port_number_of_midi_device
from .playback_adjustments import NotePlaybackAdjustment, ParamPlaybackAdjustment, PlaybackAdjustmentsDictionary
from .note_properties import NoteProperties
from ._package_info import version as __version__
from ._package_info import author as __author__

assert isinstance(playback_settings.adjustments, PlaybackAdjustmentsDictionary)
