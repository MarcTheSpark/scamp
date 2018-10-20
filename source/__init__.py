from .session import Session
from .envelope import Envelope
from .ensemble import Ensemble
from .instruments import MidiScampInstrument, ScampInstrument, OSCScampInstrument
from .clock import Clock, TempoEnvelope, wait
from .performance import Performance, PerformancePart
from .score import *
from .quantization import *
from .performance_note import PerformanceNote, NotePropertiesDictionary

__author__ = 'mpevans'
