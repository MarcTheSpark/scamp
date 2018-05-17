from playcorder.performance import Performance, PerformancePart
from fractions import Fraction
from playcorder.utilities import indigestibility, is_multiple, is_x_pow_of_y
from collections import namedtuple


class QuantizedPerformancePart(PerformancePart):

    def __init__(self, performance_part, quantization_scheme):
        super().__init__(performance_part.instrument, performance_part.name,
                         performance_part.notes, performance_part.instrument_id)
        self.quantized_measures = self.quantize(quantization_scheme)

    def quantize(self, quantization_scheme):
        # TODO: THIS
        pass
        # # raw_onsets and raw_terminations are in seconds
        # raw_onsets = [(pc_note.start_time, pc_note) for pc_note in recording_in_seconds]
        # raw_terminations = [(pc_note.start_time + pc_note.length, pc_note) for pc_note in recording_in_seconds]
        # raw_onsets.sort(key=lambda x: x[0])
        # raw_terminations.sort(key=lambda x: x[0])
        #
        # pc_note_to_quantize_start_time = {}
        # pc_note_to_quantize_end_time = {}
        # current_beat_scheme = 0
        # quarters_beat_start_time = 0.0
        # seconds_beat_start_time = 0.0
        # beat_divisors = []
        # while len(raw_onsets) + len(raw_terminations) > 0:
        #     # move forward one beat at a time
        #     # get the beat scheme for this beat
        #     this_beat_scheme = beat_schemes[current_beat_scheme] if current_beat_scheme < len(beat_schemes) \
        #         else beat_schemes[-1]
        #     assert isinstance(this_beat_scheme, BeatQuantizationScheme)
        #     current_beat_scheme += 1
        #
        #     # get the beat length and end time in quarters and seconds
        #     quarters_beat_length = this_beat_scheme.length
        #     seconds_beat_length = this_beat_scheme.length * 60.0 / this_beat_scheme.tempo
        #     quarters_beat_end_time = quarters_beat_start_time + this_beat_scheme.length
        #     seconds_beat_end_time = seconds_beat_start_time + seconds_beat_length
        #
        #     # find the onsets in this beat
        #     onsets_to_quantize = []
        #     while len(raw_onsets) > 0 and raw_onsets[0][0] < seconds_beat_end_time:
        #         onsets_to_quantize.append(raw_onsets.pop(0))
        #
        #     # find the terminations in this beat
        #     terminations_to_quantize = []
        #     while len(raw_terminations) > 0 and raw_terminations[0][0] < seconds_beat_end_time:
        #         terminations_to_quantize.append(raw_terminations.pop(0))
        #
        #     if len(onsets_to_quantize) + len(terminations_to_quantize) == 0:
        #         # an empty beat, nothing to see here
        #         beat_divisors.append(None)
        #     else:
        #         # try out each quantization division
        #         best_divisor = None
        #         best_error = float("inf")
        #
        #         for divisor, undesirability in this_beat_scheme.quantization_divisions:
        #             seconds_piece_length = seconds_beat_length / divisor
        #             total_squared_onset_error = 0
        #             for onset in onsets_to_quantize:
        #                 time_since_beat_start = onset[0] - seconds_beat_start_time
        #                 total_squared_onset_error += (time_since_beat_start - round_to_multiple(time_since_beat_start,
        #                                                                                         seconds_piece_length)) ** 2
        #             total_squared_term_error = 0
        #             for term in terminations_to_quantize:
        #                 time_since_beat_start = term[0] - seconds_beat_start_time
        #                 total_squared_term_error += (time_since_beat_start - round_to_multiple(time_since_beat_start,
        #                                                                                        seconds_piece_length)) ** 2
        #             this_div_error_score = undesirability * (onset_termination_weighting * total_squared_term_error +
        #                                                      (
        #                                                              1 - onset_termination_weighting) * total_squared_onset_error)
        #             if this_div_error_score < best_error:
        #                 best_divisor = divisor
        #                 best_error = this_div_error_score
        #         best_piece_length_quarters = this_beat_scheme.length / best_divisor
        #         best_piece_length_seconds = seconds_beat_length / best_divisor
        #
        #         for onset, pc_note in onsets_to_quantize:
        #             pieces_past_beat_start = round((onset - seconds_beat_start_time) / best_piece_length_seconds)
        #             pc_note_to_quantize_start_time[
        #                 pc_note] = quarters_beat_start_time + pieces_past_beat_start * best_piece_length_quarters
        #             # save this info for later, when we need to assure they all have the same Tuplet
        #             pc_note.start_time_divisor = best_divisor
        #
        #         for termination, pc_note in terminations_to_quantize:
        #             pieces_past_beat_start = round((termination - seconds_beat_start_time) / best_piece_length_seconds)
        #             pc_note_to_quantize_end_time[
        #                 pc_note] = quarters_beat_start_time + pieces_past_beat_start * best_piece_length_quarters
        #             if pc_note_to_quantize_end_time[pc_note] == pc_note_to_quantize_start_time[pc_note]:
        #                 # if the quantization collapses the start and end times of a note to the same point, adjust the
        #                 # end time so the the note is a single piece_length long.
        #                 if pc_note_to_quantize_end_time[pc_note] + best_piece_length_quarters <= quarters_beat_end_time:
        #                     # unless both are quantized to the start of the next beat, just move the end one piece forward
        #                     pc_note_to_quantize_end_time[pc_note] += best_piece_length_quarters
        #                 else:
        #                     # if they're at the start of the next beat, move the start one piece back
        #                     pc_note_to_quantize_start_time[pc_note] -= best_piece_length_quarters
        #             # save this info for later, when we need to assure they all have the same Tuplet
        #             pc_note.end_time_divisor = best_divisor
        #
        #         beat_divisors.append(best_divisor)
        #
        #     quarters_beat_start_time += quarters_beat_length
        #     seconds_beat_start_time += seconds_beat_length
        #
        # quantized_recording = []
        # for pc_note in recording_in_seconds:
        #     quantized_recording.append(PCNote(start_time=pc_note_to_quantize_start_time[pc_note],
        #                                       length=pc_note_to_quantize_end_time[pc_note] -
        #                                              pc_note_to_quantize_start_time[pc_note],
        #                                       pitch=pc_note.pitch, volume=pc_note.volume, variant=pc_note.variant,
        #                                       tie=pc_note.tie))
        #
        # return quantized_recording, beat_divisors


class QuantizedPerformance(Performance):

    def __init__(self, performance, quantization_scheme):
        """
        Represents a quantized version of a performance that knows what measure schemes it was quantized to.
        This is the first step in outputting a readable score.
        :param performance: The unquantized performance it's based on
        :param measure_schemes: the measure quantization scheme(s) to use
        """
        super().__init__(performance.parts, performance.tempo_curve)
        self.quantize(quantization_scheme)

    def quantize(self, quantization_scheme):
        self.parts = [QuantizedPerformancePart(part, quantization_scheme) for part in self.parts]


QuantizedBeat = namedtuple("QuantizedBeat", "start_time beat_length end_time beat_length_without_tuplet divisor")


class BeatQuantizationScheme:

    def __init__(self, length, divisors, simplicity_preference=1.5):
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
    def from_max_divisor(cls, length, max_divisor, simplicity_preference=2.0):
        """
        Takes a max divisor argument instead of a list of allowed divisors.
        """
        return cls(length, range(2, max_divisor + 1), simplicity_preference)

    @classmethod
    def from_max_indigestibility(cls, length, max_divisor, max_indigestibility, simplicity_preference=1.5):
        """
        Takes a max_divisor and max_indigestibility to get a determine the list of divisors.
        """
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


class TimeSignature:

    def __init__(self, numerator, denominator):
        self.numerator = numerator
        # For now, and the foreseeable future, I don't want to deal with time signatures like 4/7
        assert is_x_pow_of_y(denominator, 2)
        self.denominator = denominator

    @classmethod
    def from_string(cls, time_signature_string):
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

    def __repr__(self):
        return "TimeSignature({}, {})".format(self.numerator, self.denominator)


QuantizedMeasure = namedtuple("QuantizedMeasure", "beat_schemes time_signature measure_length start_time end_time")


class MeasureQuantizationScheme:

    def __init__(self, beat_schemes, time_signature: TimeSignature):
        if isinstance(time_signature, str):
            time_signature = TimeSignature.from_string(time_signature)
        self.time_signature = time_signature
        self.length = time_signature.measure_length()
        # this better be true
        assert sum([beat_scheme.length for beat_scheme in beat_schemes]) == self.length
        self.beat_schemes = beat_schemes

    @classmethod
    def from_time_signature(cls, time_signature: TimeSignature, max_divisor=8,
                            max_indigestibility=None, simplicity_preference=2.0):
        # allow for different formulations of the time signature argument
        if isinstance(time_signature, str):
            time_signature = TimeSignature.from_string(time_signature)
        elif isinstance(time_signature, tuple):
            time_signature = TimeSignature(*time_signature)

        measure_length = time_signature.measure_length()

        # first we make a list of the beat lengths based on the time signature
        if not hasattr(time_signature.numerator, '__len__'):
            # not an additive meter
            if time_signature.denominator <= 4 or is_multiple(time_signature.numerator, 3):
                # if the denominator is 4 or less, we'll use the denominator as the beat
                # and if not, but the numerator is a multiple of 3, then we've got a compound meter
                if time_signature.denominator > 4:
                    beat_length = 4.0 / time_signature.denominator * 3
                else:
                    beat_length = 4.0 / time_signature.denominator
                num_beats = int(round(measure_length/beat_length))
                beat_lengths = [beat_length] * num_beats
            else:
                # if we're here then the denominator is >= 8 and the numerator is not a multiple of 3
                # so we'll do a bunch of duple beats followed by a triple beat if the numerator is odd
                duple_beat_length = 4.0 / time_signature.denominator * 2
                triple_beat_length = 4.0 / time_signature.denominator * 3

                if time_signature.numerator % 2 == 0:
                    beat_lengths = [duple_beat_length] * (time_signature.numerator // 2)
                else:
                    beat_lengths = [duple_beat_length] * (time_signature.numerator // 2 - 1) + [triple_beat_length]
        else:
            # additive meter
            if time_signature.denominator <= 4:
                # denominator is quarter note or slower, so treat each denominator value as a beat, ignoring groupings
                beat_lengths = [4.0 / time_signature.denominator] * sum(time_signature.numerator)
            else:
                # denominator is eighth or faster, so treat each grouping as a beat
                beat_lengths = [4.0 / time_signature.denominator * x for x in time_signature.numerator]

        # now we convert the beat lengths to BeatQuantizationSchemes and construct our object
        if max_indigestibility is None:
            # no max_indigestibility, so just use the max divisor
            beat_schemes = [
                BeatQuantizationScheme.from_max_divisor(beat_length, max_divisor, simplicity_preference)
                for beat_length in beat_lengths
            ]
        else:
            # using a max_indigestibility
            beat_schemes = [
                BeatQuantizationScheme.from_max_indigestibility(beat_length, max_divisor,
                                                                max_indigestibility, simplicity_preference)
                for beat_length in beat_lengths
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
