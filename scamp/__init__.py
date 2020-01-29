"""
SCAMP: A Suite for Computer-Assisted Music in Python
"""

__author__ = 'mpevans'

from clockblocks import Clock, TempoEnvelope, MetricPhaseTarget, wait, fork_unsynchronized, fork, current_clock
from expenvelope import Envelope, EnvelopeSegment
from .session import Session
from .instruments import Ensemble, ScampInstrument, NoteHandle, ChordHandle
from .playback_implementations import *
from .transcriber import Transcriber
from .performance import Performance, PerformancePart
from .score import *
from .quantization import *
from .settings import *
from .soundfont_host import get_soundfont_presets, print_soundfont_presets, get_soundfont_presets_with_substring
from ._midi import get_available_midi_input_devices, get_available_midi_output_devices, \
    print_available_midi_input_devices, print_available_midi_output_devices, get_port_number_of_midi_device
from .playback_adjustments import NotePlaybackAdjustment, ParamPlaybackAdjustment, PlaybackAdjustmentsDictionary

assert isinstance(playback_settings, PlaybackSettings)
assert isinstance(quantization_settings, QuantizationSettings)
assert isinstance(engraving_settings, EngravingSettings)
assert isinstance(playback_settings.adjustments, PlaybackAdjustmentsDictionary)
