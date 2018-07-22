from playcorder.performance import PerformancePart, PerformanceNote
from playcorder.settings import engraving_settings
from playcorder.parameter_curve import ParameterCurve
from copy import deepcopy
import math
from fractions import Fraction
from itertools import permutations, accumulate
from playcorder.utilities import get_standard_indispensability_array, prime_factor, floor_x_to_pow_of_y

# TODO: NoteLike needs a static method to take a PerformanceNote and a desired split of the lengths and produce
# a list of tied NoteLikes. They'll also need to split up any pitch ParameterCurves into their chunks.
# For now, we'll do this as gracenotes, but maybe there can be a setting that first splits a note into constituents
# based on the key points of the param curve and then splits those constituents into reproducible notes?

# TODO: fix old code in_process_and_convert_beat

# ---------------------------------------------- Duration Utilities --------------------------------------------

length_to_note_type = {
    8.0: "breve",
    4.0: "whole",
    2.0: "half",
    1.0: "quarter",
    0.5: "eighth",
    0.25: "16th",
    1.0/8: "32nd",
    1.0/16: "64th",
    1.0/32: "128th"
}


def get_basic_length_and_num_dots(length):
    length = Fraction(length).limit_denominator()
    if length in length_to_note_type:
        return length, 0
    else:
        dots_multiplier = 1.5
        dots = 1
        while length / dots_multiplier not in length_to_note_type:
            dots += 1
            dots_multiplier = (2.0 ** (dots + 1) - 1) / 2.0 ** dots
            if dots > engraving_settings.max_dots_allowed:
                raise ValueError("Duration length of {} does not resolve to single note type.".format(length))
        return length / dots_multiplier, dots


def is_single_note_length(length):
    try:
        get_basic_length_and_num_dots(length)
        return True
    except ValueError:
        return False


def length_to_undotted_constituents(length):
    # fix any floating point inaccuracies
    length = Fraction(length).limit_denominator()
    length_parts = []
    while length > 0:
        this_part = floor_x_to_pow_of_y(length, 2.0)
        length -= this_part
        length_parts.append(this_part)
    return length_parts


def _get_beat_division_indispensabilities(beat_length, beat_divisor):
    # In general, it's best to divide a beat into the smaller prime factors first. For instance, a 6 tuple is probably
    # easiest as two groups of 3 rather than 3 groups of 2. (This is definitely debatable and context dependent.)
    # An special case occurs when the beat naturally wants to divide a certain way. For instance, a beat of length 1.5
    # divided into 6 will prefer to divide into 3s first and then 2s.

    # first, get the divisor prime factors from to small
    divisor_factors = sorted(prime_factor(beat_divisor))

    # then get the natural divisors of the beat length from big to small
    natural_factors = sorted(prime_factor(Fraction(beat_length).limit_denominator().numerator), reverse=True)

    # now for each natural factor
    for natural_factor in natural_factors:
        # if it's a factor of the divisor
        if natural_factor in divisor_factors:
            # then pop it and move it to the front
            divisor_factors.pop(divisor_factors.index(natural_factor))
            divisor_factors.insert(0, natural_factor)
            # (Note that we sorted the natural factors from big to small so that the small ones get
            # pushed to the front last and end up at the very beginning of the queue)

    return get_standard_indispensability_array(divisor_factors, normalize=True)


# ---------------------------------------- Performance Part Conversion -----------------------------------------


def quantized_performance_part_to_staff_group(quantized_performance_part: PerformancePart):
    assert quantized_performance_part.is_quantized()
    # gets us to list of measures, each of which is a dictionary from voice name to tuple of (notes list, quantization)
    measures_voice_dictionaries = _separate_voices_into_measures(quantized_performance_part)
    # gets us to list of measures, each of which is a list of ordered voices in the form (notes list, quantization)
    measures_of_voices = [_voice_dictionary_to_list(x) for x in measures_voice_dictionaries]
    # if a measure is empty, we need to give it a signifier of an empty voice of a particular length
    # similarly if a voice is empty, we need to give it a signifier of the length of the rest

    StaffGroup.from_measure_bins_of_voice_lists(measures_of_voices, quantized_performance_part.measure_lengths)


def _separate_voices_into_measures(quantized_performance_part: PerformancePart):
    """
    Separates the voices of a performance part into a list of measure bins containing chunks of those voices
    :param quantized_performance_part: a PerformancePart that has been quantized
    :return: a list of measure bins, each of which is a dictionary from voice names to tuples of
    (notes in that measure for that voice, QuantizedMeasure for that measure for that voice)
    """
    # each entry is a dictionary of the form {voice name: voice notes in this measure}
    measure_bins = []

    # look within the start and end beat of each measure
    for voice_name in quantized_performance_part.voices:
        measure_start = 0
        voice = deepcopy(quantized_performance_part.voices[voice_name])
        voice_quantization_record = quantized_performance_part.voice_quantization_records[voice_name]
        for measure_num, quantized_measure in enumerate(voice_quantization_record.quantized_measures):
            measure_end = measure_start + quantized_measure.measure_length

            # make sure we have a bin for this measure
            while measure_num >= len(measure_bins):
                measure_bins.append({})
            this_measure_bin = measure_bins[measure_num]

            # we wish to isolate just the notes of this voice that would fit in this measure
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
                this_measure_bin[voice_name] = measure_voice, quantized_measure

            measure_start = measure_end

    return measure_bins


def _voice_dictionary_to_list(voice_dictionary):
    """
    Takes a dictionary from voice name to (voice notes, voice quantization) tuples and returns a list of ordered voices.
    Voices with numbers as names are assigned that voice number. Others are sorted by average pitch.
    :rtype: list of voices, each of which is a tuple of (list of PerformanceNotes, quantization)
    """
    # start out by making a list of all of the named (not numbered) voices
    voice_list = [voice_dictionary[voice_name] for voice_name in voice_dictionary if not voice_name.isdigit()]
    # sort them by their average pitch. (Call average_pitch on each note, since it might be a gliss or chord)
    # note that voice[0] is the first part of the (list of PerformanceNotes, quantization) tuple, so the notes
    voice_list.sort(key=lambda voice: sum(n.average_pitch() for n in voice[0])/len(voice[0]))

    # now we insert all the numbered voices in the correct spot in the list
    numbered_voice_names = [x for x in voice_dictionary.keys() if x.isdigit()]
    numbered_voice_names.sort(key=lambda name: int(name))
    for numbered_voice_name in numbered_voice_names:
        voice_number = int(numbered_voice_name)
        if (voice_number - 1) < len(voice_list):
            voice_list.insert(voice_number, voice_dictionary[numbered_voice_name])
        else:
            # insert dummy voices if necessary
            voice_list.extend([None] * (voice_number - 1 - len(voice_list)))
            voice_list.append(voice_dictionary[numbered_voice_name])
    return voice_list


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

            if isinstance(performance_note.pitch, ParameterCurve):
                # if the pitch is a parameter curve, then we split it appropriately
                pitch_curve_start, pitch_curve_end = performance_note.pitch.split_at(performance_note.length)
                performance_note.pitch = pitch_curve_start
                second_part.pitch = pitch_curve_end
            elif isinstance(performance_note.pitch, tuple) and isinstance(performance_note.pitch[0], ParameterCurve):
                # if the pitch is a tuple of parameter curve (glissing chord) then same idea
                first_part_chord = []
                second_part_chord = []
                for pitch_curve in performance_note.pitch:
                    assert isinstance(pitch_curve, ParameterCurve)
                    pitch_curve_start, pitch_curve_end = pitch_curve.split_at(performance_note.length)
                    first_part_chord.append(pitch_curve_start)
                    second_part_chord.append(pitch_curve_end)
                performance_note.pitch = tuple(first_part_chord)
                second_part.pitch = tuple(second_part_chord)

        return performance_note, second_part
    else:
        # since the expectation is a tuple as return value, in the event that the split does
        # nothing we return the note unaltered in a length-1 tuple
        return performance_note,


class StaffGroup:

    def __init__(self, staves):
        self.staves = staves

    @classmethod
    def from_measure_bins_of_voice_lists(cls, measure_bins, measure_lengths):
        """
        Creates a StaffGroup with Staves that accomidate engraving_settings.max_voices_per_part voices each
        :param measure_bins: a list of voice lists (can be many voices each)
        :param measure_lengths: a list of the measure lengths (used for specifying bar rest lengths)
        """
        engraving_settings.max_voices_per_part = 3
        num_staffs_required = int(max(math.ceil(len(x) / engraving_settings.max_voices_per_part) for x in measure_bins))

        # create a bunch of dummy bins for the different measures of each staff
        #             measures ->      staffs -v
        # [ [None, None, None, None, None, None, None, None],
        #   [None, None, None, None, None, None, None, None] ]
        staves = [[None] * len(measure_bins) for _ in range(num_staffs_required)]

        for measure_num, (measure_voices, measure_length) in enumerate(zip(measure_bins, measure_lengths)):
            voice_groups = [measure_voices[i:i + engraving_settings.max_voices_per_part]
                            for i in range(0, len(measure_voices), engraving_settings.max_voices_per_part)]

            for staff_num in range(len(staves)):
                if staff_num < len(voice_groups):
                    this_voice_group = voice_groups[staff_num]
                    if all(x is None for x in this_voice_group):
                        # this staff is empty for this measure; put the length of the measure for making the bar rest
                        staves[staff_num][measure_num] = measure_length
                    else:
                        if this_voice_group[0] is None:
                            # if the first voice is empty, it needs a measure length placeholder for making the bar rest
                            this_voice_group[0] = measure_length
                        staves[staff_num][measure_num] = this_voice_group
                else:
                    # the active voices here don't extend to all staves
                    staves[staff_num][measure_num] = measure_length

        # At this point, each entry in the staves / measures matrix is either
        #   (1) a number, in which case it is an empty measure of this length
        #   (2) a list of voices, each of which is either:
        #       - a list of PerformanceNotes
        #       - a number, in the case of an empty voice 1, which requires a bar rest
        #       - None, in the case of an empty voice other than 1 which can be ignored

        return cls([Staff.from_measure_bins_of_voice_lists(x) for x in staves])

    def get_XML(self):
        pass


class Staff:

    def __init__(self, measures):
        self.measures = measures

    @classmethod
    def from_measure_bins_of_voice_lists(cls, measure_bins):
        # Espects a list of measure bins formatted as outputted by StaffGroup.from_measure_bins_of_voice_lists
        # I.e. a list whose entries are either:
        #   (1) a number, in which case it is an empty measure of this length
        #   (2) a list of voices, each of which is either:
        #       - a list of PerformanceNotes
        #       - a number, in the case of an empty voice 1, which requires a bar rest
        #       - None, in the case of an empty voice other than 1 which can be ignored
        return cls([Measure.from_list_of_performance_voices(measure_content) if isinstance(measure_content, list)
                    else Measure.empty_measure(measure_content) for measure_content in measure_bins])

    def get_XML(self):
        pass


class Measure:

    # TODO: Probably needs time signatures!!!??!?
    def __init__(self, voices):
        self.voices = voices

    @classmethod
    def empty_measure(cls, length):
        return cls([Voice.empty_voice(length)])

    @classmethod
    def from_list_of_performance_voices(cls, voices_list):
        # voices_list consists of elements each of which is either:
        #   - a number, standing for the length of the empty measure, used for an empty voice 1
        #   - a (list of PerformanceNotes, measure quantization record) tuple for an active voice
        #   - None, for a skipped voice (i.e. an empty voice other than voice 1)
        return cls([Voice.from_performance_voice(*voice_content) if isinstance(voice_content, tuple)
                    else Voice.empty_voice(voice_content) if voice_content is not None else None
                    for voice_content in voices_list])

    def get_XML(self):
        pass


class Voice:

    def __init__(self, contents, length):
        self.contents = contents
        self.length = length
        # print("THE VOICE:")
        # print("[\n   " + "\n   ".join(str(x) for x in self.contents) + "\n]")

    @classmethod
    def empty_voice(cls, length):
        return cls(None, length)

    @classmethod
    def from_performance_voice(cls, notes, measure_quantization):
        """
        This is where a lot of the magic of converting performed notes to written symbols occurs.
        :param notes: the list of PerformanceNotes played in this measure
        :param measure_quantization: the quantization used for this measure for this voice
        :return: a Voice object containing all the notation
        """
        length = measure_quantization.measure_length

        # change each PerformanceNote to have a start_time relative to the start of the measure
        for note in notes:
            note.start_time -= measure_quantization.start_time

        notes = Voice._fill_in_rests(notes, length)
        # break notes that cross beat boundaries into two tied notes
        # later, some of these can be recombined, but we need to convert them to NoteLikes first

        notes = Voice._split_notes_at_beats(notes, [beat.start_time_in_measure for beat in measure_quantization.beats])

        # construct the processed contents of this voice (made up of NoteLikes Tuplets)
        processed_contents = []
        for beat_quantization in measure_quantization.beats:
            notes_from_this_beat = []

            while len(notes) > 0 and \
                    notes[0].start_time < beat_quantization.start_time_in_measure + beat_quantization.length:
                # go through all the notes in this beat
                notes_from_this_beat.append(notes.pop(0))

            processed_contents.extend(Voice._process_and_convert_beat(notes_from_this_beat, beat_quantization))

        # instantiate and return the constructed voice
        return cls(processed_contents, length)

    @staticmethod
    def _fill_in_rests(notes, total_length):
        notes_and_rests = []
        t = 0
        for note in notes:
            if t < note.start_time:
                notes_and_rests.append(PerformanceNote(t, note.start_time - t, None, None, {}))
            notes_and_rests.append(note)
            t = note.end_time

        if t < total_length:
            notes_and_rests.append(PerformanceNote(t, total_length - t, None, None, {}))
        return notes_and_rests

    @staticmethod
    def _split_notes_at_beats(notes, beats):
        for beat in beats:
            split_notes = []
            for note in notes:
                split_notes.extend(_split_performance_note_at_beat(note, beat))
            notes = split_notes
        return notes

    @staticmethod
    def _process_and_convert_beat(beat_notes, beat_quantization):
        if beat_quantization.divisor is None:
            # if there's no beat divisor, then it should just be a note or rest of the full length of the beat
            assert len(beat_notes) == 1
            pitch, length, properties = beat_notes[0].pitch, beat_notes[0].length, beat_notes[0].properties

            if is_single_note_length(length):
                return [NoteLike(pitch, length, properties)]
            else:
                constituent_lengths = length_to_undotted_constituents(length)
                return [NoteLike(pitch, l, properties) for l in constituent_lengths]

        # if the divisor requires a tuplet, we construct it
        tuplet = Tuplet.from_length_and_divisor(beat_quantization.length, beat_quantization.divisor) \
            if beat_quantization.divisor is not None else None

        dilation_factor = 1 if tuplet is None else tuplet.dilation_factor()
        written_division_length = beat_quantization.length / beat_quantization.divisor * dilation_factor

        division_indispensabilities = _get_beat_division_indispensabilities(beat_quantization.length,
                                                                            beat_quantization.divisor)

        for note in beat_notes:
            written_length = note.length * dilation_factor
            if is_single_note_length(written_length):
                written_length_components = [written_length]
            else:
                written_length_components = length_to_undotted_constituents(written_length)

            # try every permutation of the length constituents. Get a score for it by multiplying the length of
            # each constituent with the indispensability of that pulse within the beat and summing them.
            best_permutation = None
            best_score = 0

            for permutation in permutations(written_length_components):

                division_indices = [int(round(x / written_division_length)) for x in accumulate([0]+written_length_components)]
                score = sum(segment_length * division_indispensabilities[division_index]
                            for division_index, segment_length in zip(division_indices, permutation))
                if score > best_score:
                    best_score = score
                    best_permutation = permutation

            print(best_permutation)
        return []

    def get_XML(self):
        pass


class Tuplet:

    def __init__(self, tuplet_divisions, normal_divisions, division_length, contents=None):
        """
        Creates a tuplet representing tuplet_divisions in the space of normal_divisions of division_length
        e.g. 7, 4, and 0.25 would mean '7 in the space of 4 sixteenth notes'
        """
        self.tuplet_divisions = tuplet_divisions
        self.normal_divisions = normal_divisions
        self.division_length = division_length
        self.contents = contents if contents is not None else []

    def dilation_factor(self):
        return self.tuplet_divisions / self.normal_divisions

    def append(self, note_like_object):
        assert isinstance(note_like_object, NoteLike)
        self.contents.append(note_like_object)

    def length(self):
        return self.normal_divisions * self.division_length

    def length_within_tuplet(self):
        return self.tuplet_divisions * self.division_length

    @classmethod
    def from_length_and_divisor(cls, length, divisor):
        # constructs the appropriate tuplet from the length and the divisor

        # consider a beat length of 1.5 and a tuplet of 11
        # normal_divisions gets set initially to 3 and normal type gets set to 8, since it's 3 eighth notes long
        beat_length_fraction = Fraction(length).limit_denominator()
        normal_divisions = beat_length_fraction.numerator
        # (if denominator is 1, normal type is quarter note, 2 -> eighth note, etc.)
        normal_type = 4 * beat_length_fraction.denominator

        # now, we keep dividing the beat in two until we're just about to divide it into more pieces than the divisor
        # so in our example, we start with 3 8th notes, then 6 16th notes, but we don't go up to 12 32nd notes, since
        # that is more than the beat divisor of 11. Now we know that we are looking at 11 in the space of 6 16th notes.
        while normal_divisions * 2 <= divisor:
            normal_divisions *= 2
            normal_type *= 2

        if normal_divisions == divisor:
            # if the beat divisor exactly equals the normal number, then we don't have a tuplet at all,
            # just a standard duple division. Return None to signify that
            return None
        else:
            # otherwise, construct a tuplet from our answer
            return cls(divisor, normal_divisions, 4.0 / normal_type)

    def __repr__(self):
        return "Tuplet({}, {}, {})".format(self.tuplet_divisions, self.normal_divisions, self.division_length,
                                           super().__repr__())


class NoteLike:

    def __init__(self, pitch, written_length, properties):
        """
        Represents note, chord, or rest that can be notated without ties
        :param pitch: tuple if a pitch, None if a rest
        """
        self.pitch = pitch
        self.written_length = written_length
        self.properties = properties
