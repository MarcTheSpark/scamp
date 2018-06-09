from playcorder.performance import PerformancePart
from copy import deepcopy


def quantized_performance_part_to_score_part(quantized_performance_part: PerformancePart):
    assert quantized_performance_part.is_quantized
    notes = deepcopy(quantized_performance_part.notes)
    _collapse_chords(notes)
    print(notes)


def _collapse_chords(notes):
    """
    Modifies a list of PerformanceNotes in place so that simultaneous notes become chords (i.e. they become
    PerformanceNotes with a tuple of different values for the pitch.
    :param notes:
    :return:
    """
    notes.sort(key=lambda note: note.start_time)
    i = 1
    while i < len(notes):
        # if same as the previous not in all but pitch
        if notes[i].start_time == notes[i - 1].start_time and notes[i].length == notes[i - 1].length \
                and notes[i].volume == notes[i - 1].volume and notes[i].properties == notes[i - 1].properties:
            # if it's already a chord (represented by a tuple in pitch)
            if isinstance(notes[i].pitch, tuple):
                notes[i-1].pitch += (notes[i].pitch,)
            else:
                notes[i-1].pitch = (notes[i-1].pitch, notes[i].pitch)
            # remove the current note, since it has been merged into the previous. No need to increment i.
            notes.pop(i)
        else:
            i += 1
