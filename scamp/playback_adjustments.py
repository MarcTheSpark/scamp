"""
Module containing classes for defining adjustments to the playback of note parameters, as well as the
:class:`PlaybackAdjustmentsDictionary`, which defines how particular notations should be played back.
"""

from .utilities import SavesToJSON
from ._engraving_translations import *
from typing import Union


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
    Represents a multiple/add playback adjustment to a single parameter.
    (The multiply happens first, then the add.

    :param multiply: how much to multiply by
    :param add: how much to add
    :ivar multiply: how much to multiply by
    :ivar add: how much to add
    """

    def __init__(self, multiply: float = 1, add: float = 0):
        self.multiply = multiply
        self.add = add

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
                if times_index is not None:
                    if plus_minus_index is not None:
                        assert plus_minus_index > times_index
                        return cls(multiply=eval(string[times_index + 1:plus_minus_index]),
                                   add=eval(string[plus_minus_index:]))
                    else:
                        return cls(multiply=eval(string[times_index + 1:]))
                else:
                    return cls(add=eval(string[plus_minus_index:]))
        except AssertionError:
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

    def adjust_value(self, param_value):
        """
        Apply this adjustment to a given parameter value

        :param param_value: the parameter value to adjust
        :return: the adjusted value of the parameter
        """
        # in case the param value is a Envelope, it's best to leave out the multiply if it's zero
        # for instance, if param_value is a Envelope, multiply is zero and add is a Envelope,
        # you would end up trying to add two Envelopes, which we don't allow
        return self.add if self.multiply == 0 else param_value * self.multiply + self.add

    def _to_json(self):
        return self.__dict__

    @classmethod
    def _from_json(cls, json_object):
        return cls(**json_object)

    def __repr__(self):
        return "ParamPlaybackAdjustment({}, {})".format(self.multiply, self.add)


class NotePlaybackAdjustment(SavesToJSON):

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
                 volume_adjustment: ParamPlaybackAdjustment = None,
                 length_adjustment: ParamPlaybackAdjustment = None):
        self.pitch_adjustment: ParamPlaybackAdjustment = pitch_adjustment
        self.volume_adjustment: ParamPlaybackAdjustment = volume_adjustment
        self.length_adjustment: ParamPlaybackAdjustment = length_adjustment

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
        string = string.replace(" ", "").replace(",", "").replace(";", "")
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
                   length_adjustment=length_adjustment)

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
        :param length: length tho adjust
        :return: tuple of (adjusted_pitch, adjusted_volume, adjusted_length)
        """
        return self.pitch_adjustment.adjust_value(pitch) if self.pitch_adjustment is not None else pitch, \
               self.volume_adjustment.adjust_value(volume) if self.volume_adjustment is not None else volume, \
               self.length_adjustment.adjust_value(length) if self.length_adjustment is not None else length

    def _to_json(self):
        json_dict = {}
        if self.pitch_adjustment is not None:
            json_dict["pitch_adjustment"] = self.pitch_adjustment._to_json()
        if self.volume_adjustment is not None:
            json_dict["volume_adjustment"] = self.volume_adjustment._to_json()
        if self.length_adjustment is not None:
            json_dict["length_adjustment"] = self.length_adjustment._to_json()
        return json_dict

    @classmethod
    def _from_json(cls, json_object):
        return cls(**{
            adjustment_name: ParamPlaybackAdjustment._from_json(json_object[adjustment_name])
            for adjustment_name in json_object
        })

    def __repr__(self):
        return "NotePlaybackAdjustment({}, {}, {})".format(
            self.pitch_adjustment, self.volume_adjustment, self.length_adjustment
        )


class PlaybackAdjustmentsDictionary(dict, SavesToJSON):

    """
    Dictionary containing playback adjustments for different articulations, noteheads, and other notations.
    The instance of this at playback_settings.adjustments is consulted during playback. Essentially, this is
    just a dictionary with some validation and a couple of convenience methods to set and get adjustments for
    different properties.

    :param articulations: dictionary mapping articulation names to playback adjustments. For example, to have
        staccato notes be played at half length: `{"staccato": NotePlaybackAdjustment.scale_params(length=0.5)}`
    :param noteheads: dictionary mapping notehead names to playback adjustments. For example, to have harmonic
        noteheads be played up an octave: `{"harmonic": NotePlaybackAdjustment.add_to_params(pitch=12)}`
    :param notations: dictionary mapping notation names to playback adjustments.
    """

    #: list of all recognized articulations
    all_articulations = list(articulation_to_xml_element_name.keys())
    #: list of all recognized noteheads
    all_noteheads = list(notehead_name_to_xml_type.keys())
    all_noteheads.extend(["filled " + notehead_name for notehead_name in all_noteheads])
    all_noteheads.extend(["open " + notehead_name for notehead_name in all_noteheads
                          if not notehead_name.startswith("filled")])
    #: list of all recognized notations
    all_notations = list(notations_to_xml_notations_element.keys())

    def __init__(self, articulations: dict = None, noteheads: dict = None, notations: dict = None):
        # make sure there is an entry for every notehead, articulation, and notation
        if articulations is None:
            articulations = {x: None for x in PlaybackAdjustmentsDictionary.all_articulations}
        else:
            articulations = {x: articulations[x] if x in articulations else None
                             for x in PlaybackAdjustmentsDictionary.all_articulations}
        if noteheads is None:
            noteheads = {x: None for x in PlaybackAdjustmentsDictionary.all_noteheads}
        else:
            noteheads = {x: noteheads[x] if x in noteheads else None
                         for x in PlaybackAdjustmentsDictionary.all_noteheads}
        if notations is None:
            notations = {x: None for x in PlaybackAdjustmentsDictionary.all_notations}
        else:
            notations = {x: notations[x] if x in notations else None
                         for x in PlaybackAdjustmentsDictionary.all_notations}

        super().__init__(articulations=articulations, noteheads=noteheads, notations=notations)

    @property
    def articulations(self) -> dict:
        """
        Dictionary mapping articulation names to corresponding playback adjustments
        """
        return self["articulations"]

    @property
    def noteheads(self) -> dict:
        """
        Dictionary mapping notehead names to corresponding playback adjustments
        """
        return self["noteheads"]

    @property
    def notations(self) -> dict:
        """
        Dictionary mapping notation names to corresponding playback adjustments
        """
        return self["notations"]

    def set(self, notation_detail: str, adjustment: Union[str, NotePlaybackAdjustment]) -> None:
        """
        Set the given notation detail to have the given :class:`NotePlaybackAdjustment`.
        Based on the name of the notation detail, it is automatically determined whether or not we are talking about
        an articulation, a notehead, or another kind of notation.

        :param notation_detail: name of the notation detail, e.g. "staccato" or "harmonic"
        :param adjustment: the adjustment to make for that notation. Either a :class:`NotePlaybackAdjustment` or a
            string to be parsed to a :class:`NotePlaybackAdjustment` using :code:`NotePlaybackAdjustment.from_string`
        """
        if isinstance(adjustment, str):
            adjustment = NotePlaybackAdjustment.from_string(adjustment)
        if "notehead" in notation_detail:
            notation_detail = notation_detail.replace("notehead", "").replace(" ", "").lower()
        if notation_detail in PlaybackAdjustmentsDictionary.all_noteheads:
            self["noteheads"][notation_detail] = adjustment
        elif notation_detail in PlaybackAdjustmentsDictionary.all_articulations:
            self["articulations"][notation_detail] = adjustment
        elif notation_detail in PlaybackAdjustmentsDictionary.all_notations:
            self["notations"][notation_detail] = adjustment
        else:
            raise ValueError("Playback property not understood.")

    def get(self, notation_detail: str) -> NotePlaybackAdjustment:
        """
        Get the :class:`NotePlaybackAdjustment` for the given notation detail.
        Based on the name of the notation detail, it is automatically determined whether or not we are talking about
        an articulation, a notehead, or another kind of notation.

        :param notation_detail: name of the notation detail, e.g. "staccato" or "harmonic"
        :return: the :class:`NotePlaybackAdjustment` for that detail
        """
        if "notehead" in notation_detail:
            notation_detail = notation_detail.replace("notehead", "").replace(" ", "").lower()
        if notation_detail in PlaybackAdjustmentsDictionary.all_noteheads:
            return self["noteheads"][notation_detail]
        elif notation_detail in PlaybackAdjustmentsDictionary.all_articulations:
            return self["articulations"][notation_detail]
        elif notation_detail in PlaybackAdjustmentsDictionary.all_notations:
            return self["notations"][notation_detail]
        else:
            raise ValueError("Playback property not found.")

    def _to_json(self):
        return {
            key: value._to_json() if hasattr(value, "_to_json")
            else PlaybackAdjustmentsDictionary._to_json(value) if isinstance(value, dict)
            else value for key, value in self.items() if value is not None
        }

    @classmethod
    def _from_json(cls, json_object):
        # convert all adjustments from dictionaries to NotePlaybackAdjustments
        for notation_category in json_object:
            for notation_name in json_object[notation_category]:
                if json_object[notation_category][notation_name] is not None:
                    json_object[notation_category][notation_name] = \
                        NotePlaybackAdjustment._from_json(json_object[notation_category][notation_name])
        return cls(**json_object)

    def __repr__(self):
        return "PlaybackAdjustmentsDictionary(articulations={}, noteheads={}, notations={})".format(
            self["articulations"], self["noteheads"], self["notations"]
        )
