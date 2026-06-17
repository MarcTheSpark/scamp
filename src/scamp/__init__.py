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

from cb2 import (
    Clock, ClockFamilyOptions,
    TempoEnvelope, MetricPhaseTarget, Moment,
    DurationUnits, TempoUnits,
    ClockblocksError, ClockKilledError, DeadClockError,
    WrongThreadError, NoActiveClockError, NotMasterClockError,
    current_clock, wait, wait_forever, wait_for_children_to_finish, fork, fork_unsynchronized,
    set_tempo, set_rate, set_beat_length,
    get_tempo, get_rate, get_beat_length,
    set_tempo_target, set_rate_target, set_beat_length_target,
    set_tempo_targets, set_rate_targets, set_beat_length_targets,
    apply_tempo_function, apply_rate_function, apply_beat_length_function,
    apply_tempo_envelope, stop_tempo_loop_or_function,
)
from expenvelope import Envelope, EnvelopeSegment
from .session import Session
from .instruments import Ensemble, ScampInstrument, NoteHandle, ChordHandle
from .playback_implementations import PlaybackImplementation, OSCPlaybackImplementation, \
    MIDIStreamPlaybackImplementation, SoundfontPlaybackImplementation
from .transcriber import Transcriber
from .performance import Performance, PerformancePart, PerformanceNote
from .spelling import SpellingPolicy
from .score import Score, StaffGroup, Staff, Measure, Voice, Tuplet, NoteLike
from .text import StaffText
from .spanners import StartBracket, StartTrill, StartPedal, StartDashes, StartSlur, StartHairpin, StartPhrasingSlur, \
    ChangePedal, StopPedal, StopTrill, StopDashes, StopSlur, StopHairpin, StopPhrasingSlur, StopBracket
from .quantization import TimeSignature, QuantizationScheme, MeasureQuantizationScheme, BeatQuantizationScheme
from .settings import playback_settings, quantization_settings, engraving_settings
from ._midi import get_available_midi_input_devices, get_available_midi_output_devices, \
    print_available_midi_input_devices, print_available_midi_output_devices, get_port_number_of_midi_device
from .playback_adjustments import NotePlaybackAdjustment, ParamPlaybackAdjustment
from .note_properties import NoteProperties
import importlib.metadata
from ._soundfont_host import print_soundfont_presets
from ._dependencies import print_dependency_status, dependency_status


__version__ = importlib.metadata.version('scamp')
__author__ = importlib.metadata.metadata('scamp')['Author-email']
