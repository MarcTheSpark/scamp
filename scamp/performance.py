import bisect
from .quantization import quantize_performance_part, QuantizationRecord, QuantizationScheme
from .settings import quantization_settings
from clockblocks import Clock, TempoEnvelope, current_clock
from .ensemble import Ensemble
from .performance_note import *
from .score import Score, StaffGroup
from .utilities import SavesToJSON
import logging
from copy import deepcopy
import itertools
import textwrap


class PerformancePart(SavesToJSON):

    def __init__(self, instrument=None, name=None, voices=None, instrument_id=None, voice_quantization_records=None):
        """
        Transcription of the notes played by a single ScampInstrument.
        Can be saved to and loaded from a json file and played back on a clock.

        :param instrument: the ScampInstrument associated with this part; used for playback
        :param name: The name of this part
        :param voices: either a list of PerformanceNotes (which is interpreted as one unnamed voice), a list of lists
            of PerformanceNotes (which is interpreted as several numbered voices), or a dictionary mapping voice names
            to lists of notes.
        :param instrument_id: a json serializable record of the instrument used
        :param voice_quantization_records: a record of how this part was quantized if it has been quantized
        """
        self.instrument = instrument  # A ScampInstrument instance
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

    def add_note(self, note: PerformanceNote, voice=None):
        """
        Add a new Performance note to this PerformancePart.

        :param note: the note to add
        :type note: PerformanceNote
        :param voice: name of the voice to which to add it (defaults to "_unspecified_")
        :type voice: str
        """
        # the voice kwarg here is only used when reconstructing this from a json serialization
        if voice is not None:
            # if the voice kwarg is given, use it - it should be a string
            assert isinstance(voice, str)
            voice_name = voice
        elif "voice" in note.properties:
            # if the note specifies its voice, use that
            voice_name = str(note.properties["voice"])
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

        last_note_start_time = voice[-1].start_time if len(voice) > 0 else 0
        voice.append(note)
        if note.start_time < last_note_start_time:
            # always keep self.notes sorted; if we're appending something that shouldn't be at the
            # very end, we'll need to sort the list after appending. This probably doesn't come up much.
            voice.sort()  # they are defined to sort by start_time

    def new_note(self, start_time, length, pitch, volume, properties):
        """
        Construct and add a new PerformanceNote to this Performance

        :param start_time: the start time of the note (in beats)
        :type start_time: float
        :param length: length of the note in beats (either a float or a list of floats representing tied segments)
        :param pitch: pitch of the note (float or Envelope)
        :param volume: volume of the note (float or Envelope)
        :param properties: dictionary of note properties, or string representing those properties
        :return: the note just added
        """
        return self.add_note(PerformanceNote(start_time, length, pitch, volume, properties))

    def set_instrument(self, instrument):
        """
        Set the instrument with which this PerformancePart will play back by default

        :param instrument: the instrument to use
        :type instrument: ScampInstrument
        """
        self.instrument = instrument
        self._instrument_id = instrument.name, instrument.name_count

    @property
    def end_time(self):
        """
        End beat of the note (based on start_time and length)
        """
        if len(self.voices) == 0:
            return 0
        return max(max(n.start_time + n.length_sum() for n in voice) if len(voice) > 0 else 0
                   for voice in self.voices.values())

    def get_note_iterator(self, start_time=0, stop_time=None, selected_voices=None):
        """
        Returns an iterator returning all the notes from start_time to stop_time in the selected voices

        :param start_time: beat to start on
        :param stop_time: beat to stop on (None keeps going until the end of the part)
        :param selected_voices: which voices to take notes from (defaults to all if None)
        :return: an iterator
        """
        # we can be given a list of voices to play, or if none is specified, we play all of them
        selected_voices = self.voices.keys() if selected_voices is None else selected_voices
        all_notes = list(itertools.chain(*[self.voices[x] for x in selected_voices]))
        all_notes.sort()

        def iterator():
            note_index = bisect.bisect_left(all_notes, start_time)
            while note_index < len(all_notes) and (stop_time is None or all_notes[note_index].start_time < stop_time):
                yield all_notes[note_index]
                note_index += 1

        return iterator()

    def play(self, start_time=0, stop_time=None, instrument=None, clock=None, blocking=True,
             tempo_envelope=None, selected_voices=None):
        """
        Play this PerformancePart (or a selection of it)

        :param start_time: Place to start playing from
        :type start_time: float
        :param stop_time: Place to stop playing at
        :type stop_time: float
        :param instrument: instrument to play back with
        :type instrument: ScampInstrument
        :param clock: clock to use for playback
        :type clock: Clock
        :param blocking: if True, don't return until the part is done playing; if False, return immediately
        :type blocking: bool
        :param tempo_envelope: (optional) a tempo envelope to use for playback
        :param selected_voices: which voices to play back (defaults to all if None)
        """
        instrument = self.instrument if instrument is None else instrument
        from scamp.instruments import ScampInstrument
        if not isinstance(instrument, ScampInstrument):
            raise ValueError("PerformancePart does not have a valid instrument and cannot play.")
        clock = Clock(instrument.name + " clock", pool_size=20) if clock is None else clock
        if not isinstance(clock, Clock):
            raise ValueError("PerformancePart was given an invalid clock.")
        stop_time = self.end_time if stop_time is None else stop_time
        if not stop_time >= start_time:
            raise ValueError("Stop time must be after start time.")

        def _play_thread(child_clock):
            note_iterator = self.get_note_iterator(start_time, stop_time, selected_voices)
            self.get_note_iterator(start_time, stop_time)
            try:
                current_note = next(note_iterator)
            except StopIteration:
                return

            child_clock.wait(current_note.start_time - start_time)

            while True:
                assert isinstance(current_note, PerformanceNote)
                current_note.play(instrument, clock=child_clock, blocking=False)

                try:
                    next_note = next(note_iterator)
                    child_clock.wait(next_note.start_time - current_note.start_time)

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

    def set_instrument_from_ensemble(self, ensemble):
        """
        Set the default instrument to play back with based on the best fit in the given ensembel

        :param ensemble: the ensemble to search in
        :type ensemble: Ensemble
        :return: self
        """
        self.instrument = ensemble.get_instrument_by_name(*self._instrument_id)
        if self.instrument is None:
            logging.warning("No matching instrument could be found for part {}.".format(self.name))
        return self

    def quantize(self, quantization_scheme="default", onset_weighting="default", termination_weighting="default"):
        """
        Quantizes this PerformancePart according to the quantization_scheme

        :param quantization_scheme: the QuantizationScheme to use. If "default", uses the default time signature defined
            in the quantization_settings.
        :param onset_weighting: how much to weight note onsets in the quantization.
        :type onset_weighting: float
        :param termination_weighting: how much to weight note terminations in the quantization.
        :type termination_weighting: float
        :return: this PerformancePart, having been quantized
        """
        if quantization_scheme == "default":
            quantization_scheme = QuantizationScheme.from_time_signature(quantization_settings.default_time_signature)

        quantize_performance_part(self, quantization_scheme, onset_weighting=onset_weighting,
                                  termination_weighting=termination_weighting)
        return self

    def quantized(self, quantization_scheme="default", onset_weighting="default", termination_weighting="default"):
        """
        Same as quantize, except that it returns a new copy, rather than changing this PerformancePart in place.

        :param quantization_scheme: the QuantizationScheme to use. If "default", uses the default time signature defined
            in the quantization_settings.
        :param onset_weighting: how much to weight note onsets in the quantization.
        :type onset_weighting: float
        :param termination_weighting: how much to weight note terminations in the quantization.
        :type termination_weighting: float
        :return: a quantized copy of this PerformancePart
        """
        if quantization_scheme == "default":
            quantization_scheme = QuantizationScheme.from_time_signature(quantization_settings.default_time_signature)

        copy = PerformancePart(instrument=self.instrument, name=self.name, voices=deepcopy(self.voices),
                               instrument_id=self._instrument_id)
        quantize_performance_part(copy, quantization_scheme, onset_weighting=onset_weighting,
                                  termination_weighting=termination_weighting)
        return copy

    def is_quantized(self):
        """
        Checks if this part has been quantized

        :return: True if quantized, False if not
        """
        return self.voice_quantization_records is not None

    def _get_longest_quantization_record(self):
        # useful if we want to get a sense of all the measures involved and their quantization,
        # since some voices may only last for a few measures and cut off early
        if len(self.voice_quantization_records) is 0:
            return None
        return max(self.voice_quantization_records.values(),
                   key=lambda quantization_record: len(quantization_record.quantized_measures))

    @property
    def measure_lengths(self):
        """
        If this PerformancePart has been quantized, gets the lengths of all the measures

        :return: list of measure lengths
        """
        assert self.is_quantized(), "Performance must be quantized to have measure lengths!"
        # base it on the longest quantization record
        return self._get_longest_quantization_record().measure_lengths

    def num_measures(self):
        """
        If this PerformancePart has been quantized, gets the number of measures

        :return: number of measures
        """
        assert self.is_quantized(), "Performance must be quantized to have a number of measures"
        longest_quantization_record = self._get_longest_quantization_record()
        return 0 if longest_quantization_record is None else \
            len(self._get_longest_quantization_record().quantized_measures)

    def to_staff_group(self):
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

    def name_count(self):
        """
        When there are multiple instrument of the same name in an ensemble, keeps track of which one we mean

        :return: int representing which instrument we mean
        """
        return self._instrument_id[1]

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

    def _to_json(self):
        return {
            "name": self.name,
            "instrument_id": self._instrument_id,
            "voices": {
                voice_name: [n._to_json() for n in voice] for voice_name, voice in self.voices.items()
            },
            "voice_quantization_records": {
                voice_name: self.voice_quantization_records[voice_name]._to_json()
                for voice_name in self.voice_quantization_records
            } if self.voice_quantization_records is not None else None
        }

    @classmethod
    def _from_json(cls, json_dict):
        performance_part = cls(name=json_dict["name"])
        performance_part._instrument_id = json_dict["instrument_id"]
        for voice in json_dict["voices"]:
            for note in json_dict["voices"][voice]:
                performance_part.add_note(PerformanceNote._from_json(note), voice=voice)
        performance_part.voice_quantization_records = {
            voice_name: QuantizationRecord._from_json(json_dict["voice_quantization_records"][voice_name])
            for voice_name in json_dict["voice_quantization_records"]
        } if json_dict["voice_quantization_records"] is not None else None

        return performance_part


class Performance(SavesToJSON):

    def __init__(self, parts=None, tempo_envelope=None):
        """
        Representation of note playback events, usually a transcription of the notes played by an Ensemble.
        Operates in continuous time, without regard to any particular way of notating it. (As opposed to a Score,
        which represents the notated music.)

        :param parts: list of PerformanceParts to start with (defaults to empty list)
        :param tempo_envelope: a tempo_envelope to associate with this performance
        """
        self.parts = [] if parts is None else parts
        self.tempo_envelope = TempoEnvelope() if tempo_envelope is None else tempo_envelope
        assert isinstance(self.parts, list) and all(isinstance(x, PerformancePart) for x in self.parts)

    def new_part(self, instrument=None):
        """
        Construct and add a new PerformancePart to this Performance

        :param instrument: the instrument to use as a default for playing back the part
        :type instrument: ScampInstrument
        :return: the newly constructed part
        """
        new_part = PerformancePart(instrument)
        self.parts.append(new_part)
        return new_part

    def add_part(self, part: PerformancePart):
        """
        Add the given PerformancePart to this performance

        :param part: a PerformancePart to add
        :type part: PerformancePart
        """
        self.parts.append(part)

    def get_part_by_index(self, index):
        """
        Get the part with the given index
        (Parts are numbered starting with 0, in order that they are added/created.)

        :param index: the index of the part in question
        :return: the PerformancePart
        """
        return self.parts[index]

    def get_parts_by_name(self, name):
        """
        Get all parts with the given name

        :param name: the part name to search for
        :type name: str
        :return: a list of parts with this name
        """
        return [x for x in self.parts if x.name == name]

    def get_parts_by_instrument(self, instrument):
        """
        Get all parts with the given instrument

        :param instrument: the instrument to search for
        :type instrument: ScampInstrument
        :return: a list of parts with this instrument
        """
        return [x for x in self.parts if x.instrument == instrument]

    @property
    def end_time(self):
        """
        The end beat of this performance (i.e. the beat corresponding to the end of the last note)

        :return: float representing the beat at which all notes are done playing
        """
        return max(p.end_time for p in self.parts)

    def length(self):
        """
        Total length of this performance. (Identical to Performance.end_time)

        :return: float representing the total length of the Performance
        """
        return self.end_time

    def play(self, start_time=0, stop_time=None, ensemble="auto", clock="auto", blocking=True, tempo_envelope="auto"):
        """
        Play back this performance (or a selection of it)

        :param start_time: Place to start playing from
        :type start_time: float
        :param stop_time: Place to stop playing at
        :type stop_time: float
        :param ensemble: The Ensemble whose instruments to use for playback. If "auto", checks to see if we are
            operating in a particular Session, and uses those instruments if so.
        :type ensemble: Ensemble
        :param clock: clock to use for playback
        :type clock: Clock
        :param blocking: if True, don't return until the part is done playing; if False, return immediately
        :type blocking: bool
        :param tempo_envelope: the TempoEnvelope with which to play back this performance. The default value of "auto"
            uses  the tempo_envelope associated with the performance, and None uses a flat tempo of rate 60bpm

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

        if ensemble is not None:
            self.set_instruments_from_ensemble(ensemble, override=False)

        # if not given a valid clock, create one
        if not isinstance(clock, Clock):
            clock = Clock()

        if tempo_envelope == "auto":
            tempo_envelope = self.tempo_envelope

        if stop_time is None:
            stop_time = max(p.end_time for p in self.parts)

        for p in self.parts:
            p.play(start_time, stop_time, clock=clock, blocking=False, tempo_envelope=tempo_envelope)

        if blocking:
            clock.wait_for_children_to_finish()

        return clock

    def set_instruments_from_ensemble(self, ensemble, override=True):
        """
        Set the playback instruments for each part in this Performance by their best match in the ensemble given.
        If override is False, only set the instrument for parts that don't already have one set.

        :param ensemble: the Ensemble in which to search for instruments
        :type ensemble: Ensemble
        :param override: Whether or not to override any instruments already assigned to parts
        :type override: bool
        :return: self
        """
        for part in self.parts:
            if override or part.instrument is None:
                part.set_instrument_from_ensemble(ensemble)
        return self

    def quantize(self, quantization_scheme="default", onset_weighting="default", termination_weighting="default"):
        """
        Quantizes all parts according to the quantization_scheme

        :param quantization_scheme: the QuantizationScheme to use. If "default", uses the default time signature defined
            in the quantization_settings.
        :param onset_weighting: how much to weight note onsets in the quantization.
        :type onset_weighting: float
        :param termination_weighting: how much to weight note terminations in the quantization.
        :type termination_weighting: float
        :return: this Performance, having been quantized
        """
        if quantization_scheme == "default":
            logging.warning("No quantization scheme given; quantizing according to default time signature.")
            quantization_scheme = QuantizationScheme.from_time_signature(quantization_settings.default_time_signature)

        for part in self.parts:
            part.quantize(quantization_scheme, onset_weighting=onset_weighting,
                          termination_weighting=termination_weighting)
        return self

    def quantized(self, quantization_scheme="default", onset_weighting="default", termination_weighting="default"):
        """
        Same as quantize, except that it returns a new copy, rather than changing this Performance in place.

        :param quantization_scheme: the QuantizationScheme to use. If "default", uses the default time signature defined
            in the quantization_settings.
        :param onset_weighting: how much to weight note onsets in the quantization.
        :type onset_weighting: float
        :param termination_weighting: how much to weight note terminations in the quantization.
        :type termination_weighting: float
        :return: a quantized copy of this Performance
        """
        if quantization_scheme == "default":
            quantization_scheme = QuantizationScheme.from_time_signature(quantization_settings.default_time_signature)

        return Performance([part.quantized(quantization_scheme, onset_weighting=onset_weighting,
                                           termination_weighting=termination_weighting)
                            for part in self.parts], tempo_envelope=self.tempo_envelope)

    def is_quantized(self):
        """
        Checks if this Performance has been quantized

        :return: True if all parts are quantized, False if not
        """
        return all(part.is_quantized() for part in self.parts)

    def num_measures(self):
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

    def to_score(self, quantization_scheme: QuantizationScheme = None, time_signature=None, bar_line_locations=None,
                 max_divisor=None, max_divisor_indigestibility=None, simplicity_preference=None, title="default",
                 composer="default"):
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

    def _to_json(self):
        return {"parts": [part._to_json() for part in self.parts], "tempo_envelope": self.tempo_envelope._to_json()}

    @classmethod
    def _from_json(cls, json_dict):
        return cls([PerformancePart._from_json(part_json) for part_json in json_dict["parts"]],
                   TempoEnvelope.from_json(json_dict["tempo_envelope"]))

    def __repr__(self):
        return "Performance([\n{}\n])".format(
            textwrap.indent(",\n".join(str(x) for x in self.parts), "   ")
        )
