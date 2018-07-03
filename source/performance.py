import bisect
from playcorder.parameter_curve import ParameterCurve
from playcorder.quantization import quantize_performance_part, QuantizationRecord
from playcorder.clock import Clock, TempoCurve
import logging
from playcorder.utilities import SavesToJSON
from functools import total_ordering
from copy import deepcopy
import itertools
import textwrap


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
            return sum(x.average_level() if isinstance(x, ParameterCurve) else x for x in self.pitch) / len(self.pitch)
        else:
            return self.pitch.average_level() if isinstance(self.pitch, ParameterCurve) else self.pitch

    def play(self, instrument, clock=None, blocking=True):
        if isinstance(self.pitch, tuple):
            instrument.play_chord(self.pitch, self.volume, self.length, self.properties, clock=clock, blocking=blocking)
        else:
            instrument.play_note(self.pitch, self.volume, self.length, self.properties, clock=clock, blocking=blocking)

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

    def _to_json(self):
        if isinstance(self.pitch, tuple):
            # if this is a chord
            json_pitch = [p._to_json() if isinstance(p, ParameterCurve) else p for p in self.pitch]
            json_pitch.insert(0, "chord")  # indicates that it's a chord, since json can't distinguish tuples from lists
        elif isinstance(self.pitch, ParameterCurve):
            json_pitch = self.pitch._to_json()
        else:
            json_pitch = self.pitch

        return {
            "start_time": self.start_time,
            "length": self.length,
            "pitch": json_pitch,
            "volume": self.volume._to_json() if isinstance(self.volume, ParameterCurve) else self.volume,
            "properties": self.properties
        }

    @classmethod
    def _from_json(cls, json_object):
        # if pitch is an array starting with "chord"
        if hasattr(json_object["pitch"], "__len__") and json_object["pitch"][0] == "chord":
            pitches = []
            for pitch in json_object["pitch"][1:]:  # ignore the "chord" indicator
                pitches.append(ParameterCurve._from_json(pitch) if hasattr(pitch, "__len__") else pitch)
            json_object["pitch"] = tuple(pitches)
        # otherwise check if it's a ParameterCurve
        elif hasattr(json_object["pitch"], "__len__"):
            json_object["pitch"] = ParameterCurve._from_json(json_object["pitch"])

        if hasattr(json_object["volume"], "__len__"):
            json_object["volume"] = ParameterCurve._from_json(json_object["volume"])
        return PerformanceNote(**json_object)

    def __repr__(self):
        return "PerformanceNote(start_time={}, length={}, pitch={}, volume={}, properties={})".format(
            self.start_time, self.length, self.pitch, self.volume, self.properties
        )


class PerformancePart(SavesToJSON):

    def __init__(self, instrument=None, name=None, voices=None, instrument_id=None, voice_quantization_records=None):
        """
        Recording of the notes played by a PlaycorderInstrument. Can be saved to json and played back on a clock.
        :param instrument: the PlaycorderInstrument associated with this part; used for playback
        :param name: The name of this part
        :param voices: either a list of PerformanceNotes (which is interpreted as one unnamed voice), a list of lists
        of PerformanceNotes (which is interpreted as several numbered voices), or a dictionary mapping voice names
        to lists of notes.
        :param instrument_id: a json serializable record of the instrument used
        :param voice_quantization_records: a record of how this part was quantized if it has been quantized
        """
        self.instrument = instrument  # A PlaycorderInstrument instance
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
            # a dict of voices is given
            self.voices = voices
            # make sure that the dict contains the catch-all voice "_unspecified_"
            if "_unspecified_" not in self.voices:
                self.voices["_unspecified_"] = []
        else:
            # a single voice or list of voices is given
            assert hasattr(voices, "__len__")
            # check if we were given a list of voices
            if hasattr(voices[0], "__len__"):
                # if so, just assign them numbers 1, 2, 3, 4...
                self.voices = {(i+1): voice for i, voice in enumerate(voices)}
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
        return max(max(n.start_time + n.length for n in voice) for voice in self.voices.values())

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
             tempo_curve=None, selected_voices=None):
        instrument = self.instrument if instrument is None else instrument
        from playcorder.instruments import PlaycorderInstrument
        if not isinstance(instrument, PlaycorderInstrument):
            raise ValueError("PerformancePart does not have a valid instrument and cannot play.")
        clock = Clock(instrument.name + " clock", pool_size=20) if clock is None else clock
        if not isinstance(clock, Clock):
            raise ValueError("PerformancePart was given an invalid clock.")
        stop_time = self.end_time if stop_time is None else stop_time
        assert stop_time >= start_time
        if tempo_curve is not None:
            assert isinstance(tempo_curve, TempoCurve)

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
                    child_clock.wait(current_note.length)
                    return

        if blocking:
            # clock blocked ;-)
            if tempo_curve is not None:
                clock.apply_tempo_curve(tempo_curve)
            _play_thread(clock)
            return clock
        else:
            sub_clock = clock.fork(_play_thread)
            if tempo_curve is not None:
                sub_clock.apply_tempo_curve(tempo_curve)
            return sub_clock

    def set_instrument_from_ensemble(self, ensemble):
        self.instrument = ensemble.get_instrument_by_name(*self._instrument_id)
        if self.instrument is None:
            logging.warning("No matching instrument could be found for part {}.".format(self.name))
        return self

    def quantize(self, quantization_scheme, onset_weighting="default", termination_weighting="default"):
        """
        Quantizes this PerformancePart according to the quantization_scheme, returning the QuantizationRecord
        """
        quantize_performance_part(self, quantization_scheme, onset_weighting=onset_weighting,
                                  termination_weighting=termination_weighting)
        return self.voice_quantization_records

    def quantized(self, quantization_scheme, onset_weighting="default", termination_weighting="default"):
        """
        Returns a quantized copy of this PerformancePart, leaving the original unchanged
        """
        copy = PerformancePart(instrument=self.instrument, name=self.name, voices=deepcopy(self.voices),
                               instrument_id=self._instrument_id)
        quantize_performance_part(copy, quantization_scheme, onset_weighting=onset_weighting,
                                  termination_weighting=termination_weighting)
        return copy

    def is_quantized(self):
        return self.voice_quantization_records is not None

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

    def __init__(self, parts=None, tempo_curve=None):
        self.parts = [] if parts is None else parts
        self.tempo_curve = TempoCurve() if tempo_curve is None else tempo_curve
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

    @property
    def end_time(self):
        return max(p.end_time for p in self.parts)

    def length(self):
        return self.end_time

    def play(self, start_time=0, stop_time=None, ensemble=None, clock=None, blocking=True, use_tempo_curve=True):
        if ensemble is not None:
            self.set_instruments_from_ensemble(ensemble)

        # if not given a valid clock, create one
        if not isinstance(clock, Clock):
            clock = Clock()

        tempo_curve = self.tempo_curve if use_tempo_curve else None

        if stop_time is None:
            stop_time = max(p.end_time for p in self.parts)

        for p in self.parts:
            p.play(start_time, stop_time, clock=clock, blocking=False, tempo_curve=tempo_curve)

        if blocking:
            clock.wait_for_children_to_finish()

        return clock

    def set_instruments_from_ensemble(self, ensemble):
        for part in self.parts:
            part.set_instrument_from_ensemble(ensemble)
        return self

    def quantize(self, quantization_scheme, onset_weighting="default", termination_weighting="default"):
        """
        Quantizes all parts according to the given quantization_scheme
        """
        for part in self.parts:
            part.quantize(quantization_scheme, onset_weighting=onset_weighting,
                          termination_weighting=termination_weighting)

    def quantized(self, quantization_scheme, onset_weighting="default", termination_weighting="default"):
        """
        Returns a quantized copy of this Performance, leaving the original unchanged
        """
        return Performance([part.quantized(quantization_scheme, onset_weighting=onset_weighting,
                                           termination_weighting=termination_weighting)
                            for part in self.parts], tempo_curve=self.tempo_curve)

    @property
    def is_quantized(self):
        return all(part.is_quantized for part in self.parts)

    def _to_json(self):
        return {"parts": [part._to_json() for part in self.parts], "tempo_curve": self.tempo_curve._to_json()}

    @classmethod
    def _from_json(cls, json_dict):
        return cls([PerformancePart._from_json(part_json) for part_json in json_dict["parts"]],
                   TempoCurve.from_list(json_dict["tempo_curve"]))

    def __repr__(self):
        return "Performance([\n{}\n])".format(
            textwrap.indent(",\n".join(str(x) for x in self.parts), "   ")
        )
