from sortedcontainers import SortedListWithKey

from collections import namedtuple


PerformanceNote = namedtuple("PerformanceNote", "start_time length pitch volume properties")


class PerformanceScore:

    def __init__(self):
        self._parts = []
        self._parts_to_instruments = {}

    def new_part(self, name: str, instrument=None):
        self._parts.append(PerformancePart(name))
        if instrument is not None:
            self.set_part_instrument(instrument, instrument)
            
    def append_part(self, part: PerformancePart, instrument=None):
        self._parts.append(part)
        if instrument is not None:
            self.set_part_instrument(instrument, instrument)

    def set_part_instrument(self, part, instrument):
        self._parts_to_instruments[part] = instrument

    def parts(self):
        return iter(self._parts)
    
    def part(self, index: int):
        return self._parts[index]
    
    def instrument_of_part(self, part):
        return self._parts_to_instruments[part]


class PerformancePart:

    def __init__(self, name):
        # contains reference to  instruments
        self.notes = SortedListWithKey(key=lambda note: note.start_time)
        self.name = name

    def add_note(self, note: PerformanceNote):
        self.notes.add(note)


