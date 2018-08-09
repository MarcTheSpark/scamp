from playcorder.performance import PerformancePart, PerformanceNote
from playcorder.settings import engraving_settings
from playcorder.parameter_curve import ParameterCurve
from playcorder.quantization import QuantizationRecord, TimeSignature
from copy import deepcopy
import math
from fractions import Fraction
from itertools import permutations, accumulate, count
from playcorder.utilities import get_standard_indispensability_array, prime_factor, floor_x_to_pow_of_y
import textwrap
import abjad
from collections import namedtuple


# TODO: Voice processing rewrite:
# 1) snip all voices into pieces: If there's a rest AND a measure break between two notes, then snip into two pieces.
# consider each of these pieces to be a certain number of measures in length, starting in a given measure. Should be
# a tuple of (start_measure, end_measure, notes_list, voice_number_or_average_pitch)
# 2) Sort the pieces into their positions. Starting from the first measure, take all pieces that start in that measure
# and first place all of the pieces with a numbered voice, then place all the pieces with named voices in order of
# average pitch. Then go to the second measure, check which slots are still filled from pieces that started in the
# first measure and are still going on, add in the numbered voice pieces, and then add the named voice pieces.
# continue like that until done.

# a list of tied NoteLikes. They'll also need to split up any pitch ParameterCurves into their chunks.
# For now, we'll do this as gracenotes, but maybe there can be a setting that first splits a note into constituents
# based on the key points of the param curve and then splits those constituents into reproducible notes?


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


# ---------------------------------------------- Other Utilities --------------------------------------------


_id_generator = count()


def _split_performance_note_at_beat(performance_note: PerformanceNote, split_beat):
    if performance_note.start_time < split_beat < performance_note.end_time:
        second_part = deepcopy(performance_note)
        second_part.start_time = split_beat
        second_part.end_time = performance_note.end_time
        performance_note.end_time = split_beat

        if performance_note.pitch is not None:
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

            # also, if this isn't a rest, then we're going to need to keep track of ties that will be needed
            performance_note.properties["_starts_tie"] = True
            second_part.properties["_ends_tie"] = True

            # we also want to keep track of which notes came from the same original note for doing ties and such
            if "_source_id" in performance_note.properties:
                second_part.properties["_source_id"] = performance_note.properties["_source_id"]
            else:
                second_part.properties["_source_id"] = performance_note.properties["_source_id"] = next(_id_generator)

        return performance_note, second_part
    else:
        # since the expectation is a tuple as return value, in the event that the split does
        # nothing we return the note unaltered in a length-1 tuple
        return performance_note,


# ---------------------------------------- Performance Part Conversion -----------------------------------------


def quantized_performance_part_to_staff_group(quantized_performance_part: PerformancePart):
    assert quantized_performance_part.is_quantized()

    fragments = _separate_voices_into_fragments(quantized_performance_part)
    measure_voice_grid = _create_measure_voice_grid(fragments, len(quantized_performance_part.measure_lengths))
    return StaffGroup.from_measure_voice_grid(
        measure_voice_grid, quantized_performance_part.get_longest_quantization_record()
    )


_NumberedVoiceFragment = namedtuple("_NumberedVoiceFragment", "voice_num start_measure_num measures_with_quantizations")
_NamedVoiceFragment = namedtuple("_NamedVoiceFragment", "average_pitch start_measure_num measures_with_quantizations")


def _construct_voice_fragment(voice_name, notes, start_measure_num, measure_quantizations):
    average_pitch = sum(note.average_pitch() for note in notes) / len(notes)

    # split the notes into measures, breaking notes that span a barline in two
    # save each to measures_with_quantizations, in a tuple along with the corresponding quantization
    measures_with_quantizations = []
    for measure_quantization in measure_quantizations:
        measure_end_time = measure_quantization.start_time + measure_quantization.measure_length
        this_measure_notes = []
        remaining_notes = []
        for note in notes:
            # check if the note starts in the measure
            if measure_quantization.start_time <= note.start_time < measure_end_time:
                # check if it straddles the following barline
                if note.end_time > measure_end_time:
                    first_half, second_half = _split_performance_note_at_beat(note, measure_end_time)
                    this_measure_notes.append(first_half)
                    remaining_notes.append(second_half)
                else:
                    # note is fully within the measure
                    this_measure_notes.append(note)
            else:
                # if it happens in a later measure, save it for later
                remaining_notes.append(note)
        notes = remaining_notes
        measures_with_quantizations.append((this_measure_notes, measure_quantization))

    # then decide based on the name of the voice whether it is from a numbered voice, which gets treated differently
    try:
        # numbered voice
        voice_num = int(voice_name)
        return _NumberedVoiceFragment(voice_num, start_measure_num, measures_with_quantizations)
    except ValueError:
        # not a numbered voice, so we want to order voices mostly by pitch
        return _NamedVoiceFragment(average_pitch, start_measure_num, measures_with_quantizations)


def _separate_voices_into_fragments(quantized_performance_part: PerformancePart):
    """
    Splits the part's voices into fragments where divisions occur whenever there is a measure break at a rest.
    If there's a measure break but not a rest, we're probably in the middle of a melodic gesture, so don't want to
    separate. If there's a rest but not a measure break then we should also probably keep the notes together in a
    single voice, since they were specified to be in the same voice.
    :param quantized_performance_part: a quantized PerformancePart
    :return: a tuple of (numbered_fragments, named_fragments), where the numbered_fragments come from numbered voices
    and are of the form (voice_num, notes_list, start_measure_num, end_measure_num, measure_quantization_schemes),
    while the named_fragments are of the form (notes_list, start_measure_num, end_measure_num,
    measure_quantization_schemes)
    """
    fragments = []

    for voice_name, note_list in quantized_performance_part.voices.items():
        # first we make an enumeration iterator for the measures
        if len(note_list) == 0:
            continue

        quantization_record = quantized_performance_part.voice_quantization_records[voice_name]
        assert isinstance(quantization_record, QuantizationRecord)
        measure_quantization_iterator = enumerate(quantization_record.quantized_measures)

        # the idea is that we build a current_fragment up until we encounter a rest at a barline
        # when that happens, we save the old fragment and start a new one
        current_fragment = []
        fragment_measure_quantizations = []
        current_measure_num, current_measure = next(measure_quantization_iterator)
        fragment_start_measure = 0

        for performance_note in note_list:
            # update so that current_measure is the measure that performance_note starts in
            while performance_note.start_time >= current_measure.start_time + current_measure.measure_length:
                # we're past the old measure, so increment to next measure
                current_measure_num, current_measure = next(measure_quantization_iterator)
                # if this measure break coincides with a rest, then we start a new fragment
                if len(current_fragment) > 0 and current_fragment[-1].end_time < performance_note.start_time:
                    fragments.append(_construct_voice_fragment(voice_name, current_fragment,
                                                               fragment_start_measure, fragment_measure_quantizations))
                    # reset all the fragment-building variables
                    current_fragment = []
                    fragment_measure_quantizations = []
                    fragment_start_measure = current_measure_num
                elif len(current_fragment) == 0:
                    # don't mark the start measure until we actually have a note!
                    fragment_start_measure = current_measure_num

            # add the new note to the current fragment
            current_fragment.append(performance_note)

            # make sure that fragment_measure_quantizations has a copy of the measure this note starts in
            if len(fragment_measure_quantizations) == 0 or fragment_measure_quantizations[-1] != current_measure:
                fragment_measure_quantizations.append(current_measure)

            # now we move forward to the end of the note, and update the measure we're on
            # (Note the > rather than a >= sign. For the end of the note, it has to actually cross the barline.)
            while performance_note.end_time > current_measure.start_time + current_measure.measure_length:
                current_measure_num, current_measure = next(measure_quantization_iterator)
                # when we cross into a new measure, add it to the measure quantizations
                fragment_measure_quantizations.append(current_measure)

        # once we're done going through the voice, save the last fragment and move on
        if len(current_fragment) > 0:
            fragments.append(_construct_voice_fragment(voice_name, current_fragment,
                                                       fragment_start_measure, fragment_measure_quantizations))

    return fragments


def _create_measure_voice_grid(fragments, num_measures):
    numbered_fragments = []
    named_fragments = []
    while len(fragments) > 0:
        fragment = fragments.pop()
        if isinstance(fragment, _NumberedVoiceFragment):
            numbered_fragments.append(fragment)
        else:
            named_fragments.append(fragment)

    measure_grid = [[] for _ in range(num_measures)]

    def is_cell_free(which_measure, which_voice):
        return len(measure_grid[which_measure]) <= which_voice or measure_grid[which_measure][which_voice] is None

    # sort by measure number (i.e. fragment[2]) then by voice number (i.e. fragment[0])
    numbered_fragments.sort(key=lambda frag: (frag.start_measure_num, frag.voice_num))
    # sort by measure number (i.e. fragment[2]) then inversely by average pitch (i.e. fragment[0])
    named_fragments.sort(key=lambda frag: (frag.start_measure_num, -frag.average_pitch))

    for fragment in numbered_fragments:
        assert isinstance(fragment, _NumberedVoiceFragment)
        measure_num = fragment.start_measure_num
        for measure_with_quantization in fragment.measures_with_quantizations:
            while len(measure_grid[measure_num]) <= fragment.voice_num:
                measure_grid[measure_num].append(None)
            measure_grid[measure_num][fragment.voice_num] = measure_with_quantization
            measure_num += 1

    for fragment in named_fragments:
        assert isinstance(fragment, _NamedVoiceFragment)
        measure_range = range(fragment.start_measure_num,
                              fragment.start_measure_num + len(fragment.measures_with_quantizations))
        voice_num = 0
        while not all(is_cell_free(measure_num, voice_num) for measure_num in measure_range):
            voice_num += 1

        measure_num = fragment.start_measure_num
        for measure_with_quantization in fragment.measures_with_quantizations:
            while len(measure_grid[measure_num]) <= voice_num:
                measure_grid[measure_num].append(None)
            measure_grid[measure_num][voice_num] = measure_with_quantization
            measure_num += 1

    return measure_grid


# ---------------------------------------------- Score Classes --------------------------------------------


class StaffGroup:

    def __init__(self, staves):
        self.staves = staves

    @classmethod
    def from_measure_voice_grid(cls, measure_bins, quantization_record):
        """
        Creates a StaffGroup with Staves that accommodate engraving_settings.max_voices_per_part voices each
        :param measure_bins: a list of voice lists (can be many voices each)
        :param quantization_record: a QuantizationRecord
        """
        num_staffs_required = int(max(math.ceil(len(x) / engraving_settings.max_voices_per_part) for x in measure_bins))

        # create a bunch of dummy bins for the different measures of each staff
        #             measures ->      staffs -v
        # [ [None, None, None, None, None, None, None, None],
        #   [None, None, None, None, None, None, None, None] ]
        staves = [[None] * len(measure_bins) for _ in range(num_staffs_required)]

        for measure_num, measure_voices in enumerate(measure_bins):
            # this breaks up the measure's voices into groups of length max_voices_per_part
            # (the last group might have fewer)
            voice_groups = [measure_voices[i:i + engraving_settings.max_voices_per_part]
                            for i in range(0, len(measure_voices), engraving_settings.max_voices_per_part)]

            for staff_num in range(len(staves)):
                # for each staff, check if this measure has enough voices to even reach that staff
                if staff_num < len(voice_groups):
                    # if so, let's take a look at our voices for this measure
                    this_voice_group = voice_groups[staff_num]
                    if all(x is None for x in this_voice_group):
                        # if all the voices are empty, this staff is empty for this measure. Put None to indicate that
                        staves[staff_num][measure_num] = None
                    else:
                        # otherwise, there's something there, so put tne voice group in the slot
                        staves[staff_num][measure_num] = this_voice_group
                else:
                    # if not, put None there to indicate an empty measure
                    staves[staff_num][measure_num] = None

        # At this point, each entry in the staves / measures matrix is either
        #   (1) None, indicating an empty measure
        #   (2) a list of voices, each of which is either:
        #       - a list of PerformanceNotes or
        #       - None, in the case of an empty voice

        return cls([Staff.from_measure_bins_of_voice_lists(x, quantization_record.time_signatures) for x in staves])

    def to_abjad(self):
        return abjad.StaffGroup([staff.to_abjad() for staff in self.staves])

    def get_XML(self):
        pass


class Staff:

    def __init__(self, measures):
        self.measures = measures

    @classmethod
    def from_measure_bins_of_voice_lists(cls, measure_bins, time_signatures):
        # Expects a list of measure bins formatted as outputted by StaffGroup.from_measure_bins_of_voice_lists
        #   (1) None, indicating an empty measure
        #   (2) a list of voices, each of which is either:
        #       - a list of PerformanceNotes or
        #       - None, in the case of an empty voice
        return cls([Measure.from_list_of_performance_voices(measure_content, time_signature)
                    if measure_content is not None else Measure.empty_measure(time_signature)
                    for measure_content, time_signature in zip(measure_bins, time_signatures)])

    def to_abjad(self):
        return abjad.Staff([measure.to_abjad() for measure in self.measures])

    def get_XML(self):
        pass


_voice_names = [r'\voiceOne', r'\voiceTwo', r'\voiceThree', r'\voiceFour']


class Measure:

    def __init__(self, voices, time_signature):
        self.voices = voices
        self.time_signature = time_signature

    @classmethod
    def empty_measure(cls, time_signature):
        return cls([Voice.empty_voice(time_signature)], time_signature)

    @classmethod
    def from_list_of_performance_voices(cls, voices_list, time_signature):
        # voices_list consists of elements each of which is either:
        #   - a (list of PerformanceNotes, measure quantization record) tuple for an active voice
        #   - None, for an empty voice
        if all(voice_content is None for voice_content in voices_list):
            # if all the voices are empty, just make an empty measure
            return cls.empty_measure(time_signature)
        else:
            voices = []
            for i, voice_content in enumerate(voices_list):
                if voice_content is None:
                    if i == 0:
                        # an empty first voice should be expressed as a bar rest
                        voices.append(Voice.empty_voice(time_signature))
                    else:
                        # an empty other voice can just be ignored. Put a placeholder of None
                        voices.append(None)
                else:
                    # should be a (list of PerformanceNotes, measure quantization record) tuple
                    voices.append(Voice.from_performance_voice(*voice_content))
            return cls(voices, time_signature)

    def to_abjad(self):
        abjad_measure = abjad.Measure(self.time_signature.to_abjad())
        for i, voice in enumerate(self.voices):
            if voice is None:
                continue
            abjad_voice = self.voices[i].to_abjad()
            literal = abjad.LilyPondLiteral(_voice_names[i+1])
            abjad.attach(literal, abjad_voice)
            abjad_measure.append(abjad_voice)
        abjad_measure.is_simultaneous = True
        return abjad_measure

    def get_XML(self):
        pass


class Voice:

    def __init__(self, contents, time_signature):
        self.contents = contents
        self.time_signature = time_signature

    @classmethod
    def empty_voice(cls, time_signature):
        return cls(None, time_signature)

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
        return cls(processed_contents, measure_quantization.time_signature)

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
        beat_start_time = beat_notes[0].start_time

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

        note_list = tuplet.contents if tuplet is not None else []

        for note in beat_notes:
            written_length = note.length * dilation_factor
            if is_single_note_length(written_length):
                written_length_components = [written_length]
            else:
                written_length_components = length_to_undotted_constituents(written_length)

            # try every permutation of the length constituents. Get a score for it by multiplying the length of
            # each constituent with the indispensability of that pulse within the beat and summing them.
            best_permutation = written_length_components
            best_score = 0

            for permutation in permutations(written_length_components):
                accumulated_length = note.start_time - beat_start_time
                division_indices = [int(round(accumulated_length / written_division_length))]
                for component_length in permutation[:-1]:
                    accumulated_length += component_length
                    division_indices.append(int(round(accumulated_length / written_division_length)))

                score = sum(segment_length * division_indispensabilities[division_index]
                            for division_index, segment_length in zip(division_indices, permutation))

                if score > best_score:
                    best_score = score
                    best_permutation = permutation

            note_parts = []
            remainder = note
            for segment_length in best_permutation:

                split_note = _split_performance_note_at_beat(
                    remainder, remainder.start_time + segment_length / dilation_factor
                )
                if len(split_note) > 1:
                    this_segment, remainder = split_note
                else:
                    this_segment = split_note[0]

                note_parts.append(NoteLike(this_segment.pitch, segment_length, this_segment.properties))

            note_list.extend(note_parts)

        return [tuplet] if tuplet is not None else note_list

    def to_abjad(self):
        if self.contents is None:
            return abjad.Voice("{{R{}*{}}}".format(self.time_signature.denominator, self.time_signature.numerator))
        else:
            return abjad.Voice([x.to_abjad() for x in self.contents])

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

    def to_abjad(self):
        return abjad.Tuplet(abjad.Multiplier(self.normal_divisions, self.tuplet_divisions),
                            [note_like.to_abjad() for note_like in self.contents])

    def __repr__(self):
        contents_string = ", contents=[\n{}\n]".format(
            textwrap.indent(",\n".join(str(x) for x in self.contents), "   ")
        ) if len(self.contents) > 0 else ""
        return "Tuplet({}, {}, {}{})".format(self.tuplet_divisions, self.normal_divisions, self.division_length,
                                             contents_string)


class NoteLike:

    def __init__(self, pitch, written_length, properties):
        """
        Represents note, chord, or rest that can be notated without ties
        :param pitch: tuple if a pitch, None if a rest
        """
        self.pitch = pitch
        self.written_length = written_length
        self.properties = properties

    def __repr__(self):
        return "NoteLike(pitch={}, written_length={}, properties={})".format(
            self.pitch, self.written_length, self.properties
        )

    def to_abjad(self):
        duration = Fraction(self.written_length / 4).limit_denominator()
        if self.pitch is None:
            abjad_object = abjad.Rest(duration)
        elif isinstance(self.pitch, tuple):
            chord = abjad.Chord()
            chord.written_duration = duration
            if isinstance(self.pitch[0], ParameterCurve):
                chord.note_heads = [x.start_level() - 60 for x in self.pitch]
            else:
                chord.note_heads = [x - 60 for x in self.pitch]
            abjad_object = chord
        elif isinstance(self.pitch, ParameterCurve):
            abjad_object = abjad.Note(self.pitch.start_level() - 60, duration)
        else:
            abjad_object = abjad.Note(self.pitch - 60, duration)
        if "_starts_tie" in self.properties and self.properties["_starts_tie"]:
            abjad.attach(abjad.Tie(), abjad_object)
        return abjad_object


