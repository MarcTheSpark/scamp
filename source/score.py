from playcorder.performance import PerformancePart, PerformanceNote
from playcorder.quantization import QuantizationRecord
from copy import deepcopy


# TODO: SEPARATE VOICES DURING QUANTIZATION OF PERFORMANCE
# TODO: ALLOW "VOICE HINT" TO BE GIVEN TO NOTES TO KEEP THEM IN THE DESIRED VOICE?

def quantized_performance_part_to_score_part(quantized_performance_part: PerformancePart):
    assert quantized_performance_part.is_quantized
    quantization_record = quantized_performance_part.quantization_record

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
    measures_voices = _separate_voices_into_measures(separated_voices, quantization_record)
    measures = [Measure(voices, measure_quantization_record)
                for voices, measure_quantization_record in zip(measures_voices, quantization_record.quantized_measures)]


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
        # if this isn't a rest, then we're going to need to keep track of ties that will be needed
        if performance_note.pitch is not None:
            # assign the '_tie' property of the parts based on the tie property of the note being split
            if "_tie" not in performance_note.properties:
                performance_note.properties["_tie"] = "start"
                second_part.properties["_tie"] = "end"
            elif performance_note.properties["_tie"] == "start":
                second_part.properties["_tie"] = "middle"
            elif performance_note.properties["_tie"] == "middle":
                second_part.properties["_tie"] = "middle"
            elif performance_note.properties["_tie"] == "end":
                performance_note.properties["_tie"] = "middle"
                second_part.properties["_tie"] = "end"

        return performance_note, second_part
    else:
        # since the expectation is a tuple as return value, in the event that the split does
        # nothing we return the note unaltered in a length-1 tuple
        return performance_note,


class Measure:

    def __init__(self, voices, measure_quantization_record):
        self.voices = [Voice(v, measure_quantization_record) for v in voices]
        self.quantization_record = measure_quantization_record
        # Add rests

    def get_XML(self):
        pass


class Voice:

    def __init__(self, notes, measure_quantization):
        self.notes = notes
        self.measure_quantization = measure_quantization
        print("HOO!!!!")
        for note in self.notes:
            note.start_time -= measure_quantization.start_time
        self._fill_in_rests()
        self._split_at_beats()
        print("[\n   " + "\n   ".join(str(x) for x in self.notes) + "\n]")
        print("Haaa")
        # Hmm... what is this???

    def _fill_in_rests(self):
        notes_and_rests = []
        t = 0
        for note in self.notes:
            if t < note.start_time:
                notes_and_rests.append(PerformanceNote(t, note.start_time - t, None, None, {}))
            notes_and_rests.append(note)
            t = note.end_time

        if t < self.measure_quantization.measure_length:
            notes_and_rests.append(PerformanceNote(t, self.measure_quantization.measure_length - t, None, None, {}))
        self.notes = notes_and_rests

    def _split_at_beats(self):
        measure_start_time = self.measure_quantization.start_time
        for beat in self.measure_quantization.beats:
            split_notes = []
            for note in self.notes:
                split_notes.extend(_split_performance_note_at_beat(note, beat.start_time - measure_start_time))
            self.notes = split_notes

    def get_XML(self):
        pass


class Tuplet:
    pass


class NoteLike:
    # represents a note, a chord, or a rest
    pass