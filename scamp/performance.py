import bisect
from .quantization import quantize_performance_part, QuantizationRecord, QuantizationScheme
from .settings import quantization_settings
from clockblocks import Clock, TempoEnvelope
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
        Recording of the notes played by a ScampInstrument. Can be saved to json and played back on a clock.
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
        self.add_note(PerformanceNote(start_time, length, pitch, volume, properties))

    def set_instrument(self, instrument):
        self.instrument = instrument
        self._instrument_id = instrument.name, instrument.name_count

    @property
    def end_time(self):
        if len(self.voices) == 0:
            return 0
        return max(max(n.start_time + n.length_sum() for n in voice) if len(voice) > 0 else 0
                   for voice in self.voices.values())

    def get_note_iterator(self, start_time=0, stop_time=None, selected_voices=None):
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
        instrument = self.instrument if instrument is None else instrument
        from scamp.instruments import ScampInstrument
        if not isinstance(instrument, ScampInstrument):
            raise ValueError("PerformancePart does not have a valid instrument and cannot play.")
        clock = Clock(instrument.name + " clock", pool_size=20) if clock is None else clock
        if not isinstance(clock, Clock):
            raise ValueError("PerformancePart was given an invalid clock.")
        stop_time = self.end_time if stop_time is None else stop_time
        assert stop_time >= start_time
        if tempo_envelope is not None:
            assert isinstance(tempo_envelope, TempoEnvelope)

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
        self.instrument = ensemble.get_instrument_by_name(*self._instrument_id)
        if self.instrument is None:
            logging.warning("No matching instrument could be found for part {}.".format(self.name))
        return self

    def quantize(self, quantization_scheme="default", onset_weighting="default", termination_weighting="default"):
        """
        Quantizes this PerformancePart according to the quantization_scheme, returning the QuantizationRecord
        """
        if quantization_scheme == "default":
            logging.warning("No quantization scheme given; quantizing according to default time signature.")
            quantization_scheme = QuantizationScheme.from_time_signature(quantization_settings.default_time_signature)

        quantize_performance_part(self, quantization_scheme, onset_weighting=onset_weighting,
                                  termination_weighting=termination_weighting)
        return self

    def quantized(self, quantization_scheme="default", onset_weighting="default", termination_weighting="default"):
        """
        Returns a quantized copy of this PerformancePart, leaving the original unchanged
        """
        if quantization_scheme == "default":
            logging.warning("No quantization scheme given; quantizing according to default time signature.")
            quantization_scheme = QuantizationScheme.from_time_signature(quantization_settings.default_time_signature)

        copy = PerformancePart(instrument=self.instrument, name=self.name, voices=deepcopy(self.voices),
                               instrument_id=self._instrument_id)
        quantize_performance_part(copy, quantization_scheme, onset_weighting=onset_weighting,
                                  termination_weighting=termination_weighting)
        return copy

    def is_quantized(self):
        return self.voice_quantization_records is not None

    def get_longest_quantization_record(self):
        # useful if we want to get a sense of all the measures involved and their quantization,
        # since some voices may only last for a few measures and cut off early
        if len(self.voice_quantization_records) is 0:
            return None
        return max(self.voice_quantization_records.values(),
                   key=lambda quantization_record: len(quantization_record.quantized_measures))

    @property
    def measure_lengths(self):
        assert self.is_quantized(), "Performance must be quantized to have measure lengths!"
        # base it on the longest quantization record
        return self.get_longest_quantization_record().measure_lengths

    def num_measures(self):
        assert self.is_quantized(), "Performance must be quantized to have a number of measures"
        longest_quantization_record = self.get_longest_quantization_record()
        return 0 if longest_quantization_record is None else \
            len(self.get_longest_quantization_record().quantized_measures)

    def to_staff_group(self):
        if not self.is_quantized():
            logging.warning("PerformancePart was not quantized before calling to_staff_group(); "
                            "quantizing according to default quantization time_signature")
            quantization_scheme = QuantizationScheme.from_time_signature(quantization_settings.default_time_signature)
            return self.quantized(quantization_scheme).to_staff_group()
        return StaffGroup.from_quantized_performance_part(self)

    def name_count(self):
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

    def to_json(self):
        return {
            "name": self.name,
            "instrument_id": self._instrument_id,
            "voices": {
                voice_name: [n.to_json() for n in voice] for voice_name, voice in self.voices.items()
            },
            "voice_quantization_records": {
                voice_name: self.voice_quantization_records[voice_name].to_json()
                for voice_name in self.voice_quantization_records
            } if self.voice_quantization_records is not None else None
        }

    @classmethod
    def from_json(cls, json_dict):
        performance_part = cls(name=json_dict["name"])
        performance_part._instrument_id = json_dict["instrument_id"]
        for voice in json_dict["voices"]:
            for note in json_dict["voices"][voice]:
                performance_part.add_note(PerformanceNote.from_json(note), voice=voice)
        performance_part.voice_quantization_records = {
            voice_name: QuantizationRecord.from_json(json_dict["voice_quantization_records"][voice_name])
            for voice_name in json_dict["voice_quantization_records"]
        } if json_dict["voice_quantization_records"] is not None else None

        return performance_part


class Performance(SavesToJSON):

    def __init__(self, parts=None, tempo_envelope=None):
        self.parts = [] if parts is None else parts
        self.tempo_envelope = TempoEnvelope() if tempo_envelope is None else tempo_envelope
        assert isinstance(self.parts, list) and all(isinstance(x, PerformancePart) for x in self.parts)

    def new_part(self, instrument=None):
        new_part = PerformancePart(instrument)
        self.parts.append(new_part)
        return new_part

    def add_part(self, part: PerformancePart):
        self.parts.append(part)

    def get_part_by_index(self, index):
        return self.parts[index]

    def get_parts_by_name(self, name):
        return [x for x in self.parts if x.name == name]

    def get_parts_by_instrument(self, instrument):
        return [x for x in self.parts if x.instrument == instrument]

    @property
    def end_time(self):
        return max(p.end_time for p in self.parts)

    def length(self):
        return self.end_time

    def play(self, start_time=0, stop_time=None, ensemble=None, clock=None, blocking=True, use_tempo_envelope=True):
        if ensemble is not None:
            self.set_instruments_from_ensemble(ensemble)

        # if not given a valid clock, create one
        if not isinstance(clock, Clock):
            clock = Clock()

        tempo_envelope = self.tempo_envelope if use_tempo_envelope else None

        if stop_time is None:
            stop_time = max(p.end_time for p in self.parts)

        for p in self.parts:
            p.play(start_time, stop_time, clock=clock, blocking=False, tempo_envelope=tempo_envelope)

        if blocking:
            clock.wait_for_children_to_finish()

        return clock

    def set_instruments_from_ensemble(self, ensemble):
        for part in self.parts:
            part.set_instrument_from_ensemble(ensemble)
        return self

    def quantize(self, quantization_scheme="default", onset_weighting="default", termination_weighting="default"):
        """
        Quantizes all parts according to the given quantization_scheme.
        By default uses the default quantization time signature and settings as defined in QuantizationSettings
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
        Returns a quantized copy of this Performance, leaving the original unchanged
        """
        if quantization_scheme == "default":
            logging.warning("No quantization scheme given; quantizing according to default time signature.")
            quantization_scheme = QuantizationScheme.from_time_signature(quantization_settings.default_time_signature)

        return Performance([part.quantized(quantization_scheme, onset_weighting=onset_weighting,
                                           termination_weighting=termination_weighting)
                            for part in self.parts], tempo_envelope=self.tempo_envelope)

    def is_quantized(self):
        return all(part.is_quantized() for part in self.parts)

    def num_measures(self):
        return max(part.num_measures() for part in self.parts)

    def to_score(self, quantization_scheme=None, title="default", composer="default"):
        return Score.from_performance(self, quantization_scheme, title=title, composer=composer)

    def to_json(self):
        return {"parts": [part.to_json() for part in self.parts], "tempo_envelope": self.tempo_envelope.to_json()}

    @classmethod
    def from_json(cls, json_dict):
        return cls([PerformancePart.from_json(part_json) for part_json in json_dict["parts"]],
                   TempoEnvelope.from_json(json_dict["tempo_envelope"]))

    def __repr__(self):
        return "Performance([\n{}\n])".format(
            textwrap.indent(",\n".join(str(x) for x in self.parts), "   ")
        )
