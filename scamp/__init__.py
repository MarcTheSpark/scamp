__author__ = 'mpevans'

from clockblocks import Clock, TempoEnvelope, wait, fork_unsynchronized, fork, current_clock
from expenvelope import Envelope, EnvelopeSegment
from .session import Session
from .ensemble import Ensemble
from .instruments import ScampInstrument, NoteHandle, ChordHandle
from .playback_implementations import *
from .transcriber import Transcriber
from .performance import Performance, PerformancePart
from .score import *
from .quantization import *
from .simple_rtmidi_wrapper import get_available_midi_output_devices
from .settings import *
from .soundfont_host import get_soundfont_presets, print_soundfont_presets, get_soundfont_presets_with_substring
from .midi_listener import get_available_ports_and_devices, get_port_number_of_device
from .playback_adjustments import NotePlaybackAdjustment, ParamPlaybackAdjustment, PlaybackAdjustmentsDictionary

assert isinstance(playback_settings, PlaybackSettings)
assert isinstance(quantization_settings, QuantizationSettings)
assert isinstance(engraving_settings, EngravingSettings)
assert isinstance(playback_settings.adjustments, PlaybackAdjustmentsDictionary)
