from sortedcontainers import SortedList
from collections import namedtuple
from playcorder.parameter_curve import ParameterCurve
from playcorder.clock import Clock, TempoCurve
import logging
from playcorder.utilities import SavesToJSON

PerformanceNote = namedtuple("PerformanceNote", "start_time length pitch volume properties")


class PerformancePart(SavesToJSON):

    def __init__(self, instrument=None, name=None, notes=None, instrument_id=None):
        self.instrument = instrument  # A PlaycorderInstrument instance
        # the name of the part can be specified directly, or if not derives from the instrument it's attached to
        # if the part is not attached to an instrument, it starts with a name of None
        self.name = name if name is not None else instrument.name if instrument is not None else None
        # this is used for serializing to and restoring from a json file. It should be enough to find
        # the instrument in the ensemble, so long as the ensemble is compatible.
        self._instrument_id = instrument_id if instrument_id is not None else \
            ((instrument.name, instrument.name_count) if instrument is not None else None)

        # since the start_time is the first element of the named tuple,
        # notes is sorted by start_time by default, which is what we want
        if notes is not None:
            assert hasattr(notes, "__len__") and all(isinstance(x, PerformanceNote) for x in notes)
            self.notes = SortedList(notes)
        else:
            self.notes = SortedList()

    def add_note(self, note: PerformanceNote):
        self.notes.add(note)

    def new_note(self, start_time, length, pitch, volume, properties):
        self.add_note(PerformanceNote(start_time, length, pitch, volume, properties))

    def set_instrument(self, instrument):
        self.instrument = instrument
        self._instrument_id = instrument.name, instrument.name_count

    @property
    def end_time(self):
        if len(self.notes) == 0:
            return 0
        return max(n.start_time + n.length for n in self.notes)

    def get_note_iterator(self, start_time, stop_time):
        def iterator():
            note_index = self.notes.bisect_left((start_time,))
            while note_index < len(self.notes) and self.notes[note_index].start_time < stop_time:
                yield self.notes[note_index]
                note_index += 1

        return iterator()

    def play(self, start_time=0, stop_time=None, instrument=None, clock=None, blocking=False, tempo_curve=None):
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
            note_iterator = self.get_note_iterator(start_time, stop_time)
            self.get_note_iterator(start_time, stop_time)
            try:
                current_note = next(note_iterator)
            except StopIteration:
                return

            child_clock.wait(current_note.start_time - start_time)

            while True:
                instrument.play_note(current_note.pitch, current_note.volume,
                                     current_note.length, current_note.properties, clock=child_clock)
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

    def __repr__(self):
        return "PerformancePart(name=\"{}\", instrument_id={}, notes=[\n{}\n])".format(
            self.name, self._instrument_id, "   " + ", \n   ".join(str(x) for x in self.notes)
        )

    def _to_json(self):
        return {"name": self.name, "instrument_id": self._instrument_id, "notes": [
            {
                "start_time": n.start_time,
                "length": n.length,
                "pitch": n.pitch._to_json() if hasattr(n.pitch, "_to_json") else n.pitch,
                "volume": n.volume._to_json() if hasattr(n.volume, "_to_json") else n.volume,
                "properties": n.properties
            } for n in self.notes
        ]}

    @classmethod
    def _from_json(cls, json_dict):
        performance_part = cls(name=json_dict["name"])
        performance_part._instrument_id = json_dict["instrument_id"]
        for note in json_dict["notes"]:
            if hasattr(note["pitch"], "__len__"):
                note["pitch"] = ParameterCurve._from_json(note["pitch"])
            if hasattr(note["volume"], "__len__"):
                note["volume"] = ParameterCurve._from_json(note["volume"])
            performance_part.add_note(PerformanceNote(**note))
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

    def play(self, start_time=0, stop_time=None, ensemble=None, clock=None, blocking=False, use_tempo_curve=True):
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

    def _to_json(self):
        return {"parts": [part._to_json() for part in self.parts], "tempo_curve": self.tempo_curve._to_json()}

    @classmethod
    def _from_json(cls, json_dict):
        return cls([PerformancePart._from_json(part_json) for part_json in json_dict["parts"]],
                   TempoCurve.from_list(json_dict["tempo_curve"]))

    def __repr__(self):
        return "Performance([\n{}\n])".format("   " + ",\n   ".join(
            "\n   ".join(str(x).split('\n')) for x in self.parts
        ))
