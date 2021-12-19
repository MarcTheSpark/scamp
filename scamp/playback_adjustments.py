"""
Module containing classes for defining adjustments to the playback of note parameters, as well as the
:class:`PlaybackAdjustmentsDictionary`, which defines how particular notations should be played back.
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
import re
from numbers import Real
from .utilities import SavesToJSON, NoteProperty
from expenvelope import Envelope
from typing import Union, Sequence


def _split_string_at_outer_spaces(s):
    """
    Splits a string only at those commas that are not inside some sort of parentheses
    e.g. "hello, [2, 5], {2: 7}" => ["hello", "[2, 5]", "{2: 7}"]
    """
    out = []
    paren_count = square_count = curly_count = 0
    last_split = i = 0
    for character in s:
        i += 1
        if character == "(":
            paren_count += 1
        elif character == "[":
            square_count += 1
        elif character == "{":
            curly_count += 1
        elif character == ")":
            paren_count -= 1
        elif character == "]":
            square_count -= 1
        elif character == "}":
            curly_count -= 1
        elif character == " " and paren_count == square_count == curly_count == 0:
            out.append(s[last_split:i-1].strip())
            last_split = i
    out.append(s[last_split:].strip())
    return out


class ParamPlaybackAdjustment(SavesToJSON):

    """
    Represents a multiply/add playback adjustment to a single parameter.
    (The multiply happens first, then the add.)

    :param multiply: how much to multiply by
    :param add: how much to add
    :ivar multiply: how much to multiply by
    :ivar add: how much to add
    """

    def __init__(self, multiply: Union[Real, Envelope, Sequence] = 1, add: Union[Real, Envelope, Sequence] = 0):
        self.multiply = Envelope.from_list(multiply) if isinstance(multiply, Sequence) else multiply
        self.add_amount = Envelope.from_list(add) if isinstance(add, Sequence) else add

    @classmethod
    def from_string(cls, string: str) -> 'ParamPlaybackAdjustment':
        """
        Construct a ParamPlaybackAdjustment from an appropriately formatted string.

        :param string: written using either "*", "+"/"-", both "*" and "+"/"-" or equals followed by numbers. For
            example, "* 0.5" multiplies by 0.5, "= 7" sets equal to 87, "* 1.1 - 3" multiplies by 1.1 and then
            subtracts 3. Note that "/" for division is not understood (instead multiply by the inverse), and that
            where a multiplication and an addition/subtraction are used together, the multiplication must come first.
        :return: a ParamPlaybackAdjustment
        """
        if "envelope" in string.lower():
            raise ValueError("Cannot directly use envelope object in string representation of parameter adjustment; "
                             "use list shorthand instead, or create a ParamPlaybackAdjustment or NotePlaybackAdjustment"
                             "directly.")
        times_index = string.index("*") if "*" in string else None
        plus_index = string.index("+") if "+" in string else None
        minus_index = string.index("-") if "-" in string else None
        equals_index = string.index("=") if "=" in string else None
        try:
            if equals_index is not None:
                assert times_index is None and plus_index is None and minus_index is None
                return cls.set_to(eval(string[equals_index + 1:]))
            else:
                assert not (plus_index is not None and minus_index is not None)
                plus_minus_index = plus_index if plus_index is not None else minus_index

                multiply_string = add_string = None
                if times_index is not None:
                    if plus_minus_index is not None:
                        assert plus_minus_index > times_index
                        multiply_string = string[times_index + 1:plus_minus_index]
                        add_string = string[plus_minus_index:] if minus_index is not None \
                            else string[plus_minus_index + 1:]
                    else:
                        multiply_string = string[times_index + 1:]
                else:
                    add_string = string[plus_minus_index:] if minus_index is not None \
                        else string[plus_minus_index + 1:]

                add = eval(re.sub(r'\[.*\]', lambda match: "Envelope.from_list(" + match.group(0) + ")",
                                  add_string)) if add_string is not None else 0
                multiply = eval(re.sub(r'\[.*\]', lambda match: "Envelope.from_list(" + match.group(0) + ")",
                                       multiply_string)) if multiply_string is not None else 1
                return cls(add=add, multiply=multiply)
        except (AssertionError, SyntaxError):
            raise ValueError("Bad parameter adjustment expression.")

    @classmethod
    def set_to(cls, value) -> 'ParamPlaybackAdjustment':
        """
        Class method for an adjustment that resets the value of the parameter, ignoring its original value

        :param value: the value to set the parameter to
        """
        return cls(0, value)

    @classmethod
    def scale(cls, value) -> 'ParamPlaybackAdjustment':
        """
        Class method for a simple scaling adjustment.

        :param value: the factor to scale by
        """
        return cls(value)

    @classmethod
    def add(cls, value) -> 'ParamPlaybackAdjustment':
        """
        Class method for a simple additive adjustment.

        :param value: how much to add
        """
        return cls(1, value)

    def adjust_value(self, param_value, normalize_envelope_to_length=None):
        """
        Apply this adjustment to a given parameter value

        :param param_value: the parameter value to adjust
        :param normalize_envelope_to_length: if given, and the add or multiply is an Envelope object, normalize the
            length of that envelope object to this.
        :return: the adjusted value of the parameter
        """
        # in case the param value is a Envelope, it's best to leave out the multiply if it's zero
        # for instance, if param_value is a Envelope, multiply is zero and add is a Envelope,
        # you would end up trying to add two Envelopes, which we don't allow
        add_amount = self.add_amount.normalize_to_duration(normalize_envelope_to_length, in_place=False) \
            if isinstance(self.add_amount, Envelope) and normalize_envelope_to_length is not None else self.add_amount
        mul_amount = self.multiply.normalize_to_duration(normalize_envelope_to_length, in_place=False) \
            if isinstance(self.multiply, Envelope) and normalize_envelope_to_length is not None else self.multiply

        return add_amount if mul_amount == 0 else param_value + add_amount if mul_amount == 1 \
            else param_value * mul_amount + add_amount

    def uses_envelope(self):
        return isinstance(self.add_amount, Envelope) or isinstance(self.multiply, Envelope)

    def _to_dict(self):
        return {"multiply": self.multiply, "add": self.add_amount}

    @classmethod
    def _from_dict(cls, json_dict):
        return cls(**json_dict)

    def __eq__(self, other):
        if isinstance(other, ParamPlaybackAdjustment):
            return hash(self) == hash(other)
        return False

    def __hash__(self):
        return hash((self.multiply, self.add_amount))

    def __repr__(self):
        return "ParamPlaybackAdjustment({}, {})".format(self.multiply, self.add_amount)


class NotePlaybackAdjustment(SavesToJSON, NoteProperty):

    """
    Represents an adjustment to the pitch, volume and/or length of the playback of a single note

    :param pitch_adjustment: The desired adjustment for the note's pitch. (None indicates no adjustment)
    :param volume_adjustment: The desired adjustment for the note's volume. (None indicates no adjustment)
    :param length_adjustment: The desired adjustment for the note's length. (None indicates no adjustment)
    :ivar pitch_adjustment: The desired adjustment for the note's pitch. (None indicates no adjustment)
    :ivar volume_adjustment: The desired adjustment for the note's volume. (None indicates no adjustment)
    :ivar length_adjustment: The desired adjustment for the note's length. (None indicates no adjustment)
    """

    def __init__(self, pitch_adjustment: ParamPlaybackAdjustment = None,
                 volume_adjustment: ParamPlaybackAdjustment = None, length_adjustment: ParamPlaybackAdjustment = None,
                 scale_envelopes_to_length=False):
        self.pitch_adjustment: ParamPlaybackAdjustment = pitch_adjustment
        self.volume_adjustment: ParamPlaybackAdjustment = volume_adjustment
        self.length_adjustment: ParamPlaybackAdjustment = length_adjustment
        if self.length_adjustment is not None and self.length_adjustment.uses_envelope():
            raise ValueError("Length adjustment cannot use an Envelope; what would that even mean?")
        self.scale_envelopes_to_length = scale_envelopes_to_length

    @classmethod
    def from_string(cls, string: str) -> 'NotePlaybackAdjustment':
        """
        Construct a NotePlaybackAdjustment from a string using a particular grammar.

        :param string: should take the form of, e.g. "volume * 0.5 pitch = 69 length * 2 - 1". This would cause the
            volume to be halved, the pitch to be set to 69, and the length to be doubled plus 1. Note that "/" for
            division is not understood and that where a multiplication and an addition/subtraction are used together,
            the multiplication must come first. The parameters can be separated by commas or semicolons optionally,
            for visual clarity.
        :return: a shiny new NotePlaybackAdjustment
        """
        if "pitch" not in string and "volume" not in string and "length" not in string:
            raise ValueError("String not parsable as NotePlaybackAdjustment")
        string = string.replace(" ", "").replace(";", "")
        pitch_adjustment = volume_adjustment = length_adjustment = None
        for adjustment_expression in NotePlaybackAdjustment._split_at_param_names(string):
            if adjustment_expression.startswith("pitch"):
                if pitch_adjustment is not None:
                    raise ValueError("Multiple conflicting pitch adjustments given.")
                pitch_adjustment = ParamPlaybackAdjustment.from_string(adjustment_expression)
            elif adjustment_expression.startswith("volume"):
                if volume_adjustment is not None:
                    raise ValueError("Multiple conflicting volume adjustments given.")
                volume_adjustment = ParamPlaybackAdjustment.from_string(adjustment_expression)
            elif adjustment_expression.startswith("length"):
                if length_adjustment is not None:
                    raise ValueError("Multiple conflicting length adjustments given.")
                length_adjustment = ParamPlaybackAdjustment.from_string(adjustment_expression)
        return cls(pitch_adjustment=pitch_adjustment, volume_adjustment=volume_adjustment,
                   length_adjustment=length_adjustment, scale_envelopes_to_length=True)

    @staticmethod
    def _split_at_param_names(string: str):
        if "pitch" in string and not string.startswith("pitch"):
            i = string.index("pitch")
            return NotePlaybackAdjustment._split_at_param_names(string[:i]) + \
                   NotePlaybackAdjustment._split_at_param_names(string[i:])
        elif "volume" in string and not string.startswith("volume"):
            i = string.index("volume")
            return NotePlaybackAdjustment._split_at_param_names(string[:i]) + \
                   NotePlaybackAdjustment._split_at_param_names(string[i:])
        elif "length" in string and not string.startswith("length"):
            i = string.index("length")
            return NotePlaybackAdjustment._split_at_param_names(string[:i]) + \
                   NotePlaybackAdjustment._split_at_param_names(string[i:])
        return string,

    @classmethod
    def scale_params(cls, pitch=1, volume=1, length=1) -> 'NotePlaybackAdjustment':
        """
        Constructs a NotePlaybackAdjustment that scales the parameters

        :param pitch: pitch scale factor
        :param volume: volume scale factor
        :param length: length scale factor
        :return: a shiny new NotePlaybackAdjustment
        """
        return cls(ParamPlaybackAdjustment.scale(pitch) if pitch != 1 else None,
                   ParamPlaybackAdjustment.scale(volume) if volume != 1 else None,
                   ParamPlaybackAdjustment.scale(length) if length != 1 else None)

    @classmethod
    def add_to_params(cls, pitch=None, volume=None, length=None) -> 'NotePlaybackAdjustment':
        """
        Constructs a NotePlaybackAdjustment that adds to the parameters

        :param pitch: pitch addition
        :param volume: volume addition
        :param length: length addition
        :return: a shiny new NotePlaybackAdjustment
        """
        return cls(ParamPlaybackAdjustment.add(pitch) if pitch is not None else None,
                   ParamPlaybackAdjustment.add(volume) if volume is not None else None,
                   ParamPlaybackAdjustment.add(length) if length is not None else None)

    @classmethod
    def set_params(cls, pitch=None, volume=None, length=None) -> 'NotePlaybackAdjustment':
        """
        Constructs a NotePlaybackAdjustment that directly resets the parameters

        :param pitch: new pitch setting
        :param volume: new volume setting
        :param length: new length setting
        :return: a shiny new NotePlaybackAdjustment
        """
        return cls(ParamPlaybackAdjustment.set_to(pitch) if pitch is not None else None,
                   ParamPlaybackAdjustment.set_to(volume) if volume is not None else None,
                   ParamPlaybackAdjustment.set_to(length) if length is not None else None)

    def adjust_parameters(self, pitch, volume, length):
        """
        Carry out the adjustments represented by this object on the pitch, volume and length given.

        :param pitch: pitch to adjust
        :param volume: volume to adjust
        :param length: length to adjust
        :return: tuple of (adjusted_pitch, adjusted_volume, adjusted_length)
        """
        adjusted_length = self.length_adjustment.adjust_value(length) if self.length_adjustment is not None else length

        return self.pitch_adjustment.adjust_value(pitch, adjusted_length if self.scale_envelopes_to_length else None) \
                   if self.pitch_adjustment is not None else pitch, \
               self.volume_adjustment.adjust_value(volume, adjusted_length if self.scale_envelopes_to_length else None) \
                   if self.volume_adjustment is not None else volume, \
               adjusted_length

    def _to_dict(self):
        json_dict = {}
        if self.pitch_adjustment is not None:
            json_dict["pitch_adjustment"] = self.pitch_adjustment
        if self.volume_adjustment is not None:
            json_dict["volume_adjustment"] = self.volume_adjustment
        if self.length_adjustment is not None:
            json_dict["length_adjustment"] = self.length_adjustment
        if self.scale_envelopes_to_length:
            json_dict["scale_envelopes_to_length"] = self.scale_envelopes_to_length
        return json_dict

    @classmethod
    def _from_dict(cls, json_dict):
        return cls(**json_dict)

    def __eq__(self, other):
        if isinstance(other, NotePlaybackAdjustment):
            return hash(self) == hash(other)
        return False

    def __hash__(self):
        return hash((self.pitch_adjustment, self.volume_adjustment, self.length_adjustment,
                     self.scale_envelopes_to_length))

    def __repr__(self):
        return "NotePlaybackAdjustment({}, {}, {})".format(
            self.pitch_adjustment, self.volume_adjustment, self.length_adjustment
        )
