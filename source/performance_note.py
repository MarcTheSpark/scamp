from playcorder.envelope import Envelope
from functools import total_ordering
from playcorder.utilities import SavesToJSON
import itertools
from copy import deepcopy

"""
Note: This is a separate file from performance.py, since it is used both in performance.py and score.py,
and since performance.py imports score.py
"""


@total_ordering
class PerformanceNote(SavesToJSON):

    def __init__(self, start_time, length, pitch, volume, properties):
        self.start_time = start_time
        self.length = length
        # if pitch is a tuple, this indicates a chord
        self.pitch = pitch
        self.volume = volume
        self.properties = properties

    @property
    def end_time(self):
        return self.start_time + self.length

    @end_time.setter
    def end_time(self, new_end_time):
        self.length = new_end_time - self.start_time

    def average_pitch(self):
        if isinstance(self.pitch, tuple):
            # it's a chord, so take the average of its members
            return sum(x.average_level() if isinstance(x, Envelope) else x for x in self.pitch) / len(self.pitch)
        else:
            return self.pitch.average_level() if isinstance(self.pitch, Envelope) else self.pitch

    def play(self, instrument, clock=None, blocking=True):
        if isinstance(self.pitch, tuple):
            instrument.play_chord(self.pitch, self.volume, self.length, self.properties, clock=clock, blocking=blocking)
        else:
            instrument.play_note(self.pitch, self.volume, self.length, self.properties, clock=clock, blocking=blocking)

    _id_generator = itertools.count()

    def split_at_beat(self, split_beat):
        if self.start_time < split_beat < self.end_time:
            second_part = deepcopy(self)
            second_part.start_time = split_beat
            second_part.end_time = self.end_time
            self.length = split_beat - self.start_time

            if self.pitch is not None:
                if isinstance(self.pitch, Envelope):
                    # if the pitch is a envelope, then we split it appropriately
                    pitch_curve_start, pitch_curve_end = self.pitch.split_at(self.length)
                    self.pitch = pitch_curve_start
                    second_part.pitch = pitch_curve_end
                elif isinstance(self.pitch, tuple) and isinstance(self.pitch[0], Envelope):
                    # if the pitch is a tuple of envelopes (glissing chord) then same idea
                    first_part_chord = []
                    second_part_chord = []
                    for pitch_curve in self.pitch:
                        assert isinstance(pitch_curve, Envelope)
                        pitch_curve_start, pitch_curve_end = pitch_curve.split_at(self.length)
                        first_part_chord.append(pitch_curve_start)
                        second_part_chord.append(pitch_curve_end)
                    self.pitch = tuple(first_part_chord)
                    second_part.pitch = tuple(second_part_chord)

                # also, if this isn't a rest, then we're going to need to keep track of ties that will be needed
                self.properties["_starts_tie"] = True
                second_part.properties["_ends_tie"] = True

                # we also want to keep track of which notes came from the same original note for doing ties and such
                if "_source_id" in self.properties:
                    second_part.properties["_source_id"] = self.properties["_source_id"]
                else:
                    second_part.properties["_source_id"] = self.properties["_source_id"] = \
                        next(PerformanceNote._id_generator)

            return self, second_part
        else:
            # since the expectation is a tuple as return value, in the event that the split does
            # nothing we return the note unaltered in a length-1 tuple
            return self,

    def __lt__(self, other):
        # this allows it to be compared with numbers. I use that below to bisect a list of notes
        if isinstance(other, PerformanceNote):
            return self.start_time < other.start_time
        else:
            return self.start_time < other

    def __eq__(self, other):
        if isinstance(other, PerformanceNote):
            return self.start_time == other.start_time
        else:
            return self.start_time == other

    def to_json(self):
        if isinstance(self.pitch, tuple):
            # if this is a chord
            json_pitch = [p.to_json() if isinstance(p, Envelope) else p for p in self.pitch]
            json_pitch.insert(0, "chord")  # indicates that it's a chord, since json can't distinguish tuples from lists
        elif isinstance(self.pitch, Envelope):
            json_pitch = self.pitch.to_json()
        else:
            json_pitch = self.pitch

        return {
            "start_time": self.start_time,
            "length": self.length,
            "pitch": json_pitch,
            "volume": self.volume.to_json() if isinstance(self.volume, Envelope) else self.volume,
            "properties": self.properties
        }

    @classmethod
    def from_json(cls, json_object):
        # if pitch is an array starting with "chord"
        if hasattr(json_object["pitch"], "__len__") and json_object["pitch"][0] == "chord":
            pitches = []
            for pitch in json_object["pitch"][1:]:  # ignore the "chord" indicator
                pitches.append(Envelope.from_json(pitch) if hasattr(pitch, "__len__") else pitch)
            json_object["pitch"] = tuple(pitches)
        # otherwise check if it's a Envelope
        elif hasattr(json_object["pitch"], "__len__"):
            json_object["pitch"] = Envelope.from_json(json_object["pitch"])

        if hasattr(json_object["volume"], "__len__"):
            json_object["volume"] = Envelope.from_json(json_object["volume"])
        return PerformanceNote(**json_object)

    def __repr__(self):
        return "PerformanceNote(start_time={}, length={}, pitch={}, volume={}, properties={})".format(
            self.start_time, self.length, self.pitch, self.volume, self.properties
        )
