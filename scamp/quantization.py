from fractions import Fraction
from .utilities import indigestibility, is_multiple, is_x_pow_of_y, round_to_multiple, SavesToJSON
from collections import namedtuple
from .settings import quantization_settings, engraving_settings
from expenvelope import Envelope
from .dependencies import abjad
from numbers import Number
import textwrap

QuantizedBeat = namedtuple("QuantizedBeat", "start_time start_time_in_measure length divisor")

QuantizedMeasure = namedtuple("QuantizedMeasure", "start_time measure_length beats time_signature ")


class QuantizationRecord(SavesToJSON):

    def __init__(self, quantized_measures):
        assert all(isinstance(x, QuantizedMeasure) for x in quantized_measures)
        self.quantized_measures = quantized_measures

    def to_json(self):
        quantized_measures_json_friendly = []
        for quantized_measure in self.quantized_measures:
            quantized_measure_as_dict = quantized_measure._asdict()
            quantized_beats_as_dicts = []
            for beat in quantized_measure.beats:
                quantized_beats_as_dicts.append(beat._asdict())
            quantized_measure_as_dict["beats"] = quantized_beats_as_dicts
            quantized_measure_as_dict["time_signature"] = quantized_measure_as_dict["time_signature"].to_json()
            quantized_measures_json_friendly.append(quantized_measure_as_dict)
        return quantized_measures_json_friendly

    @classmethod
    def from_json(cls, json_object):
        quantized_measures = []
        for quantized_measure_as_dict in json_object:
            quantized_measure_as_dict["time_signature"] = TimeSignature.from_json(
                quantized_measure_as_dict["time_signature"]
            )
            quantized_beats = []
            for quantized_beat_as_dict in quantized_measure_as_dict["beats"]:
                quantized_beats.append(QuantizedBeat(**quantized_beat_as_dict))
            quantized_measure_as_dict["beats"] = quantized_beats
            quantized_measures.append(QuantizedMeasure(**quantized_measure_as_dict))
        return cls(quantized_measures)

    @property
    def measure_lengths(self):
        return [quantized_measure.measure_length for quantized_measure in self.quantized_measures]

    @property
    def time_signatures(self):
        return [quantized_measure.time_signature for quantized_measure in self.quantized_measures]

    def __repr__(self):
        return "QuantizationRecord([\n{}\n])".format(
            textwrap.indent(",\n".join(str(x) for x in self.quantized_measures), "   ")
        )


def quantize_performance_part(part, quantization_scheme, onset_weighting="default", termination_weighting="default",
                              inner_split_weighting="default"):
    """
    Quantizes a performance part (in place) and sets its voice_quantization_records
    :param part: a PerformancePart
    :param quantization_scheme: a QuantizationScheme
    :param onset_weighting: How much do we care about accurate onsets
    :param termination_weighting: How much do we care about accurate terminations
    :param inner_split_weighting: How much do we care about inner segmentation timing (e.g. tuple note lengths)
    :return: a QuantizationRecord, detailing all of the time signatures, beat divisions selected, etc.
    """
    if isinstance(quantization_scheme, (str, Number, TimeSignature)) or isinstance(quantization_scheme, tuple) and \
            len(quantization_scheme) == 2 and all(isinstance(x, int) for x in quantization_scheme):
        # note that a tuple of length 2 with two integers is interpreted as a single time signature, but any other tuple
        # filled with numbers will be interpreted as a list of measure lengths
        quantization_scheme = QuantizationScheme.from_time_signature(quantization_scheme)
    elif hasattr(quantization_scheme, "__len__") and \
            all(isinstance(x, (str, tuple, Number, TimeSignature)) for x in quantization_scheme):
        # make it easy to loop a series of time signatures by adding the string "loop" at the end
        loop = False
        if isinstance(quantization_scheme[-1], str) and quantization_scheme[-1].lower() == "loop":
            quantization_scheme.pop()
            loop = True
        quantization_scheme = QuantizationScheme.from_time_signature_list(quantization_scheme, loop=loop)

    if not isinstance(quantization_scheme, QuantizationScheme):
        raise ValueError("Couldn't understand quantization scheme.")

    part.voice_quantization_records = {}

    for voice_name, voice in list(part.voices.items()):
        quantization_record = _quantize_performance_voice(voice, quantization_scheme,
                                                          onset_weighting, termination_weighting, inner_split_weighting)
        # make any simultaneous notes in the part chords
        _collapse_chords(voice)
        # break the voice into a list of non-overlapping voices. If there was no overlap, this has length 1
        non_overlapping_voices = _separate_into_non_overlapping_voices(voice)

        for i, new_voice in enumerate(non_overlapping_voices):
            if i == 0:
                # the first of the non-overlapping voices just retains the old voice name
                new_voice_name = voice_name
            else:
                # any extra voice created has to be given a related name
                # we follow the pattern 'original_voice', 'original_voice_2', 'original_voice_3', etc.
                k = i+1
                new_voice_name = voice_name + "_{}".format(str(k))
                # in the ridiculous case someone names two voices 'voice' and 'voice_2', and the first one needs to
                # be split up, we'll just have to increment to 'voice_3'
                while new_voice_name in part.voices:
                    k += 1
                    voice_name + "_{}".format(str(k))
            part.voices[new_voice_name] = new_voice
            part.voice_quantization_records[new_voice_name] = quantization_record


def _quantize_performance_voice(voice, quantization_scheme, onset_weighting="default", termination_weighting="default",
                                inner_split_weighting="default"):
    """
    Quantizes a voice (modifying notes in place) and returns a QuantizationRecord
    :param voice: a single voice (list of PerformanceNotes) from a PerformancePart
    :param quantization_scheme: a QuantizationScheme
    :param onset_weighting: How much do we care about accurate onsets
    :param termination_weighting: How much do we care about accurate terminations
    :return: QuantizationRecord, detailing all of the time signatures, beat divisions selected, etc.
    """
    assert isinstance(quantization_scheme, QuantizationScheme)
    if onset_weighting == "default":
        onset_weighting = quantization_settings.onset_weighting
    if termination_weighting == "default":
        termination_weighting = quantization_settings.termination_weighting
    if inner_split_weighting == "default":
        inner_split_weighting = quantization_settings.inner_split_weighting

    if engraving_settings.glissandi.control_point_policy == "split":
        for note in voice:
            note.divide_length_at_gliss_control_points()

    # make list of (note onset time, note) tuples
    raw_onsets = [(performance_note.start_time, performance_note) for performance_note in voice]
    # make list of (note termination time, note) tuples
    raw_terminations = [(performance_note.start_time + performance_note.length_sum(), performance_note)
                        for performance_note in voice]
    # make list of (inner split time, note) tuples
    raw_inner_splits = []
    for performance_note in voice:
        if hasattr(performance_note.length, "__len__"):
            t = performance_note.start_time
            for length_segment in performance_note.length[:-1]:
                t += length_segment
                raw_inner_splits.append((t, performance_note))

    # sort them
    raw_onsets.sort(key=lambda x: x[0])
    raw_terminations.sort(key=lambda x: x[0])
    raw_inner_splits.sort(key=lambda x: x[0])

    beat_scheme_iterator = quantization_scheme.beat_scheme_iterator()
    beat_divisors = []

    while len(raw_onsets) + len(raw_inner_splits) + len(raw_terminations) > 0:
        # First, use all the onsets, inner splits, and terminations in this beat to determine the best divisor
        beat_scheme, beat_start_time = next(beat_scheme_iterator)
        assert isinstance(beat_scheme, BeatQuantizationScheme)
        beat_end_time = beat_start_time + beat_scheme.length

        # find the onsets in this beat
        onsets_in_this_beat = []
        while len(raw_onsets) > 0 and raw_onsets[0][0] < beat_end_time:
            onsets_in_this_beat.append(raw_onsets.pop(0))

        # find the terminations in this beat
        terminations_in_this_beat = []
        while len(raw_terminations) > 0 and raw_terminations[0][0] < beat_end_time:
            terminations_in_this_beat.append(raw_terminations.pop(0))

        # find the inner splits in this beat
        inner_splits_in_this_beat = []
        while len(raw_inner_splits) > 0 and raw_inner_splits[0][0] < beat_end_time:
            inner_splits_in_this_beat.append(raw_inner_splits.pop(0))

        if len(onsets_in_this_beat) + len(terminations_in_this_beat) + len(inner_splits_in_this_beat) == 0:
            # an empty beat, nothing to see here
            beat_divisors.append(None)
            continue

        best_divisor = _get_best_divisor_for_beat(
            beat_scheme, beat_start_time, onsets_in_this_beat, terminations_in_this_beat, inner_splits_in_this_beat,
            onset_weighting, termination_weighting, inner_split_weighting
        )
        beat_divisors.append(best_divisor)

        # Now, quantize all of the notes that start or end in this beat accordingly
        division_length = beat_scheme.length / best_divisor
        for onset, note in onsets_in_this_beat:
            divisions_after_beat_start = round((onset - beat_start_time) / division_length)
            note.start_time = beat_start_time + divisions_after_beat_start * division_length

        for termination, note in terminations_in_this_beat:
            divisions_after_beat_start = round((termination - beat_start_time) / division_length)
            note.end_time = beat_start_time + divisions_after_beat_start * division_length

            if note.length_sum() <= 0:
                # if the quantization collapses the start and end times of a note to the same point,
                # adjust so the the note is a single division_length long.
                if note.end_time + division_length <= beat_end_time:
                    # if there's room to, just move the end of the note one division forward
                    note.length += division_length
                else:
                    # otherwise, move the start of the note one division backward
                    note.start_time -= division_length
                    note.length += division_length

        # we take note of where all the inner splits quantize to, and then once all of the start
        # and end times for the notes are adjusted, we go ahead and put them it.
        for inner_split, note in inner_splits_in_this_beat:
            divisions_after_beat_start = round((inner_split - beat_start_time) / division_length)
            quantized_split_time = beat_start_time + divisions_after_beat_start * division_length
            if "split_points" in note.properties.temp:
                note.properties.temp["split_points"].append(quantized_split_time)
            else:
                note.properties.temp["split_points"] = [quantized_split_time]

    last_note_end_time = 0
    for note in voice:
        # now that all the start and end points have been adjusted,
        # we implement the quantized split points where applicable
        if "split_points" in note.properties.temp:
            last_split_point = note.start_time
            new_lengths = []
            for split_point in sorted(note.properties.temp["split_points"]):
                if round(split_point - last_split_point, 10) > 0:
                    new_lengths.append(split_point - last_split_point)
                last_split_point = split_point
            if round(note.end_time - last_split_point, 10) > 0:
                new_lengths.append(note.end_time - last_split_point)
            note.length = tuple(new_lengths)

        last_note_end_time = max(note.end_time, last_note_end_time)

        # also normalize the pitch envelopes
        if isinstance(note.pitch, Envelope):
            note.pitch.normalize_to_duration(note.length_sum())

    return _construct_quantization_record(beat_divisors, last_note_end_time, quantization_scheme)


def _collapse_chords(notes):
    """
    Modifies a list of PerformanceNotes in place so that simultaneous notes become chords
    (i.e. they become PerformanceNotes with a tuple of different values for the pitch.)
    :param notes: a list of PerformanceNotes
    """
    i = 1
    while i < len(notes):
        if notes[i - 1].attempt_chord_merger_with(notes[i]):
            # if the merger is successful, notes[i] has been incorporated into notes[i-1]
            # so we can simply pop notes[i] and not increment
            notes.pop(i)
        else:
            # otherwise, since the merger fails, we simply increment i
            i += 1


def _separate_into_non_overlapping_voices(notes, max_overlap=1e-10):
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
            if voice[-1].end_time <= note.start_time + max_overlap:
                voice_to_add_to = voice
                break
        if voice_to_add_to is None:
            voice_to_add_to = []
            voices.append(voice_to_add_to)
        voice_to_add_to.append(note)

    return voices


def _get_best_divisor_for_beat(beat_scheme, beat_start_time, onsets_in_beat, terminations_in_beat, inner_splits_in_beat,
                               onset_weighting, termination_weighting, inner_split_weighting):
    # try out each quantization division of a beat and return the best fit
    best_divisor = None
    best_error = float("inf")

    for divisor, undesirability in beat_scheme.quantization_divisions:
        division_length = beat_scheme.length / divisor
        total_squared_onset_error = 0
        total_squared_termination_error = 0
        total_squared_inner_split_error = 0

        for onset in onsets_in_beat:
            time_since_beat_start = onset[0] - beat_start_time
            # squared distance from closest division of the beat
            total_squared_onset_error += \
                (time_since_beat_start - round_to_multiple(time_since_beat_start, division_length)) ** 2

        for termination in terminations_in_beat:
            time_since_beat_start = termination[0] - beat_start_time
            # squared distance from closest division of the beat
            total_squared_termination_error += \
                (time_since_beat_start - round_to_multiple(time_since_beat_start, division_length)) ** 2

        for inner_split in inner_splits_in_beat:
            time_since_beat_start = inner_split[0] - beat_start_time
            # squared distance from closest division of the beat
            total_squared_inner_split_error += \
                (time_since_beat_start - round_to_multiple(time_since_beat_start, division_length)) ** 2

        this_div_error_score = undesirability * (termination_weighting * total_squared_termination_error +
                                                 onset_weighting * total_squared_onset_error +
                                                 inner_split_weighting * total_squared_inner_split_error)

        if this_div_error_score < best_error:
            best_divisor = divisor
            best_error = this_div_error_score

    return best_divisor


def _construct_quantization_record(beat_divisors, end_time, quantization_scheme):
    """
    Constructs a QuantizationRecord from the given scheme and divisors
    :param beat_divisors: a list of beat divisors resulting from quantization
    :param end_time: This helps us cover the special case in which the last note ends at the very end of a measure.
    In this case, it's termination gets quantized in the first beat of the next measure, so we have a beat divisor
    in that measure but no actual notes there. By checking if we've hit the end_time we can avoid constructing
    that extra measure.
    :param quantization_scheme: the quantization scheme being used
    :return: a QuantizationRecord
    """
    assert isinstance(beat_divisors, list)
    quantized_measures = []
    for measure_scheme, t in quantization_scheme.measure_scheme_iterator():
        quantized_measure = QuantizedMeasure(t, measure_scheme.length, [], measure_scheme.time_signature)
        for beat_scheme in measure_scheme.beat_schemes:
            divisor = beat_divisors.pop(0) if len(beat_divisors) > 0 else None
            quantized_measure.beats.append(
                QuantizedBeat(t, t - quantized_measure.start_time, beat_scheme.length, divisor)
            )
            t += beat_scheme.length
        quantized_measures.append(quantized_measure)
        if len(beat_divisors) == 0 or t >= end_time:
            return QuantizationRecord(quantized_measures)


class BeatQuantizationScheme:

    def __init__(self, length, divisors, simplicity_preference="default"):
        """
        A scheme for making a decision about which divisor to use to quantize a beat
        :param length: In quarter-notes
        :param divisors: A list of allowed divisors or a list of tuples of (divisor, undesirability). If just
        divisors are given, the undesirability for wach will be calculated based on its indigestibility.
        :param simplicity_preference: ranges 0 - whatever. A simplicity_preference of 0 means, all divisions are
        treated equally; a 7 is as good as a 4. A simplicity_preference of 1 means that the most desirable division
        is left alone, the most undesirable division gets its error doubled, and all other divisions are somewhere in
        between. Simplicity preference can be greater than 1, in which case the least desirable division gets its
        error multiplied by (simplicity_preference + 1)
        """
        # load default if not specified
        if simplicity_preference == "default":
            simplicity_preference = quantization_settings.simplicity_preference

        # actual length of the beat
        self.length = float(length)
        self.length_as_fraction = Fraction(length).limit_denominator()

        # now we populate a self.quantization_divisions with tuples consisting of the allowed divisions and
        # their undesirabilities. Undesirability is a factor by which the error in a given quantization option
        # is multiplied; the lowest possible undesirability is 1
        assert hasattr(divisors, "__len__") and len(divisors) > 0
        if isinstance(divisors[0], tuple):
            # already (divisor, undesirability) tuples
            self.quantization_divisions = divisors
        else:
            # we've just been given the divisors, and have to figure out the undesirabilities
            if len(divisors) == 1:
                # there's only one way we're allowed to divide the beat, so just give it undesirability 1, whatever
                self.quantization_divisions = list(zip(divisors, [1.0]))
            else:
                div_indigestibilities = BeatQuantizationScheme.get_divisor_indigestibilities(length, divisors)
                self.quantization_divisions = list(zip(
                    divisors,
                    BeatQuantizationScheme.get_divisor_undesirabilities(div_indigestibilities, simplicity_preference)
                ))

    @classmethod
    def from_max_divisor(cls, length, max_divisor, simplicity_preference="default"):
        """
        Takes a max divisor argument instead of a list of allowed divisors.
        """
        return cls(length, range(2, max_divisor + 1), simplicity_preference)

    @classmethod
    def from_max_indigestibility(cls, length, max_divisor, max_indigestibility, simplicity_preference="default"):
        """
        Takes a max_divisor and max_indigestibility to get a determine the list of divisors.
        """
        if simplicity_preference == "default":
            simplicity_preference = quantization_settings.simplicity_preference

        # look at all possible divisors and the indigestibilities
        all_divisors = range(2, max_divisor + 1)
        all_indigestibilities = BeatQuantizationScheme.get_divisor_indigestibilities(length, all_divisors)

        # keep only those that fall below the max_indigestibility
        quantization_divisions = []
        div_indigestibilities = []
        for div, div_indigestibility in zip(all_divisors, all_indigestibilities):
            if div_indigestibility <= max_indigestibility:
                quantization_divisions.append(div)
                div_indigestibilities.append(div_indigestibility)

        return cls(length, list(zip(
            quantization_divisions,
            BeatQuantizationScheme.get_divisor_undesirabilities(div_indigestibilities, simplicity_preference)
        )))

    @staticmethod
    def get_divisor_indigestibilities(length, divisors):
        # What we care about is how well the given division works within the most natural division of the
        # length so first notate the length as a fraction; its numerator is its most natural division
        # Example: if length = 1.5, then length_fraction = 3/2
        # so for a divisor of 6, the relative division is 6/3, which Fraction automatically reduces to 2/1
        # on the other hand, a divisor of 2 has relative division 2/3, which is irreducible
        # thus the div_indigestibility for divisor 6 in this case is indigestibility(2) = 1
        # and the div_indigestibility for divisor 2 is indigestibility(2) + indigestibility(3) = 3.6667
        # this is appropriate for a beat of length 1.5 (compound meter)
        length_fraction = Fraction(length).limit_denominator()
        out = []
        for div in divisors:
            relative_division = Fraction(div, length_fraction.numerator)
            out.append(indigestibility(relative_division.numerator) + indigestibility(relative_division.denominator))
        return out

    @staticmethod
    def get_divisor_undesirabilities(divisor_indigestibilities, simplicity_preference):
        div_indigestibility_range = min(divisor_indigestibilities), max(divisor_indigestibilities)
        return [1 + simplicity_preference * (float(div) - div_indigestibility_range[0]) /
                (div_indigestibility_range[1] - div_indigestibility_range[0])
                for div in divisor_indigestibilities]

    def __str__(self):
        return "BeatQuantizationScheme({}, {})".format(
            self.length, [x[0] for x in sorted(self.quantization_divisions, key=lambda x: x[1])]
        )

    def __repr__(self):
        return "BeatQuantizationScheme(length={}, quantization_divisions={})".format(
            self.length, sorted(self.quantization_divisions)
        )


class TimeSignature(SavesToJSON):

    def __init__(self, numerator, denominator, beat_lengths=None):
        """
        Class representing a time signature
        :param numerator: self-explanatory
        :param denominator: self-explanatory
        :param beat_lengths: This is a hint as to how the time signature is divided up into beats. By default,
        it is None, meaning that a sensible default will be constructed.
        """
        self.numerator = numerator
        # For now, and the foreseeable future, I don't want to deal with time signatures like 4/7
        assert is_x_pow_of_y(denominator, 2)
        self.denominator = denominator
        self.beat_lengths = beat_lengths if beat_lengths is not None else self._calculate_default_beat_lengths()

    def _calculate_default_beat_lengths(self):
        if not hasattr(self.numerator, '__len__'):
            # not an additive meter
            if self.denominator <= 4 or is_multiple(self.numerator, 3):
                # if the denominator is 4 or less, we'll use the denominator as the beat
                # and if not, but the numerator is a multiple of 3, then we've got a compound meter
                if self.denominator > 4:
                    beat_length = 4.0 / self.denominator * 3
                else:
                    beat_length = 4.0 / self.denominator
                num_beats = int(round(self.measure_length() / beat_length))
                beat_lengths = [beat_length] * num_beats
            else:
                # if we're here then the denominator is >= 8 and the numerator is not a multiple of 3
                # so we'll do a bunch of duple beats followed by a triple beat if the numerator is odd
                duple_beat_length = 4.0 / self.denominator * 2
                triple_beat_length = 4.0 / self.denominator * 3

                if self.numerator % 2 == 0:
                    beat_lengths = [duple_beat_length] * (self.numerator // 2)
                else:
                    beat_lengths = [duple_beat_length] * (self.numerator // 2 - 1) + [triple_beat_length]
        else:
            # additive meter
            if self.denominator <= 4:
                # denominator is quarter note or slower, so treat each denominator value as a beat, ignoring groupings
                beat_lengths = [4.0 / self.denominator] * sum(self.numerator)
            else:
                # denominator is eighth or faster, so treat each grouping as a beat
                beat_lengths = [4.0 / self.denominator * x for x in self.numerator]
        return beat_lengths

    @classmethod
    def from_measure_length(cls, measure_length: Number):
        fraction_length = Fraction(measure_length)
        numerator, denominator = fraction_length.numerator, fraction_length.denominator * 4
        return cls(numerator, denominator)

    @classmethod
    def from_string(cls, time_signature_string):
        assert isinstance(time_signature_string, str) and len(time_signature_string.split("/")) == 2
        numerator_string, denominator_string = time_signature_string.split("/")
        numerator = tuple(int(x) for x in numerator_string.split("+")) \
            if "+" in numerator_string else int(numerator_string)
        denominator = int(denominator_string)
        return cls(numerator, denominator)

    def as_string(self):
        if hasattr(self.numerator, "__len__"):
            return "{}/{}".format("+".join(str(x) for x in self.numerator), self.denominator)
        else:
            return "{}/{}".format(self.numerator, self.denominator)

    def as_tuple(self):
        return self.numerator, self.denominator

    def measure_length(self):
        if hasattr(self.numerator, "__len__"):
            return 4 * sum(self.numerator) / self.denominator
        else:
            return 4 * self.numerator / self.denominator

    def to_json(self):
        return self.numerator, self.denominator

    @classmethod
    def from_json(cls, json_object):
        return cls(*json_object)

    def to_abjad(self):
        return abjad.TimeSignature((self.numerator, self.denominator))

    def __eq__(self, other):
        return self.numerator == other.numerator and self.denominator == other.denominator

    def __repr__(self):
        return "TimeSignature({}, {})".format(self.numerator, self.denominator)


class MeasureQuantizationScheme:

    def __init__(self, beat_schemes, time_signature):
        if isinstance(time_signature, str):
            time_signature = TimeSignature.from_string(time_signature)
        self.time_signature = time_signature
        self.length = time_signature.measure_length()
        # this better be true
        assert sum([beat_scheme.length for beat_scheme in beat_schemes]) == self.length
        self.beat_schemes = beat_schemes

    @classmethod
    def from_time_signature(cls, time_signature, max_divisor="default", max_indigestibility="default",
                            simplicity_preference="default"):
        # load default settings if not specified (the default simplicity_preference gets loaded
        # later in the constructor of BeatQuantizationScheme if nothing is specified here)
        if max_divisor == "default":
            max_divisor = quantization_settings.max_divisor
        if max_indigestibility == "default":
            max_indigestibility = quantization_settings.max_indigestibility

        # allow for different formulations of the time signature argument
        if isinstance(time_signature, str):
            time_signature = TimeSignature.from_string(time_signature)
        elif isinstance(time_signature, tuple):
            time_signature = TimeSignature(*time_signature)
        elif isinstance(time_signature, Number):
            time_signature = TimeSignature.from_measure_length(time_signature)

        assert isinstance(time_signature, TimeSignature)

        # now we convert the beat lengths to BeatQuantizationSchemes and construct our object
        if max_indigestibility is None:
            # no max_indigestibility, so just use the max divisor
            beat_schemes = [
                BeatQuantizationScheme.from_max_divisor(beat_length, max_divisor, simplicity_preference)
                for beat_length in time_signature.beat_lengths
            ]
        else:
            # using a max_indigestibility
            beat_schemes = [
                BeatQuantizationScheme.from_max_indigestibility(beat_length, max_divisor,
                                                                max_indigestibility, simplicity_preference)
                for beat_length in time_signature.beat_lengths
            ]
        return cls(beat_schemes, time_signature)

    def __str__(self):
        return "MeasureQuantizationScheme({})".format(self.time_signature.as_string())

    def __repr__(self):
        return "MeasureQuantizationScheme({}, {})".format(self.beat_schemes, self.time_signature)


class QuantizationScheme:

    def __init__(self, measure_schemes, loop=False):
        assert all(isinstance(x, MeasureQuantizationScheme) for x in measure_schemes)
        self.measure_schemes = measure_schemes
        self.loop = loop

    @classmethod
    def from_time_signature(cls, time_signature, max_divisor="default",
                            max_indigestibility="default", simplicity_preference="default"):
        return cls.from_time_signature_list(
            [time_signature], max_divisor=max_divisor, max_indigestibility=max_indigestibility,
            simplicity_preference=simplicity_preference
        )

    @classmethod
    def from_time_signature_list(cls, time_signatures_list, loop=False, max_divisor="default",
                                 max_indigestibility="default", simplicity_preference="default"):
        measure_schemes = []
        for time_signature in time_signatures_list:
            measure_schemes.append(
                MeasureQuantizationScheme.from_time_signature(time_signature, max_divisor=max_divisor,
                                                              max_indigestibility=max_indigestibility,
                                                              simplicity_preference=simplicity_preference)
            )
        return cls(measure_schemes, loop=loop)

    def measure_scheme_iterator(self):
        # iterates and returns tuples of (measure_scheme, start_time)
        t = 0
        while self.loop or t == 0:
            # if loop is True, then we repeatedly loop through the measure schemes array,
            # never reaching the second while loop
            for measure_scheme in self.measure_schemes:
                yield measure_scheme, t
                t += measure_scheme.length
        while True:
            # if loop is False, then we repeat the last measure scheme
            yield self.measure_schemes[-1], t
            t += self.measure_schemes[-1].length

    def beat_scheme_iterator(self):
        # iterates and returns tuples of (beat_scheme, start_time)
        for measure_scheme, t in self.measure_scheme_iterator():
            for beat_scheme in measure_scheme.beat_schemes:
                yield beat_scheme, t
                t += beat_scheme.length
