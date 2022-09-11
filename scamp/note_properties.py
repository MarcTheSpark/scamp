"""
Module containing the NoteProperties object, which is a dictionary that stores a variety of playback and notation
options that affect a given note.
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
from .utilities import _is_non_str_sequence
from .playback_adjustments import NotePlaybackAdjustment
from .utilities import SavesToJSON, NoteProperty
from .spelling import SpellingPolicy
from .text import StaffText
from .spanners import Spanner
from expenvelope import Envelope
from copy import deepcopy
from . import _parsing
import re
from types import SimpleNamespace
from typing import Union, MutableMapping


class NoteProperties(SimpleNamespace, SavesToJSON, NoteProperty):
    """
    Class that holds information about any and all playback or notational details for a note or chord aside
    from its pitch, volume and duration. See :ref:`The Note Properties Argument` for more information.

    :param args: Any number of things that are interpretable as note properties via
        :func:`NoteProperties.interpret`, which are merged together into a single object.
    :param kwargs: individual note properties can be given as keyword arguments, e.g. `articulation=staccato`
    """

    # list of all valid kinds of NoteProperties and their attributes
    PROPERTY_TYPES = (
        # "key" is the name of the property as it appears in the NoteProperties namespace/dictionary
        # "regex" is a regular expression, and input key matching this regex is considered to refer to this property
        # "default" is the default value of this property if none is given. (list properties are treated specially:
        #    if given a non-list, it gets wrapped as a list)
        # "regularization_function" is a function to call when receiving an entry for this property, e.g. used to
        #    parse a string into a StaffText object
        # "custom_type" is a custom class associated with this property, such that if we are given one of these custom
        #    classes, we know it's for this property
        # "merger_function": defines what to do with this attribute when merging two NoteProperties
        # "chord_merger_critical": whether this property has to match in order for two notes to merge into a chord
        {
            "key": "articulations",
            "regex": r"^articulations?$",
            "default": [],
            "regularization_function": None,
            "merger_function": lambda p1, p2: p1 + p2,
            "chord_merger_critical": True
        },
        {
            "key": "notations",
            "regex": r"^notations?$",
            "default": [],
            "regularization_function": None,
            "merger_function": lambda p1, p2: p1 + p2,
            "chord_merger_critical": True
        },
        {
            "key": "spanners",
            "regex": r"^spanners?$",
            "default": [],
            "regularization_function": None,
            "custom_type": Spanner,
            "merger_function": lambda p1, p2: p1 + p2,
            "chord_merger_critical": True
        },
        {
            "key": "noteheads",
            "regex": r"^noteheads?$",
            "default": ["normal"],
            "is_default_function": lambda noteheads: all(x == "normal" for x in noteheads),
            "regularization_function": None,
            "merger_function": lambda p1, p2: p1 if p2 == ["normal"] else p2,
            "chord_merger_critical": False
        },
        {
            "key": "dynamics",
            "regex": r"^dynamics?$",
            "default": [],
            "regularization_function": None,
            "merger_function": lambda p1, p2: p1 + p2,
            "chord_merger_critical": True
        },
        {
            "key": "texts",
            "regex": r"^texts?$",
            "default": [],
            "regularization_function": lambda x: StaffText.from_string(x) if isinstance(x, str) else x,
            "custom_type": StaffText,
            "merger_function": lambda p1, p2: p1 + p2,
            "chord_merger_critical": True
        },
        {
            "key": "playback_adjustments",
            "regex": r"^(playback_)?adjustments?$",
            "default": [],
            "regularization_function": lambda x: NotePlaybackAdjustment.from_string(x) if isinstance(x, str) else x,
            "custom_type": NotePlaybackAdjustment,
            "merger_function": lambda p1, p2: p1 + p2,
            "chord_merger_critical": True
        },
        {
            "key": r"spelling_policies",
            "regex": r"^(spelling|spelling_policy|spelling_policies|key)$",
            "default": [],
            "is_default_function": lambda sp: all(x == SpellingPolicy() for x in sp),
            "regularization_function": lambda x: SpellingPolicy.from_string(x) if isinstance(x, str) else x,
            "custom_type": SpellingPolicy,
            "merger_function": lambda p1, p2: p1 + p2,
            "chord_merger_critical": False
        },
        {
            "key": r"voice",
            "regex": r"^voice$",
            "default": None,
            "regularization_function": None,
            "merger_function": lambda p1, p2: p2,
            "chord_merger_critical": True
        },
        {
            "key": "extra_playback_parameters",
            "regex": r"^extra_playback_parameters$",
            "default": {},
            "regularization_function": None,
            "merger_function": lambda p1, p2: {**p1, **p2},
            "chord_merger_critical": True
        },
        {
            "key": "starts_tie",
            "regex": r"^starts_tie$",
            "default": False,
            "regularization_function": None,
            "merger_function": lambda p1, p2: p1,
            "chord_merger_critical": True
        },
        {
            "key": "ends_tie",
            "regex": r"^ends_tie$",
            "default": False,
            "regularization_function": None,
            "merger_function": lambda p1, p2: p2,
            "chord_merger_critical": True
        }
    )

    PROPERTY_TYPES_AS_DICT = {property_info["key"]: property_info for property_info in PROPERTY_TYPES}

    def __init__(self, *args, **kwargs):
        if len(args) > 0:
            arg_properties = NoteProperties.interpret(args)
            if "bundles" in kwargs:
                kwargs.append(arg_properties)
            else:
                kwargs["bundles"] = [arg_properties]

        normalized_kwargs = {}
        for property_info in NoteProperties.PROPERTY_TYPES:
            for key in kwargs:
                if re.match(property_info["regex"], key):
                    # if there's a match in kwargs
                    value = kwargs[key]
                    if _is_non_str_sequence(property_info["default"]):
                        # if it's a container property
                        if not _is_non_str_sequence(kwargs[key]):
                            # ... and we weren't given a container, then put it in a list
                            value = [value]
                        if property_info["regularization_function"] is not None:
                            # If there's a regularization function to call, do it for each element of the list
                            value = [property_info["regularization_function"](x) for x in value]
                    else:
                        # not a container property
                        if property_info["regularization_function"] is not None:
                            # If there's a regularization function to call, do it
                            value = property_info["regularization_function"](value)
                    normalized_kwargs[property_info["key"]] = value
                    break
            else:
                # no match in kwargs make a deep copy of the default (since it's often a list!)
                normalized_kwargs[property_info["key"]] = deepcopy(property_info["default"])

        # pull out any "param_*" keys and store them in the extra playback parameters
        for key in kwargs:
            if key.startswith("param_"):
                param_name, param_value = key[6:], kwargs[key]
                if isinstance(param_value, (list, tuple)):
                    param_value = Envelope.from_list(param_value)
                    param_value.parsed_from_list = True
                normalized_kwargs["extra_playback_parameters"][param_name] = param_value

        super().__init__(**normalized_kwargs)

        # the "bundles" keyword allows us to pass full NoteProperties, which just get incorporated
        if "bundles" in kwargs:
            for note_property in kwargs["bundles"]:
                self.incorporate(note_property)

        self.temp = {}

    @classmethod
    def interpret(cls, properties_object) -> 'NoteProperties':
        """
        Interprets a properties_object of unknown type into a :class:`NoteProperties`.

        :param properties_object: a :class:`NoteProperties` object, dict-like object, parseable
            properties string, custom NoteProperties object or list of any of the above that get merged together.
            See :ref:`The Note Properties Argument` for more info.
        :return: a new :class:`NoteProperties`. Note that if a :class:`NoteProperties` is passed in, the function will
            simply return the exact same object (not a duplicate)
        """
        if isinstance(properties_object, cls):
            return properties_object
        elif properties_object is None:
            return cls()
        elif isinstance(properties_object, MutableMapping):
            return cls(**properties_object)
        elif _is_non_str_sequence(properties_object):
            properties = cls()
            for item in properties_object:
                properties.incorporate(cls.interpret(item))
            return properties
        elif isinstance(properties_object, str):
            return cls(**_parsing.parse_note_properties(properties_object))
        else:
            for property_info in NoteProperties.PROPERTY_TYPES:
                if "custom_type" in property_info and isinstance(properties_object, property_info["custom_type"]):
                    return cls(**{property_info["key"]: properties_object})
            raise ValueError(f"{properties_object} not interpretable as NoteProperties.")

    def incorporate(self, other_properties: Union[SimpleNamespace, MutableMapping, None]) -> 'NoteProperties':
        """
        Incorporates a different NoteProperties or dictionary into this one.

        :param other_properties: A NoteProperties, or a dictionary-like object with similar structure
        :return: self, for chaining purposes
        """
        if other_properties is None:
            return self

        if isinstance(other_properties, MutableMapping):
            other_properties = NoteProperties(**other_properties)

        for property_info in NoteProperties.PROPERTY_TYPES:
            merged_property = property_info["merger_function"](
                getattr(self, property_info["key"]),
                getattr(other_properties, property_info["key"])
            )
            setattr(self, property_info["key"], merged_property)

        return self

    def chord_mergeable_with(self, other_properties: 'NoteProperties') -> bool:
        """
        Determines whether this NoteProperties is compatible with another for chord merger purposes.

        :param other_properties: the NoteProperties object of another note
        :return: whether the note with this NoteProperties is compatible with the note with the other NoteProperties
            as far as combining them both into a chord is concerned.
        """
        return all(getattr(self, property_info["key"]) == getattr(other_properties, property_info["key"])
                   for property_info in NoteProperties.PROPERTY_TYPES if property_info["chord_merger_critical"])

    def apply_playback_adjustments(self, pitch, volume, length, include_notation_derived=True):
        """
        Applies both explicit and (if flag is set) derived playback_adjustments to the given pitch, volume, and length

        :param pitch: unadjusted pitch
        :param volume: unadjusted volume
        :param length: unadjusted length
        :param include_notation_derived: if true, include adjustments based on notations like staccato, by searching
            the playback_settings.adjustments dictionary
        :return: adjusted pitch, volume, length, as well as a boolean stating whether anything changed
        """
        # If the note has a tuple length, indicating adjoined tied segments, we need to replace "length" with the
        # sum of those segments before adjustment and save the segments themselves in "length_segments"
        if hasattr(length, "__len__"):
            length_segments = length
            length = sum(length)
        else:
            length_segments = None

        did_an_adjustment = False
        # first apply all of the explicit playback adjustments
        for adjustment in self.playback_adjustments:
            pitch, volume, length = adjustment.adjust_parameters(pitch, volume, length)
            did_an_adjustment = True

        if include_notation_derived:
            from . import playback_settings
            # try all categories of playback adjustments that are found in the adjustments dictionary and this dict
            for notation_category in set(self.__dict__.keys()).intersection(set(playback_settings.adjustments.keys())):
                for applied_notation in getattr(self, notation_category):
                    notation_derived_adjustment = playback_settings.get_playback_adjustment(applied_notation)
                    if notation_derived_adjustment is not None:
                        assert isinstance(notation_derived_adjustment, NotePlaybackAdjustment)
                        pitch, volume, length = notation_derived_adjustment.adjust_parameters(pitch, volume, length)
                        did_an_adjustment = True

        # Having made the adjustment, if the length was a tuple of adjoined segments, we now go back
        # and scale those according to the adjustment made to length
        if length_segments is not None:
            length_scale_factor = length / sum(length_segments)
            length = length_segments if length_scale_factor == 1 else \
                tuple(segment_length * length_scale_factor for segment_length in length_segments)

        return pitch, volume, length, did_an_adjustment

    def _to_dict(self) -> dict:
        json_friendly_dict = dict(self.__dict__)
        del json_friendly_dict["temp"]

        for property_info in NoteProperties.PROPERTY_TYPES:
            if json_friendly_dict[property_info["key"]] == property_info["default"]:
                del json_friendly_dict[property_info["key"]]

        return json_friendly_dict

    def get_spelling_policy(self, which_note=0):
        return self.spelling_policies[which_note] if which_note < len(self.spelling_policies) \
            else self.spelling_policies[-1]

    def get_midi_cc_params(self):
        return {
            int(k): v
            for k, v in self.extra_playback_parameters.items()
            if k.isdigit() and 0 <= int(k) < 128
        }

    def get_midi_cc_start_values(self, digits_to_round_to=10):
        return {
            k: round(v.start_level() if isinstance(v, Envelope) else v, digits_to_round_to)
            for k, v in self.get_midi_cc_params().items()
        }

    def get_extra_parameter_start_values(self):
        return {
            k: v.start_level() if isinstance(v, Envelope) else v
            for k, v in self.extra_playback_parameters.items()
        }

    @classmethod
    def _from_dict(cls, json_dict):
        return cls(**json_dict)

    def __add__(self, other):
        return self.duplicate().incorporate(other)

    def __repr__(self):
        kwarg_string = ", ".join(
            f"{key}={value}" for key, value in self.__dict__.items()
            if key != "temp" and NoteProperties.PROPERTY_TYPES_AS_DICT[key]["default"] != value
            and ("is_default_function" not in NoteProperties.PROPERTY_TYPES_AS_DICT[key]
                 or not NoteProperties.PROPERTY_TYPES_AS_DICT[key]["is_default_function"](value))
        )
        return f"NoteProperties({kwarg_string})"
