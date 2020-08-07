#  ++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++  #
#  SCAMP (Suite for Computer-Assisted Music in Python)                                           #
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

from copy import deepcopy
import math

from playcorder.utilities import floor_x_to_pow_of_y, is_x_pow_of_y, is_multiple, indigestibility

__author__ = 'mpevans'

empty_variant_dictionary = {
    # gets converted to an element with the same name placed in the note articulations
    # put any properties in parentheses
    "articulations": [],
    # gets converted to an element of the same name placed in the dynamics tag in the notations tag
    # put any properties in parentheses
    "dynamics": [],
    # gets converted to an element of the same name placed in the notations element
    # put any properties in parentheses
    "notations": [],
    # gets converted to the text of a "notehead" element placed in the note object
    # put any properties in parentheses, e.g. "diamond(filled=no)"
    "notehead": None,
    # gets converted to a Text element that is placed before the note
    # if properties need to be set, the annotation should be a tuple of (text, properties_dictionary)
    "text_annotations": []
}


def standardize_variant_dictionary(variant_dictionary):
    standardized_variant_dict = deepcopy(empty_variant_dictionary)
    if variant_dictionary is not None:
        assert isinstance(standardized_variant_dict, dict)
        for key in standardized_variant_dict.keys():
            if key.endswith("s"):
                # it's a list key, like articulations
                if key[:-1] in variant_dictionary:
                    standardized_variant_dict[key].append(variant_dictionary[key[:-1]])
                if key in variant_dictionary:
                    standardized_variant_dict[key].extend(variant_dictionary[key])
            else:
                # it's a single value key, like "notehead"
                if key in variant_dictionary:
                    standardized_variant_dict[key] = variant_dictionary[key]
    return standardized_variant_dict


class PCNote:
    def __init__(self, start_time, length, pitch, volume, variant=None, tie=None, notations=None, articulations=None,
                 notehead=None, beams=None, text_annotations=None, time_modification=None):
        self.start_time = start_time
        self.length = length
        self.pitch = pitch
        self.volume = volume
        self.variant = standardize_variant_dictionary(variant)
        self.tie = tie
        self.beams = beams
        self.time_modification = time_modification
        # xml objects from variants
        self.notations = [] if notations is None else notations
        self.articulations = [] if articulations is None else articulations
        self.notehead = notehead
        self.text_annotations = [] if text_annotations is None else text_annotations
        # used during processing
        self.length_without_tuplet = None
        self.starts_tuplet = self.ends_tuplet = False
        self.initial_notehead = False

    def __repr__(self):
        return "PCNote(start_time={}, length={}, pitch={}, volume={}, variant={}, tie={}, time_modification={}, " \
               "notations={}, articulations={})".format(
                    self.start_time, self.length, self.pitch, self.volume, self.variant, self.tie,
                    self.time_modification, self.notations, self.articulations
                )
        # return "MPNote(start_time={}, length={}, pitch={})".format(
        #     self.start_time, self.length, self.pitch
        # )

    @property
    def end_time(self):
        return self.start_time + self.length

    def get_num_beams(self):
        return -int(round(math.floor(math.log(self.length_without_tuplet, 2))))

    def add_beam_layer(self, depth, text):
        if self.beams is None:
            self.beams = {}
        self.beams[depth] = text

    @staticmethod
    def length_to_undotted_constituents(length):
        length = round(length, 6)
        length_parts = []
        while length > 0:
            this_part = floor_x_to_pow_of_y(length, 2.0)
            length -= this_part
            length_parts.append(this_part)
        return length_parts


class BeatQuantizationScheme:

    def __init__(self, tempo, beat_length, divisions=8, max_indigestibility=4, simplicity_preference=0.5):
        """

        :param tempo: In quarter-notes per minute
        :param beat_length: In quarter-notes
        :param divisions: This parameter can take several forms. If an integer is given, then all beat divisions up to
        that integer are allowed, providing that the divisor indigestibility is less than the max_indigestibility.
        Alternatively, a list of allowed divisors can be given. This is useful if we know ahead of time exactly how
        we will be dividing the beat. Each divisor will be assigned an undesirability based on its indigestibility;
        however these can be overridden by passing a list of tuples formatted [(divisor1, undesirability1),
        (divisor2, undesirability2), etc... ] to this parameter.
        :param max_indigestibility: For generating preferred divisions automatically, the biggest divisor
        indigestibility allowed.
        :param simplicity_preference: ranges 0 - whatever. A simplicity_preference of 0 means, all divisions are
        treated equally; a 7 is as good as a 4. A simplicity_preference of 1 means that the most desirable division
        is left alone, the most undesirable division gets its error doubled, and all other divisions are somewhere in
        between. Simplicity preference can be greater than 1, in which case the least desirable division gets its
        error multiplied by (simplicity_preference + 1)
        """
        self.tempo = tempo
        # actual length of the beat
        self.beat_length = float(beat_length)
        # the length it would be if no tuplet were written. e.g. if it a quarter beat divided in 7, we're going to have
        # seven 16ths in the space of 4, so the written length aside from the tuplet will be  1.75
        self.length_without_tuplet = None
        # now we populate a self.quantization_divisions with tuples consisting of the allowed divisions and
        # their undesirabilities. Undesirability is a factor by which the error in a given quantization option
        # is multiplied; the lowest possible undesirability is 1
        if isinstance(divisions, int):
            # what we care about is how well the given division works within the most natural division of the
            # beat_length so first notate the beat_length as a fraction; its numerator is its most natural division
            beat_length_fraction = Fraction(self.beat_length).limit_denominator()

            quantization_divisions = []
            div_indigestibilities = []
            for div in range(2, divisions + 1):
                relative_division = Fraction(div, beat_length_fraction.numerator)
                div_indigestibility = indigestibility(relative_division.numerator) + \
                    indigestibility(relative_division.denominator)
                if div_indigestibility < max_indigestibility:
                    quantization_divisions.append(div)
                    div_indigestibilities.append(div_indigestibility)
            div_indigestibility_range = min(div_indigestibilities), max(div_indigestibilities)
            div_undesirabilities = [1 + simplicity_preference * (float(di) - div_indigestibility_range[0]) /
                                    (div_indigestibility_range[1] - div_indigestibility_range[0])
                                    for di in div_indigestibilities]
            self.quantization_divisions = list(zip(quantization_divisions, div_undesirabilities))
        else:
            assert hasattr(divisions, "__len__") and len(divisions) > 0
            if isinstance(divisions[0], tuple):
                # already (divisor, undesirability) tuples
                self.quantization_divisions = divisions
            else:
                # we've just been given the divisors, and have to figure out the undesirabilities
                if len(divisions) == 1:
                    # there's only one way we're allowed to divide the beat, so just give it undesirability 1, whatever
                    self.quantization_divisions = list(zip(divisions, [1.0]))
                else:
                    beat_length_fraction = Fraction(self.beat_length).limit_denominator()
                    div_indigestibilities = []
                    for div in divisions:
                        relative_division = Fraction(div, beat_length_fraction.numerator)
                        div_indigestibility = indigestibility(relative_division.numerator) + \
                            indigestibility(relative_division.denominator)
                        div_indigestibilities.append(div_indigestibility)
                    div_indigestibility_range = min(div_indigestibilities), max(div_indigestibilities)
                    div_undesirabilities = [1 + simplicity_preference * (float(di) - div_indigestibility_range[0]) /
                                            (div_indigestibility_range[1] - div_indigestibility_range[0])
                                            for di in div_indigestibilities]
                    self.quantization_divisions = list(zip(divisions, div_undesirabilities))

        # when used to quantize something, this gets set
        self.start_time = 0

    @property
    def end_time(self):
        return self.start_time + self.beat_length

    def __str__(self):
        return "BeatQuantizationScheme(tempo={}, beat_length={}, quantization_divisions={})".format(
            self.tempo, self.beat_length, self.quantization_divisions)

    def __repr__(self):
        return "BeatQuantizationScheme(tempo={}, beat_length={}, quantization_divisions={})".format(
            self.tempo, self.beat_length, self.quantization_divisions)


class MeasureScheme:

    def __init__(self, time_signature, beat_quantization_schemes):
        # time_signature is either a tuple, e.g. (3, 4), or a string, e.g. "3/4"
        self.string_time_signature, self.tuple_time_signature = MeasureScheme.time_sig_to_string_and_tuple(time_signature)
        # in quarter notes
        self.measure_length = self.tuple_time_signature[0]*4/float(self.tuple_time_signature[1])

        # either we give a list of beat_quantization schemes or a single beat quantization scheme to use for all beats
        if hasattr(beat_quantization_schemes, "__len__"):
            total_length = 0
            for beat_quantization_scheme in beat_quantization_schemes:
                assert isinstance(beat_quantization_scheme, BeatQuantizationScheme)
                total_length += beat_quantization_scheme.beat_length
            assert total_length == self.measure_length
            self.beat_quantization_schemes = beat_quantization_schemes
        else:
            assert isinstance(beat_quantization_schemes, BeatQuantizationScheme)
            assert is_multiple(self.measure_length, beat_quantization_schemes.beat_length)
            num_beats_in_measure = int(round(self.measure_length / beat_quantization_schemes.beat_length))
            self.beat_quantization_schemes = []
            for _ in range(num_beats_in_measure):
                self.beat_quantization_schemes.append(deepcopy(beat_quantization_schemes))

        self.length = sum([beat_scheme.beat_length for beat_scheme in self.beat_quantization_schemes])

        # when used to quantize something, this gets set
        self.start_time = 0

    @property
    def end_time(self):
        return self.start_time + self.length

    @staticmethod
    def time_sig_to_string_and_tuple(time_signature):
        if isinstance(time_signature, str):
            string_time_signature = time_signature
            tuple_time_signature = tuple([int(x) for x in time_signature.split("/")])
        else:
            tuple_time_signature = tuple(time_signature)
            string_time_signature = str(time_signature[0]) + "/" + str(time_signature[1])
        return string_time_signature, tuple_time_signature

    @classmethod
    def from_time_signature(cls, time_signature, tempo, divisions=8, max_indigestibility=4, simplicity_preference=0.5):
        # it would be good to be able to handle ((2, 3, 2), 8) or "2+3+2/8"
        _, tuple_time_signature = MeasureScheme.time_sig_to_string_and_tuple(time_signature)
        measure_length = tuple_time_signature[0] * 4.0 / tuple_time_signature[1]
        assert is_x_pow_of_y(tuple_time_signature[1], 2)
        if tuple_time_signature[1] <= 4:
            beat_length = 4.0 / tuple_time_signature[1]
            num_beats = int(round(measure_length/beat_length))
            beat_quantization_schemes = []
            for _ in range(num_beats):
                beat_quantization_schemes.append(BeatQuantizationScheme(tempo, beat_length, divisions=divisions,
                                                                        max_indigestibility=max_indigestibility,
                                                                        simplicity_preference=simplicity_preference))
        else:
            # we're dealing with a denominator of 8, 16, etc., so either we have a compound meter, or an uneven meter
            if is_multiple(tuple_time_signature[0], 3):
                beat_length = 4.0 / tuple_time_signature[1] * 3
                num_beats = int(round(measure_length/beat_length))
                beat_quantization_schemes = []
                for _ in range(num_beats):
                    beat_quantization_schemes.append(BeatQuantizationScheme(tempo, beat_length,
                                                                            divisions=divisions,
                                                                            max_indigestibility=max_indigestibility,
                                                                            simplicity_preference=simplicity_preference))

            else:
                duple_beat_length = 4.0 / tuple_time_signature[1] * 2
                triple_beat_length = 4.0 / tuple_time_signature[1] * 3
                if is_multiple(tuple_time_signature[0], 2):
                    num_duple_beats = int(round(measure_length/duple_beat_length))
                    num_triple_beats = 0
                else:
                    num_duple_beats = int(round((measure_length-triple_beat_length)/duple_beat_length))
                    num_triple_beats = 1
                beat_quantization_schemes = []
                for _ in range(num_duple_beats):
                    beat_quantization_schemes.append(BeatQuantizationScheme(tempo, duple_beat_length,
                                                                            divisions=divisions,
                                                                            max_indigestibility=max_indigestibility,
                                                                            simplicity_preference=simplicity_preference))
                for _ in range(num_triple_beats):
                    beat_quantization_schemes.append(BeatQuantizationScheme(tempo, triple_beat_length,
                                                                            divisions=divisions,
                                                                            max_indigestibility=max_indigestibility,
                                                                            simplicity_preference=simplicity_preference))
        return cls(time_signature, beat_quantization_schemes)