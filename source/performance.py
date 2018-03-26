from sortedcontainers import SortedList
from collections import namedtuple

PerformanceNote = namedtuple("PerformanceNote", "start_time length pitch volume properties")


class PerformancePart:

    def __init__(self, name, instrument=None):
        # since the start_time is the first element of the named tuple,
        # notes is sorted by start_time by default, which is what we want
        self.notes = SortedList()
        self.name = name
        self.instrument = instrument

    def add_note(self, note: PerformanceNote):
        self.notes.add(note)

    def new_note(self, start_time, length, pitch, volume, properties):
        self.add_note(PerformanceNote(start_time, length, pitch, volume, properties))

    def set_instrument(self, instrument):
        self.instrument = instrument

    def __repr__(self):
        return "PerformancePart({}, {})".format(self.name, self.instrument)


class Performance:

    def __init__(self, parts=None):
        self.parts = [] if parts is None else parts
        assert isinstance(self.parts, list) and all(isinstance(x, PerformancePart) for x in self.parts)

    def new_part(self, name: str, instrument=None):
        new_part = PerformancePart(name, instrument)
        self.parts.append(new_part)
        return new_part

    def add_part(self, part: PerformancePart):
        self.parts.append(part)

    def __repr__(self):
        return "Performance({})".format(self.parts)