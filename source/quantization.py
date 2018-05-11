from .performance import Performance
from fractions import Fraction
from .utilities import indigestibility, is_multiple, is_x_pow_of_y
from collections import namedtuple


class QuantizedPerformance(Performance):

    def __init__(self, performance, quantization_scheme):
        """
        Represents a quantized version of a performance that knows what measure schemes it was quantized to.
        This is the first step in outputting a readable score.
        :param performance: The unquantized performance it's based on
        :param quantization_scheme: the quantization scheme to use
        """
        super().__init__(performance.parts, performance.tempo_curve)
        self.measure_schemes = measure_schemes
        self.quantize()

    def quantize(self):
        pass


QuantizedBeat = namedtuple("QuantizedBeat", "start_time beat_length end_time beat_length_without_tuplet divisor")


class BeatQuantizationScheme:

    def __init__(self, beat_length, divisors, simplicity_preference=1.5):
        """
        A scheme for making a decision about which divisor to use to quantize a beat
        :param beat_length: In quarter-notes
        :param divisors: A list of allowed divisors or a list of tuples of (divisor, undesirability). If just
        divisors are given, the undesirability for wach will be calculated based on its indigestibility.
        :param simplicity_preference: ranges 0 - whatever. A simplicity_preference of 0 means, all divisions are
        treated equally; a 7 is as good as a 4. A simplicity_preference of 1 means that the most desirable division
        is left alone, the most undesirable division gets its error doubled, and all other divisions are somewhere in
        between. Simplicity preference can be greater than 1, in which case the least desirable division gets its
        error multiplied by (simplicity_preference + 1)
        """
        # actual length of the beat
        self.beat_length = float(beat_length)
        self.beat_length_as_fraction = Fraction(beat_length).limit_denominator()

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
                div_indigestibilities = BeatQuantizationScheme.get_divisor_indigestibilities(beat_length, divisors)
                self.quantization_divisions = list(zip(
                    divisors,
                    BeatQuantizationScheme.get_divisor_undesirabilities(div_indigestibilities, simplicity_preference)
                ))

    @classmethod
    def from_max_divisor(cls, beat_length, max_divisor, simplicity_preference=2.0):
        """
        Takes a max divisor argument instead of a list of allowed divisors.
        """
        return cls(beat_length, range(2, max_divisor + 1), simplicity_preference)

    @classmethod
    def from_max_indigestibility(cls, beat_length, max_divisor, max_indigestibility, simplicity_preference=1.5):
        """
        Takes a max_divisor and max_indigestibility to get a determine the list of divisors.
        """
        # look at all possible divisors and the indigestibilities
        all_divisors = range(2, max_divisor + 1)
        all_indigestibilities = BeatQuantizationScheme.get_divisor_indigestibilities(beat_length, all_divisors)

        # keep only those that fall below the max_indigestibility
        quantization_divisions = []
        div_indigestibilities = []
        for div, div_indigestibility in zip(all_divisors, all_indigestibilities):
            if div_indigestibility <= max_indigestibility:
                quantization_divisions.append(div)
                div_indigestibilities.append(div_indigestibility)

        return cls(beat_length, list(zip(
            quantization_divisions,
            BeatQuantizationScheme.get_divisor_undesirabilities(div_indigestibilities, simplicity_preference)
        )))

    @staticmethod
    def get_divisor_indigestibilities(beat_length, divisors):
        # What we care about is how well the given division works within the most natural division of the
        # beat_length so first notate the beat_length as a fraction; its numerator is its most natural division
        # Example: if beat_length = 1.5, then beat_length_fraction = 3/2
        # so for a divisor of 6, the relative division is 6/3, which Fraction automatically reduces to 2/1
        # on the other hand, a divisor of 2 has relative division 2/3, which is irreducible
        # thus the div_indigestibility for divisor 6 in this case is indigestibility(2) = 1
        # and the div_indigestibility for divisor 2 is indigestibility(2) + indigestibility(3) = 3.6667
        # this is appropriate for a beat of length 1.5 (compound meter)
        beat_length_fraction = Fraction(beat_length).limit_denominator()
        out = []
        for div in divisors:
            relative_division = Fraction(div, beat_length_fraction.numerator)
            out.append(indigestibility(relative_division.numerator) + indigestibility(relative_division.denominator))
        return out

    @staticmethod
    def get_divisor_undesirabilities(divisor_indigestibilities, simplicity_preference):
        div_indigestibility_range = min(divisor_indigestibilities), max(divisor_indigestibilities)
        return [1 + simplicity_preference * (float(div) - div_indigestibility_range[0]) /
                (div_indigestibility_range[1] - div_indigestibility_range[0])
                for div in divisor_indigestibilities]

    def __repr__(self):
        return "BeatQuantizationScheme(beat_length={}, quantization_divisions={})".format(
            self.beat_length, self.quantization_divisions
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


class MeasureScheme:

    def __init__(self, beat_quantization_schemes, time_signature: TimeSignature):
        if isinstance(time_signature, str):
            time_signature = TimeSignature.from_string(time_signature)
        self.time_signature = time_signature
        self.measure_length = time_signature.measure_length()
        # this better be true
        assert sum([beat_scheme.beat_length for beat_scheme in beat_quantization_schemes]) == self.measure_length
        self.beat_quantization_schemes = beat_quantization_schemes

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