from playcorder.performance import PerformancePart, PerformanceNote
from playcorder.quantization import QuantizationRecord
from copy import deepcopy


def quantized_performance_part_to_score_part(quantized_performance_part: PerformancePart):
    assert quantized_performance_part.is_quantized
    notes = deepcopy(quantized_performance_part.notes)
    # probably shouldn't be necessary to sort, but we'll do it anyway
    notes.sort(key=lambda note: note.start_time)
    print("Notes:")
    print(notes)
    print("--------")
    _collapse_chords(notes)
    separated_voices = _separate_into_non_overlapping_voices(notes)
    print("Separated voices:")
    print(separated_voices)
    print("--------")
    measures = _separate_voices_into_measures(separated_voices, quantized_performance_part.quantization_record)


def _collapse_chords(notes):
    """
    Modifies a list of PerformanceNotes in place so that simultaneous notes become chords
    (i.e. they become PerformanceNotes with a tuple of different values for the pitch.)
    :param notes: a list of PerformanceNotes
    """
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


def _separate_into_non_overlapping_voices(notes):
    """
    Takes a list of PerformanceNotes and breaks it up into separate voices that don't overlap more than max_overlap
    :param notes: a list of PerformanceNotes
    :return: a list of voices, each of which is a non-overlapping list of PerformanceNotes
    """
    voices = []
    # for each note, find the first non-conflicting voice and add it to that
    # or create a new voice to add it to if none of the existing voices work
    for note in notes:
        voice_to_add_to = None
        for voice in voices:
            # check each voice to see if its last note ends before the note we want to add
            if voice[-1].end_time <= note.start_time:
                voice_to_add_to = voice
                break
        if voice_to_add_to is None:
            voice_to_add_to = []
            voices.append(voice_to_add_to)
        voice_to_add_to.append(note)

    return voices


def _separate_voices_into_measures(separated_voices, quantization: QuantizationRecord):
    """
    Separates a list of non-overlapping voices into a list of measure bins containing parts of those voices
    :param separated_voices: a list of voices, each of which is a non-overlapping list of PerformanceNotes
    :param quantization: a QuantizationRecord, which has information about beats and measures
    :return: a list of measure bins, each of which is a list of voices for that measure, each of which
    is a list of PerformanceNotes
    """
    all_measure_voices = []

    # look within the start and end beat of each measure
    measure_start = 0
    for quantized_measure in quantization.quantized_measures:
        measure_end = measure_start + quantized_measure.measure_length

        # construct a list of voices for this measure
        this_measure_voices = []

        # for each voice (currently spanning the length of the whole part)
        for voice in separated_voices:
            # we wish to isolate just the notes of that voice that would fit in this measure
            measure_voice = []
            # for each note in the voice that starts in this measure
            while len(voice) > 0 and voice[0].start_time < measure_end:
                # if the end time of the note is after the end of the measure, we need to split it
                if voice[0].end_time > measure_end:
                    first_part, second_part = _split_performance_note_at_beat(voice[0], measure_end)
                    measure_voice.append(first_part)
                    voice[0] = second_part
                else:
                    measure_voice.append(voice.pop(0))
            if len(measure_voice) > 0:
                this_measure_voices.append(measure_voice)

        all_measure_voices.append(this_measure_voices)
        measure_start = measure_end

    print(quantization)
    for measure_voices in all_measure_voices:
        print(measure_voices)
        print("-----")

    return all_measure_voices


def _split_performance_note_at_beat(performance_note: PerformanceNote, split_beat):
    if performance_note.start_time < split_beat < performance_note.end_time:
        second_part = deepcopy(performance_note)
        second_part.start_time = split_beat
        second_part.end_time = performance_note.end_time
        performance_note.end_time = split_beat
        # assign the '_tie_position' property of the parts based on the tie position of the original note
        if "_tie_position" not in performance_note.properties:
            performance_note.properties["_tie_position"] = "start"
            second_part.properties["_tie_position"] = "end"
        elif performance_note.properties["_tie_position"] == "start":
            second_part.properties["_tie_position"] = "middle"
        elif performance_note.properties["_tie_position"] == "middle":
            second_part.properties["_tie_position"] = "middle"
        elif performance_note.properties["_tie_position"] == "end":
            performance_note.properties["_tie_position"] = "middle"
            second_part.properties["_tie_position"] = "end"

        return performance_note, second_part
    else:
        # since the expectation is a tuple as return value, in the event that the split does
        # nothing we return the note unaltered in a length-1 tuple
        return performance_note,


class Measure:

    def __init__(self, voices, quantization_record):
        self.voices = voices
        self.quantization_record = quantization_record

    def get_XML(self):
        pass


class Voice:

    def __init__(self, notes):
        # Hmm... what is this???
        self.notes = notes

    def get_XML(self):
        pass
