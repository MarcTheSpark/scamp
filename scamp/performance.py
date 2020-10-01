"""
Module containing the :class:`PerformanceNote`, :class:`PerformancePart`, and :class:`Performance` classes, which
represent transcriptions of notes played by a group of :class:`~scamp.instruments.ScampInstrument` objects. These
classes contain continuous time, pitch, volume, and other parameter data, which can then be quantized and converted
into the notation-based classes in the score module.
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

import bisect
from functools import total_ordering
from numbers import Real
from expenvelope import Envelope
from .note_properties import NoteProperties
from .settings import engraving_settings
from .quantization import quantize_performance_part, QuantizationRecord, QuantizationScheme
from .settings import quantization_settings
from clockblocks import Clock, TempoEnvelope, current_clock
from .instruments import Ensemble, ScampInstrument
from .score import Score, StaffGroup
from .utilities import SavesToJSON
import logging
from copy import deepcopy
import itertools
import textwrap
from typing import Union, Sequence, Tuple, Iterator, Callable


@total_ordering
class PerformanceNote(SavesToJSON):
    """
    Represents a single note played by a :class:`~scamp.instruments.ScampInstrument`.

    :param start_beat: the start beat of the note
    :param length: the length of the note in beats (either a float or a tuple of floats representing tied segments)
    :param pitch: the pitch of the note (float or Envelope)
    :param volume: the volume of the note (float or Envelope)
    :param properties: dictionary of note properties, or string representing those properties
    :ivar start_beat: the start beat of the note
    :ivar length: the length of the note in beats (either a float or a tuple of floats representing tied segments)
    :ivar pitch: the pitch of the note (float or Envelope); note that this can also be a tuple of pitches representing
        a chord, but that this usually happens in the process of quantization when notes that can be merged into
        chords are merged.
    :ivar volume: the volume of the note (float or Envelope)
    :ivar properties: dictionary of note properties, or string representing those properties
    """

    def __init__(self, start_beat: float, length: Union[float, Tuple[float]], pitch: Union[float, Envelope, Sequence],
                 volume: Union[float, Envelope], properties: dict):
        self.start_beat = start_beat
        # if length is a tuple, this indicates that the note is to be split into tied segments
        self.length = length
        # if pitch is a tuple, this indicates a chord
        self.pitch = pitch
        self.volume = volume
        self.properties = properties if isinstance(properties, NoteProperties) \
            else NoteProperties.from_unknown_format(properties)

    def length_sum(self) -> float:
        """
        Total length of this note, adding together any tied segments.
        (The attribute "length" can be a list of floats representing tied segments.)

        :return: length of note as a float
        """
        return sum(self.length) if hasattr(self.length, "__len__") else self.length

    @property
    def end_beat(self) -> float:
        """
        End beat of this note
        """
        return self.start_beat + self.length_sum()

    @end_beat.setter
    def end_beat(self, new_end_beat: float):
        new_length = new_end_beat - self.start_beat
        if hasattr(self.length, "__len__"):
            ratio = new_length / self.length_sum()
            self.length = tuple(segment_length * ratio for segment_length in self.length)
        else:
            self.length = new_length

    def average_pitch(self) -> float:
        """
        Averages the pitch of this note, accounting for if it's a glissando or a chord

        :return: the averaged pitch as a float
        """
        if isinstance(self.pitch, tuple):
            # it's a chord, so take the average of its members
            return sum(x.average_level() if isinstance(x, Envelope) else x for x in self.pitch) / len(self.pitch)
        else:
            return self.pitch.average_level() if isinstance(self.pitch, Envelope) else self.pitch

    def play(self, instrument: ScampInstrument, clock: Clock = None, blocking: bool = True) -> None:
        """
        Play this note with the given instrument on the given clock

        :param instrument: instrument to play back with
        :param clock: the clock to play back on (if None, infers it from context)
        :param blocking: if True, don't return until the note is done playing; if False, return immediately
        """
        if isinstance(self.pitch, tuple):
            instrument.play_chord(self.pitch, self.volume, self.length, self.properties, clock=clock, blocking=blocking)
        else:
            instrument.play_note(self.pitch, self.volume, self.length, self.properties, clock=clock, blocking=blocking)

    _id_generator = itertools.count()

    @staticmethod
    def next_id() -> int:
        """
        Return a new unique ID number for this note, different from all PerformanceNotes created so far.

        :return: id number (int)
        """
        return next(PerformanceNote._id_generator)

    def _divide_length_at_gliss_control_points(self):
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

    def split_at_beat(self, split_beat: float) -> Sequence['PerformanceNote']:
        """
        Splits this note at the given beat, returning a tuple of the pieces created

        :param split_beat: where to split (relative to the performance start time, not the note start time)
        :return: tuple of (first half note, second half note) if split beat is within the note.
            Otherwise just return the unchanged note in a length-1 tuple.
        """
        if not self.start_beat + 1e-10 < split_beat < self.end_beat - 1e-10:
            # if we're asked to split at a beat that is outside the note, it has no effect
            # since the expectation is a tuple as return value, return the note unaltered in a length-1 tuple
            return self,
        else:
            second_part = self.duplicate()
            second_part.start_beat = split_beat
            self.length, second_part.length = PerformanceNote._split_length(self.length, split_beat - self.start_beat)

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

                # clear all of the text for the second part, since we only need it at the start of the note
                second_part.properties.texts.clear()

                # we also want to keep track of which notes came from the same original note for doing ties and such
                if "_source_id" in self.properties.temp:
                    second_part.properties.temp["_source_id"] = self.properties.temp["_source_id"]
                else:
                    second_part.properties.temp["_source_id"] = \
                        self.properties.temp["_source_id"] = PerformanceNote.next_id()

            return self, second_part

    def split_at_length_divisions(self) -> Sequence['PerformanceNote']:
        """
        If the self.length is a tuple, indicating a set of tied constituents, splits this into separate PerformanceNotes

        :return: a list of pieces
        """

        if not hasattr(self.length, "__len__") or len(self.length) == 1:
            return self,
        pieces = [self]
        for piece_length in self.length:
            last_piece = pieces.pop()
            pieces.extend(last_piece.split_at_beat(last_piece.start_beat + piece_length))
        return pieces

    def attempt_chord_merger_with(self, other: 'PerformanceNote') -> bool:
        """
        Try to merge this note with another note to form a chord.
        Returns whether it worked or not, and when it did, has the side effect of changing this note into a chord
        that incorporates the other note.

        :param other: another PerformanceNote
        :return: True if the merger works, False otherwise
        """
        assert isinstance(other, PerformanceNote)
        # to merge, the start time, length, and volume must match and the properties need to be compatible
        if self.start_beat != other.start_beat or self.length != other.length \
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
            return self.start_beat < other.start_beat
        else:
            return self.start_beat < other

    def __eq__(self, other):
        if isinstance(other, PerformanceNote):
            return self.start_beat == other.start_beat
        else:
            return self.start_beat == other

    def _to_dict(self):
        return {
            "start_beat": self.start_beat,
            "length": self.length,
            "pitch": self.pitch,
            "volume": self.volume,
            "properties": self.properties
        }

    @classmethod
    def _from_dict(cls, json_dict):
        return PerformanceNote(**json_dict)

    def __repr__(self):
        return "PerformanceNote(start_beat={}, length={}, pitch={}, volume={}, properties={})".format(
            self.start_beat, self.length, self.pitch, self.volume, self.properties
        )


class PerformancePart(SavesToJSON):

    """
    Transcription of the notes played by a single :class:`~scamp.instruments.ScampInstrument`.
    Can be saved to and loaded from a json file and played back on a clock.

    :param instrument: the ScampInstrument associated with this part; used for playback
    :param name: The name of this part
    :param voices: either a list of PerformanceNotes (which is interpreted as one unnamed voice), a list of lists
        of PerformanceNotes (which is interpreted as several numbered voices), or a dictionary mapping voice names
        to lists of notes.
    :param instrument_id: a json serializable record of the instrument used
    :param voice_quantization_records: a record of how this part was quantized if it has been quantized
    :ivar instrument: the ScampInstrument associated with this part; used for playback
    :ivar name: The name of this part
    :ivar voices: dictionary mapping voice names to lists of notes.
    :ivar instrument_id: a json serializable record of the instrument used
    :ivar voice_quantization_records: dictionary mapping voice names to QuantizationRecords, if this is quantized
    """

    def __init__(self, instrument: ScampInstrument = None, name: str = None, voices: Union[dict, Sequence] = None,
                 instrument_id: Tuple[str, int] = None, voice_quantization_records: dict = None,
                 clef_preference: Sequence[Union[str, Tuple[str, Real]]] = None):
        self.instrument = instrument  # A ScampInstrument instance
        self.clef_preference = clef_preference if clef_preference is not None \
            else instrument.resolve_clef_preference() if instrument is not None \
            else engraving_settings.clefs_by_instrument["default"]
        # the name of the part can be specified directly, or if not derives from the instrument it's attached to
        # if the part is not attached to an instrument, it starts with a name of None
        self.name = name if name is not None else instrument.name if instrument is not None else None
        # this is used for serializing to and restoring from a json file. It should be enough to find
        # the instrument in the ensemble, so long as the ensemble is compatible.
        self._instrument_id = instrument_id if instrument_id is not None else \
            ((instrument.name, instrument.name_count) if instrument is not None else None)

        if voices is None:
            # no voices specified; create a dictionary with the catch-all voice "_unspecified_"
            self.voices = {"_unspecified_": []}
        elif isinstance(voices, dict):
            self.voices = {}
            for key, value in voices.items():
                # for each key, if it can be parsed as an integer, make sure it's doing so in only one way
                # this prevents confusion from two voices called "01" and "1" for instance
                try:
                    self.voices[str(int(key))] = value
                except ValueError:
                    self.voices[key] = value

            # make sure that the dict contains the catch-all voice "_unspecified_"
            if "_unspecified_" not in self.voices:
                self.voices["_unspecified_"] = []
        else:
            # a single voice or list of voices is given
            assert hasattr(voices, "__len__")
            # check if we were given a list of voices
            if hasattr(voices[0], "__len__"):
                # if so, just assign them numbers 1, 2, 3, 4...
                self.voices = {str(i+1): voice for i, voice in enumerate(voices)}
                # and add the unspecified voice
                self.voices["_unspecified_"] = []
            else:
                # otherwise, we should have just been given a single list of notes for an unspecified default voice
                assert all(isinstance(x, PerformanceNote) for x in voices)
                self.voices = {"_unspecified_": voices}

        # a record of the quantization that was applied to this part, if any
        self.voice_quantization_records = voice_quantization_records

    def add_note(self, note: PerformanceNote, voice: str = None) -> PerformanceNote:
        """
        Add a new Performance note to this PerformancePart.

        :param note: the note to add
        :param voice: name of the voice to which to add it (defaults to "_unspecified_")
        :return: the note you just added (for chaining purposes)
        """
        # the voice kwarg here is only used when reconstructing this from a json serialization
        if voice is not None:
            # if the voice kwarg is given, use it - it should be a string
            assert isinstance(voice, str)
            voice_name = voice
        elif note.properties.voice is not None:
            # if the note specifies its voice, use that
            voice_name = str(note.properties.voice)
        else:
            # otherwise, use the catch-all voice "_unspecified_"
            voice_name = "_unspecified_"

        # make sure an integer voice is formatted in a unique way
        try:
            voice_name = str(int(voice_name))
        except ValueError:
            pass

        # make sure we have an entry for the desired voice, or create one if not
        if voice_name not in self.voices:
            self.voices[voice_name] = []
        voice = self.voices[voice_name]

        last_note_start_beat = voice[-1].start_beat if len(voice) > 0 else 0
        voice.append(note)
        if note.start_beat < last_note_start_beat:
            # always keep self.notes sorted; if we're appending something that shouldn't be at the
            # very end, we'll need to sort the list after appending. This probably doesn't come up much.
            voice.sort()  # they are defined to sort by start_beat
        return note

    def new_note(self, start_beat: float, length, pitch, volume, properties: dict) -> PerformanceNote:
        """
        Construct and add a new PerformanceNote to this Performance

        :param start_beat: the start beat of the note
        :param length: length of the note in beats (either a float or a list of floats representing tied segments)
        :param pitch: pitch of the note (float, Envelope, or list to interpret as an envelope)
        :param volume: volume of the note (float or Envelope, or list to interpret as an envelope)
        :param properties: dictionary of note properties, or string representing those properties
        :return: the note just added
        """
        return self.add_note(PerformanceNote(start_beat, length, pitch, volume, properties))

    def set_instrument(self, instrument: ScampInstrument) -> None:
        """
        Set the instrument with which this PerformancePart will play back by default

        :param instrument: the instrument to use
        """
        self.instrument = instrument
        self._instrument_id = instrument.name, instrument.name_count

    @property
    def end_beat(self) -> float:
        """
        End beat of the last note in this part.
        """
        if len(self.voices) == 0:
            return 0
        return max(max(n.start_beat + n.length_sum() for n in voice) if len(voice) > 0 else 0
                   for voice in self.voices.values())

    def get_note_iterator(self, start_beat: float = 0, stop_beat: float = None,
                          selected_voices: Sequence[str] = None) -> Iterator[PerformanceNote]:
        """
        Returns an iterator returning all the notes from start_beat to stop_beat in the selected voices

        :param start_beat: beat to start on
        :param stop_beat: beat to stop on (None keeps going until the end of the part)
        :param selected_voices: which voices to take notes from (defaults to all if None)
        :return: an iterator
        """
        # we can be given a list of voices to play, or if none is specified, we play all of them
        selected_voices = self.voices.keys() if selected_voices is None else selected_voices
        all_notes = list(itertools.chain(*[self.voices[x] for x in selected_voices]))
        all_notes.sort()

        def iterator():
            note_index = bisect.bisect_left(all_notes, start_beat)
            while note_index < len(all_notes) and (stop_beat is None or all_notes[note_index].start_beat < stop_beat):
                yield all_notes[note_index]
                note_index += 1

        return iterator()

    def play(self, start_beat: float = 0, stop_beat: float = None, instrument: ScampInstrument = None,
             clock: Clock = None, blocking: bool = True, tempo_envelope: TempoEnvelope = None,
             selected_voices: Sequence[str] = None,
             note_filter: Callable[[PerformanceNote], PerformanceNote] = None) -> Clock:
        """
        Play this PerformancePart (or a selection of it)

        :param start_beat: Place to start playing from
        :param stop_beat: Place to stop playing at
        :param instrument: instrument to play back with
        :param clock: clock to use for playback
        :param blocking: if True, don't return until the part is done playing; if False, return immediately
        :param tempo_envelope: (optional) a tempo envelope to use for playback
        :param selected_voices: which voices to play back (defaults to all if None)
        :param note_filter: a function that takes the PerformanceNote about to be played and returns a modified
            PerformanceNote to play. NB: this will modify the original note unless the input to the function is
            duplicated and left unaltered!
        :return: the Clock on which playback takes place
        """
        instrument = self.instrument if instrument is None else instrument
        from scamp.instruments import ScampInstrument
        if not isinstance(instrument, ScampInstrument):
            raise ValueError("PerformancePart does not have a valid instrument and cannot play.")
        clock = Clock(instrument.name + " clock", pool_size=20) if clock is None else clock
        if not isinstance(clock, Clock):
            raise ValueError("PerformancePart was given an invalid clock.")
        stop_beat = self.end_beat if stop_beat is None else stop_beat
        if not stop_beat >= start_beat:
            raise ValueError("Stop beat must be after start beat.")

        def _play_thread(child_clock):
            note_iterator = self.get_note_iterator(start_beat, stop_beat, selected_voices)
            self.get_note_iterator(start_beat, stop_beat)
            try:
                current_note = next(note_iterator)
            except StopIteration:
                return

            child_clock.wait(current_note.start_beat - start_beat)

            while True:
                assert isinstance(current_note, PerformanceNote)
                if note_filter is not None:
                    note_filter(current_note).play(instrument, clock=child_clock, blocking=False)
                else:
                    current_note.play(instrument, clock=child_clock, blocking=False)

                try:
                    next_note = next(note_iterator)
                    child_clock.wait(next_note.start_beat - current_note.start_beat)

                    current_note = next_note
                except StopIteration:
                    # when done, wait for the children to finish
                    child_clock.wait(current_note.length_sum())
                    return

        if blocking:
            # clock blocked ;-)
            if tempo_envelope is not None:
                clock.tempo_envelope.append_envelope(tempo_envelope)
            _play_thread(clock)
            return clock
        else:
            sub_clock = clock.fork(_play_thread)
            if tempo_envelope is not None:
                sub_clock.tempo_envelope.append_envelope(tempo_envelope)
            return sub_clock

    def set_instrument_from_ensemble(self, ensemble: Ensemble) -> 'PerformancePart':
        """
        Set the default instrument to play back with based on the best fit in the given ensembel

        :param ensemble: the ensemble to search in
        :return: self
        """
        self.instrument = ensemble.get_instrument_by_name(*self._instrument_id)
        if self.instrument is None:
            logging.warning("No matching instrument could be found for part {}.".format(self.name))
        return self

    def quantize(self, quantization_scheme: QuantizationScheme = "default",
                 onset_weighting: float = "default",
                 termination_weighting: float = "default") -> 'PerformancePart':
        """
        Quantizes this PerformancePart according to the quantization_scheme

        :param quantization_scheme: the QuantizationScheme to use. If "default", uses the default time signature defined
            in the quantization_settings.
        :param onset_weighting: how much to weight note onsets in the quantization. If "default", uses the default
            value defined in the quantization_settings.
        :param termination_weighting: how much to weight note terminations in the quantization. If "default", uses the
            default value defined in the quantization_settings.
        :return: this PerformancePart, having been quantized
        """
        if quantization_scheme == "default":
            quantization_scheme = QuantizationScheme.from_time_signature(quantization_settings.default_time_signature)

        quantize_performance_part(self, quantization_scheme, onset_weighting=onset_weighting,
                                  termination_weighting=termination_weighting)
        return self

    def quantized(self, quantization_scheme: QuantizationScheme = "default",
                  onset_weighting: float = "default",
                  termination_weighting: float = "default") -> 'PerformancePart':
        """
        Same as quantize, except that it returns a new copy, rather than changing this PerformancePart in place.

        :param quantization_scheme: the QuantizationScheme to use. If "default", uses the default time signature defined
            in the quantization_settings.
        :param onset_weighting: how much to weight note onsets in the quantization. If "default", uses the default
            value defined in the quantization_settings.
        :param termination_weighting: how much to weight note terminations in the quantization. If "default", uses the
            default value defined in the quantization_settings.
        :return: a quantized copy of this PerformancePart
        """
        if quantization_scheme == "default":
            quantization_scheme = QuantizationScheme.from_time_signature(quantization_settings.default_time_signature)

        copy = PerformancePart(instrument=self.instrument, name=self.name, voices=deepcopy(self.voices),
                               instrument_id=self._instrument_id)
        quantize_performance_part(copy, quantization_scheme, onset_weighting=onset_weighting,
                                  termination_weighting=termination_weighting)
        return copy

    def is_quantized(self) -> bool:
        """
        Checks if this part has been quantized

        :return: True if quantized, False if not
        """
        return self.voice_quantization_records is not None

    def _get_longest_quantization_record(self):
        # useful if we want to get a sense of all the measures involved and their quantization,
        # since some voices may only last for a few measures and cut off early
        if len(self.voice_quantization_records) == 0:
            return None
        return max(self.voice_quantization_records.values(),
                   key=lambda quantization_record: len(quantization_record.quantized_measures))

    @property
    def measure_lengths(self) -> Sequence[float]:
        """
        If this PerformancePart has been quantized, gets the lengths of all the measures

        :return: list of measure lengths
        """
        assert self.is_quantized(), "Performance must be quantized to have measure lengths!"
        # base it on the longest quantization record
        return self._get_longest_quantization_record().measure_lengths

    def num_measures(self) -> int:
        """
        If this PerformancePart has been quantized, gets the number of measures

        :return: number of measures
        """
        assert self.is_quantized(), "Performance must be quantized to have a number of measures"
        longest_quantization_record = self._get_longest_quantization_record()
        return 0 if longest_quantization_record is None else \
            len(self._get_longest_quantization_record().quantized_measures)

    def to_staff_group(self) -> StaffGroup:
        """
        Converts this PerformancePart to a StaffGroup object.
        (Quantizes in a default way, if necessary, but it should be quantized already.)

        :return: a new StaffGroup made from this PerformancePart
        """
        if not self.is_quantized():
            logging.warning("PerformancePart was not quantized before calling to_staff_group(); "
                            "quantizing according to default quantization time_signature")
            quantization_scheme = QuantizationScheme.from_time_signature(quantization_settings.default_time_signature)
            return self.quantized(quantization_scheme).to_staff_group()
        return StaffGroup.from_quantized_performance_part(self)

    def name_count(self) -> int:
        """
        When there are multiple instrument of the same name in an ensemble, keeps track of which one we mean

        :return: int representing which instrument we mean
        """
        return self._instrument_id[1]

    def _to_dict(self):
        return {
            "name": self.name,
            "instrument_id": self._instrument_id,
            "clef_preference": self.clef_preference,
            "voices": self.voices,
            "voice_quantization_records": self.voice_quantization_records
        }

    @classmethod
    def _from_dict(cls, json_dict):
        return cls(**json_dict)

    def __repr__(self):
        voice_strings = [
            "{}: [\n{}\n]".format("'" + voice_name + "'" if isinstance(voice_name, str) else voice_name,
                                  textwrap.indent(",\n".join(str(x) for x in self.voices[voice_name]), "   "))
            for voice_name in self.voices
        ]
        return "PerformancePart(name=\'{}\', instrument_id={}, voices={}{}".format(
            self.name, self._instrument_id,
            "{{\n{}\n}}".format(textwrap.indent(",\n".join(voice_strings), "   ")),
            ", quantization_record={})".format(self.voice_quantization_records)
            if self.voice_quantization_records is not None else ")"
        )


class Performance(SavesToJSON):

    """
    Representation of note playback events, usually a transcription of the notes played by an
    :class:`~scamp.instruments.Ensemble`. Operates in continuous time, without regard to any particular way of notating
    it. (As opposed to a :class:`~scamp.score.Score`, which represents the notated music.)

    :param parts: list of parts (:class:`PerformancePart` objects) to start with (defaults to empty list)
    :param tempo_envelope: a tempo_envelope to associate with this performance
    :ivar parts: list of parts (:class:`PerformancePart` objects) in this Performance
    :ivar tempo_envelope: the tempo_envelope associated this performance and used for playback by default
    """

    def __init__(self, parts: Sequence[PerformancePart] = None, tempo_envelope: TempoEnvelope = None):
        self.parts = [] if parts is None else parts
        self.tempo_envelope = TempoEnvelope() if tempo_envelope is None else tempo_envelope
        assert isinstance(self.parts, list) and all(isinstance(x, PerformancePart) for x in self.parts)

    def new_part(self, instrument: ScampInstrument = None) -> PerformancePart:
        """
        Construct and add a new PerformancePart to this Performance

        :param instrument: the instrument to use as a default for playing back the part
        :return: the newly constructed part
        """
        new_part = PerformancePart(instrument)
        self.parts.append(new_part)
        return new_part

    def add_part(self, part: PerformancePart) -> None:
        """
        Add the given PerformancePart to this performance

        :param part: a PerformancePart to add
        """
        self.parts.append(part)

    def get_part_by_index(self, index: int) -> PerformancePart:
        """
        Get the part with the given index
        (Parts are numbered starting with 0, in order that they are added/created.)

        :param index: the index of the part in question
        :return: the PerformancePart
        """
        return self.parts[index]

    def get_parts_by_name(self, name: str) -> Sequence[PerformancePart]:
        """
        Get all parts with the given name

        :param name: the part name to search for
        :return: a list of parts with this name
        """
        return [x for x in self.parts if x.name == name]

    def get_parts_by_instrument(self, instrument: ScampInstrument) -> Sequence[PerformancePart]:
        """
        Get all parts with the given instrument

        :param instrument: the instrument to search for
        :return: a list of parts with this instrument
        """
        return [x for x in self.parts if x.instrument == instrument]

    @property
    def end_beat(self) -> float:
        """
        The end beat of this performance.
        (i.e. the beat corresponding to the end of the last note)

        :return: float representing the beat at which all notes are done playing
        """
        return max(p.end_beat for p in self.parts)

    def length(self) -> float:
        """
        Total length of this performance. (Identical to Performance.end_beat)

        :return: float representing the total length of the Performance
        """
        return self.end_beat

    def get_note_iterator(self, start_beat: float = 0, stop_beat: float = None,
                          selected_voices: Sequence[str] = None) -> Iterator[PerformanceNote]:
        """
        Returns an iterator returning all the notes from start_beat to stop_beat in the selected voices, in all parts.
        In order of start time, jumping from part to part as needed.

        :param start_beat: beat to start on
        :param stop_beat: beat to stop on (None keeps going until the end of the part)
        :param selected_voices: which voices to take notes from (defaults to all if None)
        :return: an iterator
        """
        part_note_iterators = [p.get_note_iterator(start_beat, stop_beat, selected_voices) for p in self.parts]

        next_notes = []
        for part_note_iterator in part_note_iterators:
            try:
                next_notes.append(next(part_note_iterator))
            except StopIteration:
                next_notes.append(None)

        while not all(x is None for x in next_notes):
            note_to_pop = min(range(len(next_notes)),
                              key=lambda i: next_notes[i].start_beat if next_notes[i] is not None else float("inf"))
            yield(next_notes[note_to_pop])
            try:
                next_notes[note_to_pop] = next(part_note_iterators[note_to_pop])
            except StopIteration:
                next_notes[note_to_pop] = None

    def apply_note_filter(self, filter_function: Callable[['PerformanceNote'], None],
                          start_beat: float = 0, stop_beat: float = None,
                          selected_voices: Sequence[str] = None) -> 'Performance':
        """
        Applies a filter function to every note in this Performance. This can be used to apply a transformation to
        the entire Performance on a note-by-note basis.

        :param filter_function: function taking a PerformanceNote object and modifying it in place
        :param start_beat: beat to start on
        :param stop_beat: beat to stop on (None keeps going until the end of the part)
        :param selected_voices: which voices to take notes from (defaults to all if None)
        :return: self, for chaining purposes
        """
        for note in self.get_note_iterator(start_beat, stop_beat, selected_voices):
            filter_function(note)
        return self

    def apply_pitch_filter(self, filter_function: Callable[[Union[Envelope, float]], Union[Envelope, float]],
                           start_beat: float = 0, stop_beat: float = None,
                           selected_voices: Sequence[str] = None) -> 'Performance':
        """
        Applies a filter function to transform the pitch of every note in this Performance.

        :param filter_function: function taking a pitch (can be envelope, float, or even a chord tuple) and returning
            another pitch-like object. If the performance hasn't been quantized and you're not using any glissandi,
            though, you can assume the pitch is a float.
        :param start_beat: beat to start on
        :param stop_beat: beat to stop on (None keeps going until the end of the part)
        :param selected_voices: which voices to take notes from (defaults to all if None)
        :return: self, for chaining purposes
        """
        def _note_filter(performance_note):
            performance_note.pitch = filter_function(performance_note.pitch)

        self.apply_note_filter(_note_filter, start_beat, stop_beat, selected_voices)
        return self

    def transpose(self, interval: float) -> 'Performance':
        """
        Transposes all notes in this Performance up or down by the desired interval. For greater flexibility, use the
        :code:`apply_pitch_filter` and :code:`apply_note_filter` methods.

        :param interval: the interval by which to transpose this Performance
        :return: self, for chaining purposes
        """
        return self.apply_pitch_filter(lambda p: p + interval)

    def apply_volume_filter(self, filter_function: Callable[[Union[Envelope, float]], Union[Envelope, float]],
                            start_beat: float = 0, stop_beat: float = None,
                            selected_voices: Sequence[str] = None) -> 'Performance':
        """
        Applies a filter function to transform the volume of every note in this Performance.

        :param filter_function: function taking a volume (can be envelope or float) and returning
            another volume-like object. If you haven't used any envelopes, though, you can assume the pitch is a float.
        :param start_beat: beat to start on
        :param stop_beat: beat to stop on (None keeps going until the end of the part)
        :param selected_voices: which voices to take notes from (defaults to all if None)
        :return: self, for chaining purposes
        """
        def _note_filter(performance_note):
            performance_note.volume = filter_function(performance_note.volume)

        self.apply_note_filter(_note_filter, start_beat, stop_beat, selected_voices)
        return self

    def play(self, start_beat: float = 0, stop_beat: float = None, ensemble: Ensemble = "auto",
             clock: Clock = "auto", blocking: bool = True, tempo_envelope: TempoEnvelope = "auto",
             note_filter: Callable[[PerformanceNote], PerformanceNote] = None) -> Clock:
        """
        Play back this Performance (or a selection of it)

        :param start_beat: Place to start playing from
        :param stop_beat: Place to stop playing at
        :param ensemble: The Ensemble whose instruments to use for playback. If "auto", checks to see if we are
            operating in a particular Session, and uses those instruments if so.
        :param clock: clock to use for playback
        :param blocking: if True, don't return until the part is done playing; if False, return immediately
        :param tempo_envelope: the TempoEnvelope with which to play back this performance. The default value of "auto"
            uses  the tempo_envelope associated with the performance, and None uses a flat tempo of rate 60bpm
        :param note_filter: a function that takes the PerformanceNote about to be played and returns a modified
            PerformanceNote to play. NB: this will modify the original note unless the input to the function is
            duplicated and left unaltered!

        :return: the clock on which this performance is playing back
        """
        if clock == "auto":
            clock = current_clock()
        if ensemble == "auto":
            # using the given clock (or the current clock on this thread as a fallback)...
            c = clock if isinstance(clock, Clock) else current_clock()

            # ... see if that clock is an Ensemble (and therefore probably a Session)
            if c is not None and isinstance(c.master, Ensemble):
                # and if so, use that as to set the instruments
                ensemble = c.master
        elif isinstance(ensemble, Sequence):
            ensemble = Ensemble(instruments=ensemble)

        if ensemble is not None:
            self.set_instruments_from_ensemble(ensemble, override=False)

        # if not given a valid clock, create one
        if not isinstance(clock, Clock):
            clock = Clock()

        if tempo_envelope == "auto":
            tempo_envelope = self.tempo_envelope

        if stop_beat is None:
            stop_beat = max(p.end_beat for p in self.parts)

        def _performance_playback(performance_playback_clock):
            for p in self.parts:
                p.play(start_beat, stop_beat, clock=performance_playback_clock, blocking=False,
                       tempo_envelope=tempo_envelope, note_filter=note_filter)
            performance_playback_clock.wait_for_children_to_finish()

        if blocking:
            _performance_playback(clock)
            return clock
        else:
            return clock.fork(_performance_playback)

    def set_instruments_from_ensemble(self, ensemble: Ensemble, override: bool = True) -> 'Performance':
        """
        Set the playback instruments for each part in this Performance by their best match in the ensemble given.
        If override is False, only set the instrument for parts that don't already have one set.

        :param ensemble: the Ensemble in which to search for instruments
        :param override: Whether or not to override any instruments already assigned to parts
        :return: self
        """
        for part in self.parts:
            if override or part.instrument is None:
                part.set_instrument_from_ensemble(ensemble)
        return self

    def quantize(self, quantization_scheme: QuantizationScheme = "default", onset_weighting: float = "default",
                 termination_weighting: float = "default") -> 'Performance':
        """
        Quantizes all parts according to the quantization_scheme

        :param quantization_scheme: the QuantizationScheme to use. If "default", uses the default time signature defined
            in the quantization_settings.
        :param onset_weighting: how much to weight note onsets in the quantization. If "default", uses the default
            value defined in the quantization_settings.
        :param termination_weighting: how much to weight note terminations in the quantization. If "default", uses the
            default value defined in the quantization_settings.
        :return: this Performance, having been quantized
        """
        if quantization_scheme == "default":
            logging.warning("No quantization scheme given; quantizing according to default time signature.")
            quantization_scheme = QuantizationScheme.from_time_signature(quantization_settings.default_time_signature)

        for part in self.parts:
            part.quantize(quantization_scheme, onset_weighting=onset_weighting,
                          termination_weighting=termination_weighting)
        return self

    def quantized(self, quantization_scheme: QuantizationScheme = "default", onset_weighting: float = "default",
                  termination_weighting: float = "default") -> 'Performance':
        """
        Same as quantize, except that it returns a new copy, rather than changing this Performance in place.

        :param quantization_scheme: the QuantizationScheme to use. If "default", uses the default time signature defined
            in the quantization_settings.
        :param onset_weighting: how much to weight note onsets in the quantization. If "default", uses the default
            value defined in the quantization_settings.
        :param termination_weighting: how much to weight note terminations in the quantization. If "default", uses the
            default value defined in the quantization_settings.
        :return: a quantized copy of this Performance
        """
        if quantization_scheme == "default":
            quantization_scheme = QuantizationScheme.from_time_signature(quantization_settings.default_time_signature)

        return Performance([part.quantized(quantization_scheme, onset_weighting=onset_weighting,
                                           termination_weighting=termination_weighting)
                            for part in self.parts], tempo_envelope=self.tempo_envelope)

    def is_quantized(self) -> bool:
        """
        Checks if this Performance has been quantized

        :return: True if all parts are quantized, False if not
        """
        return all(part.is_quantized() for part in self.parts)

    def num_measures(self) -> int:
        """
        If this Performance has been quantized, gets the number of measures

        :return: number of measures
        """
        return max(part.num_measures() for part in self.parts)

    def warp_to_tempo_curve(self, tempo_curve):
        """
        (Not yet implemented)
        """
        raise NotImplementedError()

    def to_score(self, quantization_scheme: QuantizationScheme = None, time_signature: Union[str, Sequence] = None,
                 bar_line_locations: Sequence[float] = None, max_divisor: int = None,
                 max_divisor_indigestibility: int = None, simplicity_preference: float = None, title: str = "default",
                 composer: str = "default") -> Score:
        """
        Convert this Performance (list of note events in continuous time and pitch) to a Score object, which represents
        the music in traditional western notation. In the process, the music must be quantized, for which two different
        options are available: one can either pass a QuantizationScheme to the first argument, which is very flexible
        but rather verbose to create, or one can specify arguments such as time signature and max divisor directly.

        :param quantization_scheme: The quantization scheme to be used when converting this performance into a score. If
            this is defined, none of the other quantization-related arguments should be defined.
        :param time_signature: the time signature to be used, represented as a string, e.g. "3/4",  or a tuple,
            e.g. (3, 2). Alternatively, a list of time signatures can be given. If this list ends in "loop", then the
            pattern specified by the list will be looped. For example, ["4/4", "2/4", "3/4", "loop"] will cause the
            fourth measure to be in "4/4", the fifth in "2/4", etc. If the list does not end in "loop", all measures
            after the final time signature specified will continue to be in that time signature.
        :param bar_line_locations: As an alternative to defining the time signatures, a list of numbers representing
            the bar line locations can be given. For instance, [4.5, 6.5, 8, 11] would result in bars of time signatures
            9/8, 2/4, 3/8, and 3/4
        :param max_divisor: The largest divisor that will be allowed to divide the beat.
        :param max_divisor_indigestibility: Indigestibility, devised by composer Clarence Barlow, is a measure of the
            "primeness" of a beat divisor, and therefore of its complexity from the point of view of a performer. For
            instance, it is easier to divide a beat in 8 than in 7, even though 7 is a smaller number. See Clarence's
            paper here: https://mat.ucsb.edu/Publications/Quantification_of_Harmony_and_Metre.pdf. By setting a max
            indigestibility, we can allow larger divisions of the beat, but only so long as they are easy ones. For
            instance, a max_divisor of 16 and a max_divisor_indigestibility of 8 would allow the beat to be divided
            in 1, 2, 3, 4, 5, 6, 8, 9, 10, 12, and 16.
        :param simplicity_preference: This defines the degree to which the quantizer will favor simple divisors. The
            higher the simplicity preference, the more precisely the notes have to fit for you to get a divisor like 7.
            Simplicity preference can range from 0 (in which case the divisor is chosen purely based on the lowest
            error) to infinity, with a typical value somewhere around 1.
        :param title: Title of the piece to be printed on the score.
        :param composer: Composer of the piece to be printed on the score.
        :return: the resulting Score object, which can then be rendered either as XML or LilyPond
        """
        return Score.from_performance(
            self, quantization_scheme, time_signature=time_signature, bar_line_locations=bar_line_locations,
            max_divisor=max_divisor, max_divisor_indigestibility=max_divisor_indigestibility,
            simplicity_preference=simplicity_preference, title=title, composer=composer
        )

    def _to_dict(self):
        return {"parts": self.parts, "tempo_envelope": self.tempo_envelope}

    @classmethod
    def _from_dict(cls, json_dict):
        return cls(**json_dict)

    def __repr__(self):
        return "Performance([\n{}\n])".format(
            textwrap.indent(",\n".join(str(x) for x in self.parts), "   ")
        )
