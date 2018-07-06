from playcorder.performance import PerformancePart, PerformanceNote
from playcorder.settings import engraving_settings
from copy import deepcopy
import math
from fractions import Fraction
from playcorder.utilities import get_standard_indispensability_array, prime_factor


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
        for note in notes:
            note.start_time -= measure_quantization.start_time
        notes = Voice._fill_in_rests(notes, length)
        notes = Voice._split_notes_at_beats(notes, [beat.start_time - measure_quantization.start_time
                                                    for beat in measure_quantization.beats])
        Voice._set_note_tuplet_info(notes, measure_quantization)
        print(notes)
        # Not appropriate yet!
        return cls(notes, length)

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
    def _set_note_tuplet_info(notes, measure_quantization):
        notes = list(notes)
        for beat_quantization in measure_quantization.beats:
            tuplet = Tuplet.from_length_and_divisor(beat_quantization.beat_length, beat_quantization.divisor) \
                if beat_quantization.divisor is not None else None

            while len(notes) > 0 and notes[0].start_time < beat_quantization.end_time:
                # go through all the notes in this beat
                this_note = notes.pop(0)
                assert isinstance(this_note, PerformanceNote)
                # it's useful to keep track of the quantization of the beat the note is a part of
                # for later ordering of the tied constituents of the note
                this_note.properties["_beat_quantization"] = beat_quantization

                if tuplet is not None:
                    this_note.properties["_tuplet"] = tuplet
                    this_note.properties["_written_length"] = this_note.length * tuplet.dilation_factor()

                    if this_note.start_time == beat_quantization.start_time:
                        this_note.properties["_starts_tuplet"] = True
                    if this_note.end_time == beat_quantization.end_time:
                        this_note.properties["_ends_tuplet"] = True
                else:
                    this_note.properties["_tuplet"] = None
                    this_note.properties["_written_length"] = this_note.length

    def get_XML(self):
        pass


def _process_voice(pc_voice, beat_schemes, beat_divisors):
    _set_tuplets_for_notes_in_voice(pc_voice, beat_schemes, beat_divisors)
    _break_notes_into_undotted_constituents(pc_voice, beat_schemes, beat_divisors)
    # this one doesn't modify in place, since we're changing the number of notes
    pc_voice = _separate_note_components_into_different_notes(pc_voice)
    return pc_voice


def _break_notes_into_undotted_constituents(voice, beat_schemes, beat_divisors):
    # first, we  decompose a note into its undotted constituents
    for pc_note in voice:
        if is_single_note_length(pc_note.length):
            pc_note.length_without_tuplet = [pc_note.length_without_tuplet]
        else:
            pc_note.length_without_tuplet = PCNote.length_to_undotted_constituents(pc_note.length_without_tuplet)

    # if it can't be represented with a single notehead, we order the constituent noteheads so that larger noteheads
    # sit on more important subdivisions. We use indispensability to judge the importance of subdivisions
    for beat_scheme, divisor in zip(beat_schemes, beat_divisors):
        if divisor is None:
            continue
        beat_indispensabilities = get_standard_indispensability_array(
            _get_multiplicative_beat_meter(beat_scheme.beat_length, divisor), normalize=True
        )
        notes_in_beat = [pc_note for pc_note in voice
                         if beat_scheme.start_time <= pc_note.start_time < beat_scheme.end_time]
        for pc_note in notes_in_beat:
            if len(pc_note.length_without_tuplet) == 1:
                # this case really shouldn't come up, since we returned above if there's only one constituent duration
                continue
            else:
                # try every permutation of the duration constituents. Get a score for it by multiplying the length of
                # each constituent with the indispensability of that pulse within the beat and summing them.
                best_permutation = None
                best_score = 0
                for permutation in permutations(pc_note.length_without_tuplet):
                    score = 0.
                    position = (pc_note.start_time - beat_scheme.start_time) * beat_scheme.length_without_tuplet / beat_scheme.beat_length
                    for segment in permutation:
                        score += beat_indispensabilities[int(round(position / beat_scheme.length_without_tuplet * divisor))] * segment
                        position += segment
                    if score > best_score:
                        best_score = score
                        best_permutation = permutation
                pc_note.length_without_tuplet = list(best_permutation)


def _get_multiplicative_beat_meter(beat_length, beat_divisor):
    # a beat of length 1.5 = 3/2 prefers to divide into 3 first
    # a beat length of 3.75 = 15/4 prefers to divide fist into 3 then into 5
    natural_divisions = sorted(Fraction(beat_length).limit_denominator().numerator, reverse=True)
    prime_decomposition = prime_factor(beat_divisor)
    prime_decomposition.sort()
    print(prime_decomposition, natural_division)
    for preferred_factor in sorted(prime_factor(natural_division), reverse=True):
        print(preferred_factor)
        prime_decomposition.insert(0, prime_decomposition.pop(prime_decomposition.index(preferred_factor)))
    return prime_decomposition


class Tuplet:

    def __init__(self, tuplet_divisions, normal_divisions, division_length):
        """
        Creates a tuplet representing tuplet_divisions in the space of normal_divisions of division_length
        e.g. 7, 4, and 0.25 would mean '7 in the space of 4 sixteenth notes'
        """
        self.tuplet_divisions = tuplet_divisions
        self.normal_divisions = normal_divisions
        self.division_length = division_length

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

    def __repr__(self):
        return "Tuplet({}, {}, {})".format(self.tuplet_divisions, self.normal_divisions, self.division_length)


class NoteLike:

    def __init__(self, pitch, written_length, properties):
        """
        Represents note, chord, or rest that can be notated without ties
        :param pitch:
        :param length:
        :param properties:
        """
        self.pitch = pitch
        self.written_length = written_length
        self.properties = properties
