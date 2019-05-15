import itertools
from copy import deepcopy
from functools import total_ordering

from expenvelope import Envelope
from .utilities import SavesToJSON
from .note_properties import NotePropertiesDictionary
from .settings import engraving_settings

"""
Note: This is a separate file from performance.py, since it is used both in performance.py and score.py,
and since performance.py imports score.py
"""


@total_ordering
class PerformanceNote(SavesToJSON):

    def __init__(self, start_time, length, pitch, volume, properties):
        self.start_time = start_time
        # if length is a tuple, this indicates that the note is to be split into tied segments
        self.length = length
        # if pitch is a tuple, this indicates a chord
        self.pitch = pitch
        self.volume = volume
        self.properties = properties if isinstance(properties, NotePropertiesDictionary) \
            else NotePropertiesDictionary.from_unknown_format(properties)

    def length_sum(self):
        return sum(self.length) if hasattr(self.length, "__len__") else self.length

    @property
    def end_time(self):
        return self.start_time + self.length_sum()

    @end_time.setter
    def end_time(self, new_end_time):
        new_length = new_end_time - self.start_time
        if hasattr(self.length, "__len__"):
            ratio = new_length / self.length_sum()
            self.length = tuple(segment_length * ratio for segment_length in self.length)
        else:
            self.length = new_length

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

    @staticmethod
    def next_id():
        return next(PerformanceNote._id_generator)

    def divide_length_at_gliss_control_points(self):
        if not isinstance(self.pitch, Envelope):
            return
        control_points = self.pitch.times[1:-1] if engraving_settings.glissandi.consider_non_extrema_control_points \
            else self.pitch.local_extrema()
        for control_point in control_points:
            if control_point <= 0 or control_point >= self.length_sum():
                continue
            first_part, second_part = PerformanceNote._split_length(self.length, control_point)
            self.length = (first_part if isinstance(first_part, tuple) else (first_part, )) + \
                          (second_part if isinstance(second_part, tuple) else (second_part, ))

    @staticmethod
    def _split_length(length, split_point):
        """
        Utility method for splitting a note length into two pieces, including the case that the length is a tuple
        For instance, if length = (3, 2, 4) and the split_point = 4.5, this gives us the tuple (3, 1.5) and (0.5, 4)
        :param length: a note length, either a number or a tuple of numbers representing tied segments
        :param split_point: where to split the length
        :return: tuple of (first half length, second half length). Each of these lengths may themselves be a tuple,
        or may be a single number if they are not split.
        """
        # raise an error if we try to split at a non-positive value or a value greater than the length
        if split_point <= 0 or split_point >= (sum(length) if hasattr(length, "__len__") else length):
            raise ValueError("Split point outside of length tuple.")

        if hasattr(length, "__len__"):
            # tuple length
            part_sum = 0
            for i, segment_length in enumerate(length):
                if part_sum + segment_length < split_point:
                    part_sum += segment_length
                elif part_sum + segment_length == split_point:
                    first_part = length[:i + 1]
                    second_part = length[i + 1:]
                    return first_part if len(first_part) > 1 else first_part[0], \
                           second_part if len(second_part) > 1 else second_part[0]
                else:
                    first_part = length[:i] + (split_point - part_sum,)
                    second_part = (part_sum + segment_length - split_point,) + length[i + 1:]
                    return first_part if len(first_part) > 1 else first_part[0], \
                           second_part if len(second_part) > 1 else second_part[0]
        else:
            # simple length, not a tuple
            return split_point, length - split_point

    def split_at_beat(self, split_beat):
        """
        Splits this note at the given beat, returning a tuple of the pieces created
        :param split_beat: where to split (relative to the performance start time, not the note start time)
        :return: tuple of (first half note, second half note) if split beat is within the note.
        Otherwise just return the unchanged note in a length-1 tuple.
        """
        if not self.start_time < split_beat < self.end_time:
            # if we're asked to split at a beat that is outside the note, it has no effect
            # since the expectation is a tuple as return value, return the note unaltered in a length-1 tuple
            return self,
        else:
            second_part = deepcopy(self)
            second_part.start_time = split_beat
            self.length, second_part.length = PerformanceNote._split_length(self.length, split_beat - self.start_time)

            if self.pitch is not None:
                if isinstance(self.pitch, Envelope):
                    # if the pitch is a envelope, then we split it appropriately
                    pitch_curve_start, pitch_curve_end = self.pitch.split_at(self.length_sum())
                    self.pitch = pitch_curve_start
                    second_part.pitch = pitch_curve_end
                elif isinstance(self.pitch, tuple) and isinstance(self.pitch[0], Envelope):
                    # if the pitch is a tuple of envelopes (glissing chord) then same idea
                    first_part_chord = []
                    second_part_chord = []
                    for pitch_curve in self.pitch:
                        assert isinstance(pitch_curve, Envelope)
                        pitch_curve_start, pitch_curve_end = pitch_curve.split_at(self.length_sum())
                        first_part_chord.append(pitch_curve_start)
                        second_part_chord.append(pitch_curve_end)
                    self.pitch = tuple(first_part_chord)
                    second_part.pitch = tuple(second_part_chord)

                # also, if this isn't a rest, then we're going to need to keep track of ties that will be needed
                self.properties["_starts_tie"] = True
                second_part.properties["_ends_tie"] = True

                for articulation in self.properties.articulations:
                    if articulation in engraving_settings.articulation_split_protocols and \
                            engraving_settings.articulation_split_protocols[articulation] == "first":
                        # this articulation is about the attack, so should appear only in the first part
                        # of a split note, so remove it from the second
                        second_part.properties.articulations.remove(articulation)
                    elif articulation in engraving_settings.articulation_split_protocols and \
                            engraving_settings.articulation_split_protocols[articulation] == "last":
                        # this articulation is about the release, so should appear only in the second part
                        # of a split note, so remove it from the first
                        self.properties.articulations.remove(articulation)
                    elif articulation in engraving_settings.articulation_split_protocols and \
                            engraving_settings.articulation_split_protocols[articulation] == "both":
                        # this articulation is about the attack and release, but it doesn't really make
                        # sense to play it on a note the middle of a tied group
                        if self.properties.starts_tie() and self.properties.ends_tie():
                            self.properties.articulations.remove(articulation)
                        if second_part.properties.starts_tie() and second_part.properties.ends_tie():
                            second_part.properties.articulations.remove(articulation)
                    # note, if the split protocol says "all" (or doesn't exist), then we just
                    # default to keeping the articulation on everything

                # we also want to keep track of which notes came from the same original note for doing ties and such
                if "_source_id" in self.properties:
                    second_part.properties["_source_id"] = self.properties["_source_id"]
                else:
                    second_part.properties["_source_id"] = self.properties["_source_id"] = PerformanceNote.next_id()

            return self, second_part

    def split_at_length_divisions(self):
        """
        If the self.length is a tuple, indicating a set of tied constituents, splits this into separate PerformanceNotes
        :return: a list of pieces
        """

        if not hasattr(self.length, "__len__") or len(self.length) == 1:
            return self,
        pieces = [self]
        for piece_length in self.length:
            last_piece = pieces.pop()
            pieces.extend(last_piece.split_at_beat(last_piece.start_time + piece_length))
        return pieces

    def attempt_chord_merger_with(self, other):
        """
        Try to merge this note with another note to form a chord.
        :param other: another PerformanceNote
        :return: True if the merger works, False otherwise
        """
        assert isinstance(other, PerformanceNote)
        # to merge, the start time, length, and volume must match and the properties need to be compatible
        if self.start_time != other.start_time or self.length != other.length \
                or self.volume != other.volume or not self.properties.mergeable_with(other.properties):
            return False

        # since one or both of these notes might already be chords (i.e. have a tuple for pitch),
        # let's make both pitches into tuples to simplify the logic
        self_pitches = (self.pitch,) if not isinstance(self.pitch, tuple) else self.pitch
        other_pitches = (other.pitch,) if not isinstance(other.pitch, tuple) else other.pitch
        all_pitches_together = self_pitches + other_pitches

        # check if any of the pitches involved are envelopes (glisses) rather than static pitches
        if any(isinstance(x, Envelope) for x in all_pitches_together):
            # if so, then they had all better be envelopes
            if not all(isinstance(x, Envelope) for x in all_pitches_together):
                return False
            # and moreover, they should all be a shifted version of the first pitch
            # otherwise, we keep them separate; a chord should gliss as a block if it glisses at all
            if not all(x.is_shifted_version_of(all_pitches_together[0]) for x in all_pitches_together[1:]):
                return False

        # if we've made it to here, then the notes are fit to be merged
        # the one wrinkle is that the notes may not be in pitch order. Let's put them in pitch order,
        # and sort the noteheads at the same time so that they match up
        all_noteheads_together = self.properties.noteheads + other.properties.noteheads
        sorted_pitches_and_noteheads = sorted(
            zip(all_pitches_together, all_noteheads_together),
            key=lambda pair: pair[0].start_level() if isinstance(pair[0], Envelope) else pair[0]
        )
        # now we can set this note's pitches and noteheads accordingly
        self.pitch = tuple(pitch for pitch, notehead in sorted_pitches_and_noteheads)
        self.properties["noteheads"] = [notehead for pitch, notehead in sorted_pitches_and_noteheads]
        # and return true because we succeeded
        return True

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
        if isinstance(self.pitch, (tuple, list)):
            # if this is a chord
            json_pitch = [p.to_json() if isinstance(p, Envelope) else p for p in self.pitch]
        elif isinstance(self.pitch, Envelope):
            json_pitch = self.pitch.to_json()
        else:
            json_pitch = self.pitch

        return {
            "start_time": self.start_time,
            "length": self.length,
            "pitch": json_pitch,
            "volume": self.volume.to_json() if isinstance(self.volume, Envelope) else self.volume,
            "properties": self.properties.to_json()
        }

    @classmethod
    def from_json(cls, json_object):
        if isinstance(json_object["pitch"], (tuple, list)):
            # a tuple or list (should be a list since it's json) indicates a chord
            json_object["pitch"] = tuple(Envelope.from_json(pitch) if isinstance(pitch, dict) else pitch
                                         for pitch in json_object["pitch"])
        elif isinstance(json_object["pitch"], dict):
            # a dict indicates it's an envelope
            json_object["pitch"] = Envelope.from_json(json_object["pitch"])

        if isinstance(json_object["volume"], dict):
            json_object["volume"] = Envelope.from_json(json_object["volume"])

        if hasattr(json_object["length"], "__len__"):
            json_object["length"] = tuple(json_object["length"])

        json_object["properties"] = NotePropertiesDictionary.from_json(json_object["properties"])

        return PerformanceNote(**json_object)

    def __repr__(self):
        return "PerformanceNote(start_time={}, length={}, pitch={}, volume={}, properties={})".format(
            self.start_time, self.length, self.pitch, self.volume, self.properties
        )
