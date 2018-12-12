__author__ = 'mpevans'

from .session import Session
from .envelope import Envelope
from .ensemble import Ensemble
from .instruments import MidiScampInstrument, ScampInstrument, OSCScampInstrument
from .clock import Clock, TempoEnvelope, wait
from .performance import Performance, PerformancePart
from .score import *
from .quantization import *
from .performance_note import PerformanceNote, NotePropertiesDictionary
from .simple_rtmidi_wrapper import get_available_midi_output_devices
from .settings import *

assert isinstance(playback_settings, PlaybackSettings)
assert isinstance(quantization_settings, QuantizationSettings)
assert isinstance(engraving_settings, EngravingSettings)
