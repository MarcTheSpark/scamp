"""
Module containing classes and functions related to the quantization of performances. (This includes the
:class:`TimeSignature` class, which also has bearing on musical notation.)
"""

#  ++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++  #
#  This file is part of SCAMP (Suite for Computer-Assisted Music in Python)                      #
#  Copyright © 2020 Marc Evanstein <marc@marcevanstein.com>.                                     #
#                                                                                                #
#  This program is free software: you can redistribute it and/or modify it under the terms of    #
#  the GNU General Public License as published by the Free Software Foundation, either version   #
#  3 of the License, or (at your option) any later version.                                      #
#                                                                                                #
#  This program is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY;     #
#  without even the implied warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.     #
#  See the GNU General Public License for more details.                                          #
#                                                                                                #
#  You should have received a copy of the GNU General Public License along with this program.    #
#  If not, see <http://www.gnu.org/licenses/>.                                                   #
#  ++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++  #

from fractions import Fraction
from .utilities import indigestibility, is_multiple, is_x_pow_of_y, round_to_multiple, sum_nested_list, prime_factor, \
    SavesToJSON, memoize
from ._metric_structure import MetricStructure
from collections import namedtuple
from .settings import quantization_settings, engraving_settings
from expenvelope import Envelope
from ._dependencies import abjad
from numbers import Number
from typing import Sequence, Union, Tuple, Iterator
import textwrap


##################################################################################################################
#                                             TimeSignature Class
##################################################################################################################


class TimeSignature(SavesToJSON):
    """
    Class representing the time signature of a measure

    :param numerator: time signature numerator. Can be a list/tuple of ints, in the case of an additive time signature
    :param denominator: time signature denominator
    :param beat_lengths: (optional) This is a hint as to how the time signature is divided up into beats. By default,
        it is None, meaning that a sensible default will be constructed. Should add up to the length of the time
        signature.
    :ivar numerator: time signature numerator. Can be a list/tuple of ints, in the case of an additive time signature
    :ivar denominator: time signature denominator
    :ivar beat_lengths: Representation of how the time signature is divided up into beats. (Affects the quantization
        process.)
    """

    def __init__(self, numerator: Union[int, Sequence[int]], denominator: int, beat_lengths: Sequence[float] = None):

        self.numerator = numerator
        # For now, and the foreseeable future, I don't want to deal with time signatures like 4/7
        if not is_x_pow_of_y(denominator, 2):
            raise ValueError("TimeSignature denominator must be a power of two.")
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

                if self.numerator == 1:
                    # covers the weird cases of 1/8 or 1/16 and such
                    beat_lengths = [4.0 / self.denominator]
                elif self.numerator % 2 == 0:
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
    def from_measure_length(cls, measure_length: float) -> 'TimeSignature':
        """
        Constructs a TimeSignature of the appropriate measure length.
        (Defaults to the simple rather than compound)

        :param measure_length: length of the measure in quarter notes
        :return: the TimeSignature so constructed
        """
        fraction_length = Fraction(measure_length)
        numerator, denominator = fraction_length.numerator, fraction_length.denominator * 4
        return cls(numerator, denominator)

    @classmethod
    def from_string(cls, time_signature_string: str):
        """
        Constructs a TimeSignature from its string representation

        :param time_signature_string: e.g. "7/8", or "3+5+2/8" in the case of a compound time signature
        :return: the TimeSignature so constructed
        """
        assert isinstance(time_signature_string, str) and len(time_signature_string.split("/")) == 2
        numerator_string, denominator_string = time_signature_string.split("/")
        numerator = tuple(int(x) for x in numerator_string.split("+")) \
            if "+" in numerator_string else int(numerator_string)
        denominator = int(denominator_string)
        return cls(numerator, denominator)

    def as_string(self) -> str:
        """
        Returns a string representation of the time signature, e.g. "5/4" or "3+2+1/8"
        """
        if hasattr(self.numerator, "__len__"):
            return "{}/{}".format("+".join(str(x) for x in self.numerator), self.denominator)
        else:
            return "{}/{}".format(self.numerator, self.denominator)

    def as_tuple(self) -> Tuple:
        """
        Returns a tuple representation of the time signature, e.g. (5, 4) or ((3, 2, 1), 8)
        """
        return self.numerator, self.denominator

    def measure_length(self) -> float:
        """
        Get the length of the measure in quarter notes
        """
        if hasattr(self.numerator, "__len__"):
            return 4 * sum(self.numerator) / self.denominator
        else:
            return 4 * self.numerator / self.denominator

    def _to_dict(self):
        return {
            "numerator": self.numerator,
            "denominator": self.denominator
        }

    @classmethod
    def _from_dict(cls, json_dict):
        return cls(**json_dict)

    def to_abjad(self) -> 'abjad().TimeSignature':
        """
        Returns the abjad version of this time signature
        """
        return abjad().TimeSignature((self.numerator, self.denominator))

    def __eq__(self, other):
        return self.numerator == other.numerator and self.denominator == other.denominator

    def __repr__(self):
        return "TimeSignature({}, {})".format(self.numerator, self.denominator)


##################################################################################################################
#                                             Quantization Schemes
##################################################################################################################


class BeatQuantizationScheme:
    """
    Scheme for making a decision about which divisor to use to quantize a beat

    :param length: In quarter-notes
    :param divisors: A list of allowed divisors or a list of tuples of (divisor, undesirability). If just
        divisors are given, the undesirability for each will be calculated based on its indigestibility.
    :param simplicity_preference: ranges 0 - whatever. A simplicity_preference of 0 means all divisions are
        treated equally; a 7 is as good as a 4. A simplicity_preference of 1 means that the error for a given
        divisor is weighted by that divisor's indigestibility, and a simplicity_preference of 2 means the error
        is weighted by the indigestibility squared, etc.
    """

    def __init__(self, length: float, divisors: Sequence, simplicity_preference: float = "default"):

        # load default if not specified
        if simplicity_preference == "default":
            simplicity_preference = quantization_settings.simplicity_preference

        # actual length of the beat
        self.length = float(length)
        self.length_as_fraction = Fraction(length).limit_denominator()
        assert is_x_pow_of_y(self.length_as_fraction.denominator, 2), \
            "Beat length must be some multiple of a power of 2 division of the bar."

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
                div_indigestibilities = BeatQuantizationScheme._get_divisor_indigestibilities(length, divisors)
                self.quantization_divisions = list(zip(
                    divisors,
                    BeatQuantizationScheme._get_divisor_undesirabilities(div_indigestibilities, simplicity_preference)
                ))

    @classmethod
    def from_max_divisor(cls, length: float, max_divisor: int,
                         simplicity_preference: float = "default") -> 'BeatQuantizationScheme':
        """
        Takes a max divisor argument instead of a list of allowed divisors.

        :param length: In quarter-notes
        :param max_divisor: The largest allowable divisor
        :param simplicity_preference: Preference for simple divisors (see class description)
        """
        return cls(length, range(2, max_divisor + 1), simplicity_preference)

    @classmethod
    def from_max_divisor_indigestibility(cls, length: float, max_divisor: int, max_divisor_indigestibility: float,
                                         simplicity_preference: float = "default") -> 'BeatQuantizationScheme':
        """
        Takes a max_divisor and max_divisor_indigestibility to determine the list of divisors.

        :param length: In quarter-notes
        :param max_divisor: The largest allowable divisor
        :param max_divisor_indigestibility: sets a hard limit on the indigestibility of divisors that we will consider,
            in contrast to simplicity_preference, which simply penalizes indigestible divisors. (See Clarence Barlow's
            writing on indigestibility.)
        :param simplicity_preference: Preference for simple divisors (see class description)
        """
        if simplicity_preference == "default":
            simplicity_preference = quantization_settings.simplicity_preference

        # look at all possible divisors and the indigestibilities
        all_divisors = range(2, max_divisor + 1)
        all_indigestibilities = BeatQuantizationScheme._get_divisor_indigestibilities(length, all_divisors)

        # keep only those that fall below the max_divisor_indigestibility
        quantization_divisions = []
        div_indigestibilities = []
        for div, div_indigestibility in zip(all_divisors, all_indigestibilities):
            if div_indigestibility <= max_divisor_indigestibility:
                quantization_divisions.append(div)
                div_indigestibilities.append(div_indigestibility)

        return cls(length, list(zip(
            quantization_divisions,
            BeatQuantizationScheme._get_divisor_undesirabilities(div_indigestibilities, simplicity_preference)
        )))

    @staticmethod
    def _get_divisor_indigestibilities(length: float, divisors: Sequence[int]) -> Sequence[float]:
        """
        Returns the indigestibilities for a given set of divisors of a given length, taking into account how those
        lengths would most naturally divide.

        If we write a length as a fraction in simplest terms, its numerator is its most natural division. For instance,
        a beat of length 1.5 would be written as a fraction as 3/2, and 3 is the most natural divisor. To get the
        indigestibility we consider the indigestibility that results when we divide a given divisor by that numerator
        and pull out any common factors.

        Example: if length = 1.5, then length_fraction = 3/2. So for a divisor of 6, the relative division is 6/3,
        which Fraction automatically reduces to 2/1. On the other hand, a divisor of 2 has relative division 2/3,
        which is irreducible thus the div_indigestibility for divisor 6 in this case is indigestibility(2) = 1
        and the div_indigestibility for divisor 2 is indigestibility(2) + indigestibility(3) = 3.6667. This is
        appropriate for a beat of length 1.5 (compound meter).

        Note that there's a little issue here with the divisor of 3, since 3/3 = 1, which has indigestibility 0
        Ultimately this would lead to that divisor being chosen no matter what, which is not good. To avoid this
        eventuality, when the length fraction numerator is not 1, we add one to all of the divisor indigestibilities
        to avoid zeroing things out.

        :param length: length of the beat we are looking to divide
        :param divisors: list of divisors we are considering for this beat
        :return: list of relative indigestibilities corresponding to each divisor
        """

        length_fraction = Fraction(length).limit_denominator()
        out = []
        for div in divisors:
            relative_division = Fraction(div, length_fraction.numerator)
            divisor_indigestibility = indigestibility(relative_division.numerator) + \
                                      indigestibility(relative_division.denominator)

            # ensures not zeroing out of indigestibility as described in the docstring
            if length_fraction.numerator > 1:
                divisor_indigestibility += 1

            out.append(divisor_indigestibility)
        return out

    @staticmethod
    def _get_divisor_undesirabilities(divisor_indigestibilities, simplicity_preference):
        return [div ** simplicity_preference for div in divisor_indigestibilities]

    def __str__(self):
        return "BeatQuantizationScheme({}, {})".format(
            self.length, [x[0] for x in sorted(self.quantization_divisions, key=lambda x: x[1])]
        )

    def __repr__(self):
        return "BeatQuantizationScheme(length={}, quantization_divisions={})".format(
            self.length, sorted(self.quantization_divisions)
        )


class MeasureQuantizationScheme:
    """
    Scheme for quantizing a measure, including beat lengths and which beat divisors to allow.

    :param beat_schemes: list of BeatQuantizationSchemes for each beat in the measure
    :param time_signature: a TimeSignature or string representing a time signature for this measure
    :param beat_groupings: a (potentially nested) list/tuple representing how beats come together to form larger
        groupings. For instance, in 4/4 time the beat_groupings will default to (2, 2).
    """

    def __init__(self, beat_schemes: Sequence[BeatQuantizationScheme], time_signature: Union[TimeSignature, str],
                 beat_groupings: Sequence = "auto"):

        if isinstance(time_signature, str):
            time_signature = TimeSignature.from_string(time_signature)
        self.time_signature = time_signature
        self.length = time_signature.measure_length()
        # this better be true
        assert sum([beat_scheme.length for beat_scheme in beat_schemes]) == self.length
        self.beat_schemes = beat_schemes
        if beat_groupings == "auto":
            self.beat_groupings = self._generate_default_beat_groupings()
        else:
            if sum_nested_list(beat_groupings) != len(beat_schemes):
                raise ValueError("Wrong number of beats in beat groupings.")
            self.beat_groupings = MetricStructure(*beat_groupings)

    @classmethod
    def from_time_signature(cls, time_signature: Union[TimeSignature, str, float], max_divisor: int = "default",
                            max_divisor_indigestibility: float = "default",
                            simplicity_preference: float = "default") -> 'MeasureQuantizationScheme':
        """
        Constructs a MeasureQuantizationScheme from a time signature.
        All beats will follow the same quantization scheme, as dictated by the parameters.

        :param time_signature: Either a TimeSignature object or something that can be interpreted as such (e.g. a
            string to parse as a time signature, a measure length)
        :param max_divisor: the max divisor for all beats in the is measure (see :class:`BeatQuantizationScheme`)
        :param max_divisor_indigestibility: the max indigestibility for all beats in the is measure
            (see :class:`BeatQuantizationScheme`)
        :param simplicity_preference: the simplicity preference for all beats in the is measure
            (see :class:`BeatQuantizationScheme`)
        """
        # load default settings if not specified (the default simplicity_preference gets loaded
        # later in the constructor of BeatQuantizationScheme if nothing is specified here)
        if max_divisor == "default":
            max_divisor = quantization_settings.max_divisor
        if max_divisor_indigestibility == "default":
            max_divisor_indigestibility = quantization_settings.max_divisor_indigestibility

        # allow for different formulations of the time signature argument
        if isinstance(time_signature, str):
            time_signature = TimeSignature.from_string(time_signature)
        elif isinstance(time_signature, tuple):
            time_signature = TimeSignature(*time_signature)
        elif isinstance(time_signature, Number):
            time_signature = TimeSignature.from_measure_length(time_signature)

        assert isinstance(time_signature, TimeSignature)

        # now we convert the beat lengths to BeatQuantizationSchemes and construct our object
        if max_divisor_indigestibility is None:
            # no max_divisor_indigestibility, so just use the max divisor
            beat_schemes = [
                BeatQuantizationScheme.from_max_divisor(beat_length, max_divisor, simplicity_preference)
                for beat_length in time_signature.beat_lengths
            ]
        else:
            # using a max_divisor_indigestibility
            beat_schemes = [
                BeatQuantizationScheme.from_max_divisor_indigestibility(
                    beat_length, max_divisor, max_divisor_indigestibility, simplicity_preference)
                for beat_length in time_signature.beat_lengths
            ]
        return cls(beat_schemes, time_signature)

    def _generate_default_beat_groupings(self):
        # break it into groups of beats of the same length
        last_beat_length = self.beat_schemes[0].length
        groups = []
        current_group_length = 1
        for beat_scheme in self.beat_schemes[1:]:
            if beat_scheme.length == last_beat_length:
                current_group_length += 1
            else:
                groups.append(current_group_length)
                current_group_length = 1
                last_beat_length = beat_scheme.length
        groups.append(current_group_length)

        # for each group make a metric layer out of the prime-factored length, breaking up large primes
        # (also, it's possible for a group to be one beat long, in which case it has empty prime factors. In this
        # case, we just need to use a MetricStructure(1)
        return MetricStructure(*(
            MetricStructure.from_string("*".join(str(x) for x in sorted(prime_factor(group))), True)
            if group != 1 else MetricStructure(1)
            for group in groups
        ))

    @memoize
    def get_beat_hierarchies(self, subdivision_length: float) -> Sequence[int]:
        """
        Generates a list of hierarchies representing how nested a subdivision is within the metric structure.
        For instance, if called on a 4/4 measure, with subdivision_length, 0.5, this will return the list
        [0, 3, 2, 3, 1, 3, 2, 3], showing that the first subdivision (downbeat) is the strongest, the 5th (3rd beat)
        is one level down, etc.

        :param subdivision_length: length (in quarter notes) of the subdivision
        """
        if not is_x_pow_of_y(subdivision_length, 2):
            raise ValueError("Bad subdivision length.")
        beat_metric_layers = [
            MeasureQuantizationScheme._get_beat_metric_layer(beat_scheme.length, subdivision_length)
            for beat_scheme in self.beat_schemes
        ]
        return MeasureQuantizationScheme._inscribe_beats(self.beat_groupings, beat_metric_layers).get_beat_depths()

    @staticmethod
    def _get_beat_metric_layer(beat_length, subdivision_length):
        if not is_multiple(beat_length, subdivision_length):
            raise ValueError("Subdivision length does not neatly subdivide beat.")
        beat_divisor = int(round(beat_length / subdivision_length))

        # first, get the divisor prime factors
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

        return MetricStructure.from_string("*".join(str(x) for x in divisor_factors), True)

    @staticmethod
    def _inscribe_beats(beat_structure: MetricStructure, beat_metric_layers):
        """
        Takes a MetricStructure representing the beat structure, and a list of MetricLayers representing the interior
        structure of each beat in order, and returns the MetricStructure that combines these two, inscribing the beat
        structures into the outer MetricStructure that represents the beat organization.

        :param beat_structure: MetricStructure representing the beat structure; each leaf is a beat
        :param beat_metric_layers: list of MetricLayers representing how each beat is subdivided
        :return: full structure of the measure as a MetricStructure
        """
        if len(beat_metric_layers) != beat_structure.num_pulses():
            raise ValueError("Wrong number of beat metric layers to inscribe.")
        new_groups = []
        for group in beat_structure.groups:
            if isinstance(group, int):
                new_groups.append(MetricStructure(*beat_metric_layers[:group]))
                beat_metric_layers = beat_metric_layers[group:]
            elif isinstance(group, MetricStructure):
                pulses_in_group = group.num_pulses()
                new_groups.append(
                    MeasureQuantizationScheme._inscribe_beats(group, beat_metric_layers[:pulses_in_group]))
                beat_metric_layers = beat_metric_layers[pulses_in_group:]
            else:
                raise ValueError("Bad group.")
        return MetricStructure(*new_groups)

    def __str__(self):
        return "MeasureQuantizationScheme({})".format(self.time_signature.as_string())

    def __repr__(self):
        return "MeasureQuantizationScheme({}, {})".format(self.beat_schemes, self.time_signature)


class QuantizationScheme:
    """
    Scheme for quantizing a :class:`~scamp.performance.PerformancePart` or :class:`~scamp.performance.Performance`

    :param measure_schemes: list of MeasureQuantizationSchemes to use
    :param loop: if True, loops through the list of MeasureQuantizationSchemes; if False, keeps reusing the last
        MeasureQuantizationScheme given after it reaches the end of the list
    """

    def __init__(self, measure_schemes: Sequence[MeasureQuantizationScheme], loop: bool = False):
        assert all(isinstance(x, MeasureQuantizationScheme) for x in measure_schemes)
        self.measure_schemes = measure_schemes
        self.loop = loop

    @classmethod
    def from_attributes(cls, time_signature: Union[str, TimeSignature, Sequence] = None,
                        bar_line_locations: Sequence[float] = None, max_divisor: int = None,
                        max_divisor_indigestibility: float = None,
                        simplicity_preference: float = None) -> 'QuantizationScheme':
        """
        Constructs a QuantizationScheme from some key attributes.

        :param time_signature: either a time signature (represented in string form or as a :class:`TimeSignature`
            object), or a list of time signatures. If a list, and the last element of that list is the string "loop",
            then the list is repeatedly looped through; if not, the last time signature specified continues to be used.
        :param bar_line_locations: a list of locations (in beats since the start of the performance) at which to place
            bar lines. Use either this parameter or the time_signature parameter, but not both.
        :param max_divisor: the max divisor for all beats in the is measure (see :class:`BeatQuantizationScheme`)
        :param max_divisor_indigestibility: the max indigestibility for all beats in the is measure
            (see :class:`BeatQuantizationScheme`)
        :param simplicity_preference: the simplicity preference for all beats in the is measure
            (see :class:`BeatQuantizationScheme`)
        """
        if bar_line_locations is not None:
            if time_signature is not None:
                raise AttributeError("Either time_signature or bar_line_locations may be defined, but not both.")
            else:
                # since time_signature can be a list of bar lengths, we just convert bar_line_locations to lengths
                time_signature = [bar_line_locations[0]] + [bar_line_locations[i+1] - bar_line_locations[i]
                                                            for i in range(len(bar_line_locations) - 1)]
        elif time_signature is None:
            # if both bar_line_locations and time_signature are none, the time signature should be the settings default
            time_signature = quantization_settings.default_time_signature

        max_divisor = max_divisor if max_divisor is not None else "default"
        max_divisor_indigestibility = max_divisor_indigestibility \
            if max_divisor_indigestibility is not None else "default"
        simplicity_preference = simplicity_preference if simplicity_preference is not None else "default"

        if isinstance(time_signature, Sequence) and not isinstance(time_signature, str):
            time_signature = list(time_signature)
            # make it easy to loop a series of time signatures by adding the string "loop" at the end
            loop = False
            if isinstance(time_signature[-1], str) and time_signature[-1].lower() == "loop":
                time_signature.pop()
                loop = True
            quantization_scheme = QuantizationScheme.from_time_signature_list(
                time_signature, max_divisor=max_divisor, max_divisor_indigestibility=max_divisor_indigestibility,
                simplicity_preference=simplicity_preference, loop=loop)
        else:
            quantization_scheme = QuantizationScheme.from_time_signature(
                time_signature, max_divisor=max_divisor, max_divisor_indigestibility=max_divisor_indigestibility,
                simplicity_preference=simplicity_preference)
        return quantization_scheme

    @classmethod
    def from_time_signature(cls, time_signature: Union[str, TimeSignature], max_divisor: int = "default",
                            max_divisor_indigestibility: float = "default",
                            simplicity_preference: float = "default") -> 'QuantizationScheme':
        """
        Constructs a QuantizationScheme using a single time signature for the whole piece.

        :param time_signature: the time signature to use (represented in string form or as a :class:`TimeSignature`
            object)
        :param max_divisor: the max divisor for all beats in the is measure (see :class:`BeatQuantizationScheme`)
        :param max_divisor_indigestibility: the max indigestibility for all beats in the is measure
            (see :class:`BeatQuantizationScheme`)
        :param simplicity_preference: the simplicity preference for all beats in the is measure
            (see :class:`BeatQuantizationScheme`)
        """
        return cls.from_time_signature_list(
            [time_signature], max_divisor=max_divisor, max_divisor_indigestibility=max_divisor_indigestibility,
            simplicity_preference=simplicity_preference
        )

    @classmethod
    def from_time_signature_list(cls, time_signatures_list: Sequence, loop: bool = False, max_divisor: int = "default",
                                 max_divisor_indigestibility: float = "default",
                                 simplicity_preference: float = "default") -> 'QuantizationScheme':
        """
        Constructs a QuantizationScheme using a list of time signatures

        :param time_signatures_list: list of time signatures to use (represented in string form or as
            :class:`TimeSignature` objects)
        :param loop: if True, then the list of time signatures is repeatedly looped through; if not, the last time
            signature specified continues to be used.
        :param max_divisor: the max divisor for all beats in the is measure (see :class:`BeatQuantizationScheme`)
        :param max_divisor_indigestibility: the max indigestibility for all beats in the is measure
            (see :class:`BeatQuantizationScheme`)
        :param simplicity_preference: the simplicity preference for all beats in the is measure
            (see :class:`BeatQuantizationScheme`)
        """
        measure_schemes = []
        for time_signature in time_signatures_list:
            measure_schemes.append(
                MeasureQuantizationScheme.from_time_signature(time_signature, max_divisor=max_divisor,
                                                              max_divisor_indigestibility=max_divisor_indigestibility,
                                                              simplicity_preference=simplicity_preference)
            )
        return cls(measure_schemes, loop=loop)

    def measure_scheme_iterator(self) -> Iterator[Tuple[MeasureQuantizationScheme, float]]:
        """
        Iterates through the measures of this QuantizationScheme, returning tuples of (measure_scheme, start_beat)
        """
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

    def beat_scheme_iterator(self) -> Iterator[Tuple[BeatQuantizationScheme, float]]:
        """
        Iterates through the beats of this QuantizationScheme, returning tuples of (beat_scheme, start_beat)
        """
        for measure_scheme, t in self.measure_scheme_iterator():
            for beat_scheme in measure_scheme.beat_schemes:
                yield beat_scheme, t
                t += beat_scheme.length


##################################################################################################################
#                                             Quantization Records
##################################################################################################################


QuantizedBeat = namedtuple("QuantizedBeat", "start_beat start_beat_in_measure length divisor")
QuantizedBeat.__doc__ = """Record of how a beat was quantized (named tuple)

:param start_beat: the start beat of the note relative to the whole performance
:param start_beat_in_measure: the start beat of the note relative to the start of the measure
:param length: the length of the beat in quarter notes
:param divisor: the divisor chosen for the beat
"""

QuantizedMeasure = namedtuple("QuantizedMeasure", "start_beat measure_length beats time_signature beat_depths")
QuantizedMeasure.__doc__ = """Record of how a measure was quantized (named tuple).

:param start_beat: the start beat of the measure relative to the whole performance
:param measure_length: the start beat of the note relative to the start of the measure
:param beats: a list of QuantizedBeat objects
:param time_signature: the :class:`TimeSignature` used for this measure
:param beat_depths: tuple of (length of minimum duple subdivision, list of integers representing the nestedness of each
    subdivision).
"""


class QuantizationRecord(SavesToJSON):
    """
    Record of how a :class:`~scamp.performance.PerformancePart` was quantized.

    :param quantized_measures: list of quantized measures
    :ivar quantized_measures: list of quantized measures
    :type quantized_measures: Sequence[QuantizedMeasure]
    """

    def __init__(self, quantized_measures: Sequence[QuantizedMeasure]):
        self.quantized_measures = quantized_measures

    def _to_dict(self):
        out = {"quantized_measures": []}
        quantized_measures_json_friendly = out["quantized_measures"]
        for quantized_measure in self.quantized_measures:
            quantized_measure_as_dict = quantized_measure._asdict()
            quantized_beats_as_dicts = [beat._asdict() for beat in quantized_measure.beats]
            quantized_measure_as_dict["beats"] = quantized_beats_as_dicts
            quantized_measures_json_friendly.append(quantized_measure_as_dict)
        return out

    @classmethod
    def _from_dict(cls, json_dict):
        quantized_measures = []
        for quantized_measure_as_dict in json_dict["quantized_measures"]:
            quantized_measure_as_dict["beats"] = [
                QuantizedBeat(**quantized_beat_as_dict) for quantized_beat_as_dict in quantized_measure_as_dict["beats"]
            ]
            quantized_measures.append(QuantizedMeasure(**quantized_measure_as_dict))
        return cls(quantized_measures)

    @property
    def measure_lengths(self) -> Sequence[float]:
        """
        Tuple of all measure lengths
        """
        return tuple(quantized_measure.measure_length for quantized_measure in self.quantized_measures)

    @property
    def time_signatures(self) -> Sequence[TimeSignature]:
        """
        Tuple of the TimeSignature object for each measure
        """
        return tuple(quantized_measure.time_signature for quantized_measure in self.quantized_measures)

    def __repr__(self):
        return "QuantizationRecord([\n{}\n])".format(
            textwrap.indent(",\n".join(str(x) for x in self.quantized_measures), "   ")
        )


##################################################################################################################
#                                           Quantization functions
##################################################################################################################


def quantize_performance_part(part: 'PerformancePart', quantization_scheme: QuantizationScheme,
                              onset_weighting: float = "default",  termination_weighting: float = "default",
                              inner_split_weighting: float = "default"):
    """
    Quantizes a performance part (in place) and sets its voice_quantization_records

    :param part: a PerformancePart
    :param quantization_scheme: a QuantizationScheme
    :param onset_weighting: How much do we care about accurate onsets
    :param termination_weighting: How much do we care about accurate terminations
    :param inner_split_weighting: How much do we care about inner segmentation timing (e.g. tuple note lengths)
    :return: a QuantizationRecord, detailing all of the time signatures, beat divisions selected, etc.
    """
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
            note._divide_length_at_gliss_control_points()

    # make list of (note onset time, note) tuples
    raw_onsets = [(performance_note.start_beat, performance_note) for performance_note in voice]
    # make list of (note termination time, note) tuples
    raw_terminations = [(performance_note.start_beat + performance_note.length_sum(), performance_note)
                        for performance_note in voice]
    # make list of (inner split time, note) tuples
    raw_inner_splits = []
    for performance_note in voice:
        if hasattr(performance_note.length, "__len__"):
            t = performance_note.start_beat
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
        beat_scheme, beat_start = next(beat_scheme_iterator)
        assert isinstance(beat_scheme, BeatQuantizationScheme)
        beat_end = beat_start + beat_scheme.length

        # find the onsets in this beat
        onsets_in_this_beat = []
        while len(raw_onsets) > 0 and raw_onsets[0][0] < beat_end:
            onsets_in_this_beat.append(raw_onsets.pop(0))

        # find the terminations in this beat
        terminations_in_this_beat = []
        while len(raw_terminations) > 0 and raw_terminations[0][0] < beat_end:
            terminations_in_this_beat.append(raw_terminations.pop(0))

        # find the inner splits in this beat
        inner_splits_in_this_beat = []
        while len(raw_inner_splits) > 0 and raw_inner_splits[0][0] < beat_end:
            inner_splits_in_this_beat.append(raw_inner_splits.pop(0))

        if len(onsets_in_this_beat) + len(terminations_in_this_beat) + len(inner_splits_in_this_beat) == 0:
            # an empty beat, nothing to see here
            beat_divisors.append(None)
            continue

        best_divisor = _get_best_divisor_for_beat(
            beat_scheme, beat_start, onsets_in_this_beat, terminations_in_this_beat, inner_splits_in_this_beat,
            onset_weighting, termination_weighting, inner_split_weighting
        )
        beat_divisors.append(best_divisor)

        # Now, quantize all of the notes that start or end in this beat accordingly
        division_length = beat_scheme.length / best_divisor
        for onset, note in onsets_in_this_beat:
            divisions_after_beat_start = round((onset - beat_start) / division_length)
            note.start_beat = beat_start + divisions_after_beat_start * division_length

        for termination, note in terminations_in_this_beat:
            divisions_after_beat_start = round((termination - beat_start) / division_length)
            note.end_beat = beat_start + divisions_after_beat_start * division_length

            if note.length_sum() <= 0:
                # this covers a rare case in which the note has multiple segments, but is getting squeezed by the
                # quantization into a length of zero. In this case, dispense with the segments, just make it length 0
                if hasattr(note.length, "__len__") > 0:
                    note.length = 0
                # if the quantization collapses the start and end times of a note to the same point,
                # adjust so the the note is a single division_length long.
                if note.end_beat + division_length <= beat_end:
                    # if there's room to, just move the end of the note one division forward
                    note.length += division_length
                else:
                    # otherwise, move the start of the note one division backward
                    note.start_beat -= division_length
                    note.length += division_length

        # we take note of where all the inner splits quantize to, and then once all of the start
        # and end times for the notes are adjusted, we go ahead and put them it.
        for inner_split, note in inner_splits_in_this_beat:
            divisions_after_beat_start = round((inner_split - beat_start) / division_length)
            quantized_split_beat = beat_start + divisions_after_beat_start * division_length
            if "split_points" in note.properties.temp:
                note.properties.temp["split_points"].append(quantized_split_beat)
            else:
                note.properties.temp["split_points"] = [quantized_split_beat]

    last_note_end_beat = 0
    for note in voice:
        # now that all the start and end points have been adjusted,
        # we implement the quantized split points where applicable
        if "split_points" in note.properties.temp:
            last_split_point = note.start_beat
            new_lengths = []
            for split_point in sorted(note.properties.temp["split_points"]):
                if round(split_point - last_split_point, 10) > 0:
                    new_lengths.append(split_point - last_split_point)
                last_split_point = split_point
            if round(note.end_beat - last_split_point, 10) > 0:
                new_lengths.append(note.end_beat - last_split_point)
            note.length = tuple(new_lengths)

        last_note_end_beat = max(note.end_beat, last_note_end_beat)

        # also normalize the pitch envelopes
        if isinstance(note.pitch, Envelope):
            note.pitch.normalize_to_duration(note.length_sum())

    return _construct_quantization_record(beat_divisors, last_note_end_beat, quantization_scheme)


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
            if voice[-1].end_beat <= note.start_beat + max_overlap:
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


def _construct_quantization_record(beat_divisors, end_beat, quantization_scheme):
    """
    Constructs a QuantizationRecord from the given scheme and divisors

    :param beat_divisors: a list of beat divisors resulting from quantization
    :param end_beat: This helps us cover the special case in which the last note ends at the very end of a measure.
        In this case, it's termination gets quantized in the first beat of the next measure, so we have a beat divisor
        in that measure but no actual notes there. By checking if we've hit the end_beat we can avoid constructing
        that extra measure.
    :param quantization_scheme: the quantization scheme being used
    :return: a QuantizationRecord
    """
    assert isinstance(beat_divisors, list)
    quantized_measures = []

    for measure_scheme, t in quantization_scheme.measure_scheme_iterator():
        measure_start_beat = t
        beats = []
        min_duple_subdivision = float("inf")

        for beat_scheme in measure_scheme.beat_schemes:
            divisor = beat_divisors.pop(0) if len(beat_divisors) > 0 else None
            beats.append(
                QuantizedBeat(t, t - measure_start_beat, beat_scheme.length, divisor)
            )
            if divisor is not None:
                subdivision_length = beat_scheme.length / divisor
                if is_x_pow_of_y(subdivision_length, 2) and subdivision_length < min_duple_subdivision:
                    min_duple_subdivision = subdivision_length
            t += beat_scheme.length

        beat_depths = (0.5, measure_scheme.get_beat_hierarchies(0.5)) if min_duple_subdivision == float("inf") \
            else (min_duple_subdivision, measure_scheme.get_beat_hierarchies(min_duple_subdivision))

        quantized_measure = QuantizedMeasure(measure_start_beat, measure_scheme.length, beats,
                                             measure_scheme.time_signature, beat_depths)

        quantized_measures.append(quantized_measure)

        if len(beat_divisors) == 0 or t >= end_beat:
            return QuantizationRecord(quantized_measures)
