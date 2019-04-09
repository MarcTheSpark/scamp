__author__ = 'mpevans'

from clockblocks import Clock, TempoEnvelope, wait
from expenvelope import Envelope
from .session import Session
from .ensemble import Ensemble
from .instruments import MidiScampInstrument, ScampInstrument, OSCScampInstrument
from .performance import Performance, PerformancePart
from .score import *
from .quantization import *
from .simple_rtmidi_wrapper import get_available_midi_output_devices
from .settings import *
from .soundfont_host import get_soundfont_presets, print_soundfont_presets, get_soundfont_presets_with_substring

assert isinstance(playback_settings, PlaybackSettings)
assert isinstance(quantization_settings, QuantizationSettings)
assert isinstance(engraving_settings, EngravingSettings)
