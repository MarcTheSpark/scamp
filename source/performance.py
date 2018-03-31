from sortedcontainers import SortedList
from collections import namedtuple

PerformanceNote = namedtuple("PerformanceNote", "start_time length pitch volume properties")


class PerformancePart:

    def __init__(self, instrument=None, name=None, notes=None, instrument_id=None):
        self.instrument = instrument  # A PlaycorderInstrument instance
        # the name of the part can be specified directly, or if not derives from the instrument it's attached to
        # if the part is not attached to an instrument, it starts with a name of None
        self.name = name if name is not None else instrument.name if instrument is not None else None
        # this is used for serializing to and restoring from a json file. It should be enough to find
        # the instrument in the ensemble, so long as the ensemble is compatible.
        self._instrument_id = instrument_id if instrument_id is not None else \
                                  instrument.name, instrument.name_count if instrument is not None else None

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

    def __repr__(self):
        return "PerformancePart(name=\"{}\", instrument_id={}, notes=[\n{}\n])".format(
            self.name, self._instrument_id, "   " + ", \n   ".join(str(x) for x in self.notes)
        )

    def to_json(self):
        return {"name": self.name, "instrument_id": self._instrument_id, "notes": self.notes}

    @classmethod
    def from_json_friendly(cls, json_dict,  ensemble):
        performance_part = cls(name=json_dict["name"])
        performance_part._instrument_id = json_dict["instrument_id"]


class Performance:

    def __init__(self, parts=None):
        self.parts = [] if parts is None else parts
        assert isinstance(self.parts, list) and all(isinstance(x, PerformancePart) for x in self.parts)

    def new_part(self, instrument=None):
        new_part = PerformancePart(instrument)
        self.parts.append(new_part)
        return new_part

    def add_part(self, part: PerformancePart):
        self.parts.append(part)

    def __repr__(self):
        return "Performance([\n{}\n])".format("   " + ",\n   ".join(
            "\n   ".join(str(x).split('\n')) for x in self.parts
        ))