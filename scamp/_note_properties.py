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

from .playback_adjustments import NotePlaybackAdjustment, PlaybackAdjustmentsDictionary
from .utilities import SavesToJSON
from .settings import playback_settings, engraving_settings
from .spelling import SpellingPolicy
from .text import StaffText
from expenvelope import Envelope
from copy import deepcopy
import logging
import json
from collections import UserDict


def _split_string_at_outer_commas(s):
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
        elif character == "," and paren_count == square_count == curly_count == 0:
            out.append(s[last_split:i-1].strip())
            last_split = i
    out.append(s[last_split:].strip())
    return out


class NotePropertiesDictionary(UserDict, SavesToJSON):

    def __init__(self, **kwargs):
        NotePropertiesDictionary._normalize_dictionary_keys(kwargs)
        super().__init__(**kwargs)
        self._convert_params_to_envelopes_if_needed()
        self._validate_values()

    @staticmethod
    def _normalize_dictionary_keys(dictionary):
        NotePropertiesDictionary._standardize_plural_key("articulations", dictionary)
        NotePropertiesDictionary._standardize_plural_key("noteheads", dictionary)
        if len(dictionary["noteheads"]) == 0:
            dictionary["noteheads"] = ["normal"]
        NotePropertiesDictionary._standardize_plural_key("notations", dictionary)
        NotePropertiesDictionary._standardize_plural_key("texts", dictionary)
        NotePropertiesDictionary._standardize_plural_key("playback_adjustments", dictionary)

        for i, adjustment in enumerate(dictionary["playback_adjustments"]):
            if isinstance(adjustment, str):
                dictionary["playback_adjustments"][i] = NotePlaybackAdjustment.from_string(adjustment)

        if "spelling_policy" not in dictionary:
            dictionary["spelling_policy"] = None

        if "temp" not in dictionary:
            # this is a throwaway directory that is not kept when we save to json
            dictionary["temp"] = {}
        return dictionary

    @staticmethod
    def _standardize_plural_key(key_name, dictionary):
        """
        Makes sure that the given entry exists in a plural form (e.g. "texts" instead of "text") and that
        it points to a list of items.
        """
        if key_name not in dictionary:
            if key_name[:-1] in dictionary:
                # the non-plural version is there, so convert to the standard plural version
                dictionary[key_name] = dictionary[key_name[:-1]]
                del dictionary[key_name[:-1]]
            else:
                dictionary[key_name] = []
        if not isinstance(dictionary[key_name], (list, tuple)):
            dictionary[key_name] = [dictionary[key_name]]

    def _validate_values(self):
        validated_articulations = []
        for articulation in self["articulations"]:
            if articulation in PlaybackAdjustmentsDictionary.all_articulations:
                validated_articulations.append(articulation)
            else:
                logging.warning("Articulation {} not understood".format(articulation))
        self["articulations"] = validated_articulations

        validated_noteheads = []
        for notehead in self["noteheads"]:
            if notehead in PlaybackAdjustmentsDictionary.all_noteheads:
                validated_noteheads.append(notehead)
            else:
                logging.warning("Notehead {} not understood".format(notehead))
                validated_noteheads.append("normal")
        self["noteheads"] = validated_noteheads

        validated_notations = []
        for notation in self["notations"]:
            if notation in PlaybackAdjustmentsDictionary.all_notations:
                validated_notations.append(notation)
            else:
                logging.warning("Notation {} not understood".format(notation))
        self["notations"] = validated_notations

        validated_playback_adjustments = []
        for playback_adjustment in self["playback_adjustments"]:
            if isinstance(playback_adjustment, NotePlaybackAdjustment):
                validated_playback_adjustments.append(playback_adjustment)
            elif isinstance(playback_adjustment, str):
                validated_playback_adjustments.append(NotePlaybackAdjustment.from_string(playback_adjustment))
            else:
                logging.warning("Playback adjustment {} not understood".format(playback_adjustment))
        self["playback_adjustments"] = validated_playback_adjustments

        if self["spelling_policy"] is not None and not isinstance(self["spelling_policy"], SpellingPolicy):
            try:
                if not isinstance("spelling_policy", str):
                    raise ValueError()
                self["spelling_policy"] = SpellingPolicy.from_string(self["spelling_policy"])
            except ValueError:
                logging.warning("Spelling policy \"{}\" not understood".format(self["spelling_policy"]))
                self["spelling_policy"] = None

        validated_texts = []
        for text in self["texts"]:
            if isinstance(text, StaffText):
                validated_texts.append(text)
            elif isinstance(text, str):
                validated_texts.append(StaffText.from_string(text))
            else:
                logging.warning("Staff text \"{}\" not understood".format(self["text"]))
        self["texts"] = validated_texts

    @classmethod
    def from_unknown_format(cls, properties):
        """
        Interprets a number of data formats as a NotePropertiesDictionary

        :param properties: can be of several formats:
            - a dictionary of note properties, using the standard format
            - a list of properties, each of which is a string or a NotePlaybackAdjustment. Each string may be
            colon-separated key / value pair (e.g. "articulation: staccato"), or simply the value (e.g. "staccato"),
            in which case an attempt is made to guess the key.
            - a string of comma-separated properties, which just gets split and treated like a list
            - a NotePlaybackAdjustment, which just put in a list and treated like a list input
        :return: a newly constructed NotePropertiesDictionary
        """
        if isinstance(properties, str):
            return NotePropertiesDictionary.from_string(properties)
        elif isinstance(properties, (SpellingPolicy, NotePlaybackAdjustment, StaffText)):
            return NotePropertiesDictionary.from_list([properties])
        elif isinstance(properties, list):
            return NotePropertiesDictionary.from_list(properties)
        elif properties is None:
            return cls()
        else:
            if not isinstance(properties, dict):
                raise ValueError("Properties argument wrongly formatted.")
            return cls(**properties)

    @classmethod
    def from_string(cls, properties_string):
        assert isinstance(properties_string, str)
        return NotePropertiesDictionary.from_list(_split_string_at_outer_commas(properties_string))

    @classmethod
    def from_list(cls, properties_list):
        assert isinstance(properties_list, (list, tuple))
        # this pre-populates the dict with all of the key/value pairs we need
        properties_dict = NotePropertiesDictionary._normalize_dictionary_keys({})

        for note_property in properties_list:
            if isinstance(note_property, NotePlaybackAdjustment):
                properties_dict["playback_adjustments"].append(note_property)
            elif isinstance(note_property, SpellingPolicy):
                properties_dict["spelling_policy"] = note_property
            elif isinstance(note_property, StaffText):
                properties_dict["texts"].append(note_property)
            elif isinstance(note_property, str):
                # if there's a colon, it represents a key/value pair, e.g. "articulation: staccato"
                if ":" in note_property:
                    colon_index = note_property.index(":")
                    key, value = note_property[:colon_index].replace(" ", "").lower(), \
                                 note_property[colon_index+1:].strip().lower()
                else:
                    # otherwise, leave the key undecided for now
                    key = None
                    value = note_property.strip().lower()

                # split values into a list based on the slash delimiter
                values = [x.strip() for x in value.split("/")]

                if key is None:
                    # if we weren't given a key/value pair, try to find it now
                    if values[0] in PlaybackAdjustmentsDictionary.all_articulations:
                        key = "articulations"
                    elif values[0] in PlaybackAdjustmentsDictionary.all_noteheads:
                        key = "noteheads"
                    elif values[0] in PlaybackAdjustmentsDictionary.all_notations:
                        key = "notations"
                    elif values[0] in ("#", "b", "sharps", "flats"):
                        key = "spelling_policy"
                    elif "volume" in values[0] or "pitch" in values[0] or "length" in values[0]:
                        key = "playback_adjustments"
                    else:
                        raise ValueError("Note property {} not understood".format(note_property))

                if key in "articulations":  # note that this allows the singular "articulation" too
                    properties_dict["articulations"].extend(values)

                elif key in "noteheads":  # note that this allows the singular "notehead" too
                    properties_dict["noteheads"] = values

                elif key in "notations":  # note that this allows the singular "notation" too
                    properties_dict["notations"].extend(values)

                elif key in "playback_adjustments":  # note that this allows the singular "playback_adjustment" too
                    properties_dict["playback_adjustments"].extend(values)

                elif key in ("key", "spelling", "spellingpolicy", "spelling_policy"):
                    properties_dict["spelling_policy"] = value

                elif key.startswith("param_") or key.endswith("_param"):
                    if not len(values) == 1:
                        raise ValueError("Cannot have multiple values for a parameter property.")
                    properties_dict[key] = json.loads(value)

                elif key == "voice":
                    if not len(values) == 1:
                        raise ValueError("Cannot have multiple values for a voice property.")
                    properties_dict["voice"] = value

                elif key in "texts":  # note that this allows the singular "text" too
                    # note that do .append(value), instead of .extend(values), because a text could have a
                    # slash in it and we don't want it to be multiple texts.
                    properties_dict["texts"].append(value)

        return cls(**properties_dict)

    def _convert_params_to_envelopes_if_needed(self):
        # if we've been given extra parameters of playback, and their values are envelopes written as lists, etc.
        # this converts them all to Envelope objects
        for key, value in self.items():
            if (key.startswith("param_") or key.endswith("_param")) and isinstance(value, (list, tuple)):
                self[key] = Envelope.from_list(value)

    @property
    def articulations(self):
        return self["articulations"]

    @articulations.setter
    def articulations(self, value):
        self["articulations"] = value

    @property
    def noteheads(self):
        return self["noteheads"]

    @noteheads.setter
    def noteheads(self, value):
        self["noteheads"] = value

    @property
    def notations(self):
        return self["notations"]

    @notations.setter
    def notations(self, value):
        self["notations"] = value

    @property
    def texts(self):
        return self["texts"]

    @texts.setter
    def texts(self, value):
        self["texts"] = value

    @property
    def playback_adjustments(self):
        return self["playback_adjustments"]

    @playback_adjustments.setter
    def playback_adjustments(self, value):
        self["playback_adjustments"] = value

    @property
    def spelling_policy(self):
        return self["spelling_policy"] if self["spelling_policy"] is not None \
            else engraving_settings.default_spelling_policy

    @spelling_policy.setter
    def spelling_policy(self, value):
        if isinstance(value, SpellingPolicy):
            self["spelling_policy"] = value
        elif isinstance(value, str):
            self["spelling_policy"] = SpellingPolicy.from_string(value)
        elif hasattr(value, "__len__") and len(value) == 12 and \
                all(hasattr(x, "__len__") and len(x) == 2 for x in value):
            self["spelling_policy"] = tuple(tuple(x) for x in value)
        else:
            raise ValueError("Spelling policy not understood.")

    @property
    def voice(self):
        if "voice" in self:
            return self["voice"]
        else:
            return None

    def iterate_extra_parameters_and_values(self):
        for key, value in self.items():
            if key.startswith("param_") or key.endswith("_param"):
                yield key.replace("param_", "").replace("_param", ""), value

    def starts_tie(self):
        return "_starts_tie" in self and self["_starts_tie"]

    def ends_tie(self):
        return "_ends_tie" in self and self["_ends_tie"]

    @property
    def temp(self):
        return self["temp"]

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
            assert isinstance(adjustment, NotePlaybackAdjustment)
            pitch, volume, length = adjustment.adjust_parameters(pitch, volume, length)
            did_an_adjustment = True

        if include_notation_derived:
            for notation_category in ["articulations", "noteheads", "notations"]:
                for applied_notation in self[notation_category]:
                    notation_derived_adjustment = playback_settings.adjustments.get(applied_notation)
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

    def mergeable_with(self, other_properties_dict):
        assert isinstance(other_properties_dict, NotePropertiesDictionary)
        return self.articulations == other_properties_dict.articulations and \
               self.notations == other_properties_dict.notations and \
               self.playback_adjustments == other_properties_dict.playback_adjustments and \
               self.texts == other_properties_dict.texts

    def _to_dict(self) -> dict:
        json_friendly_dict = dict(deepcopy(self))
        del json_friendly_dict["temp"]

        # remove entries that contain no information for conciseness. They will be reconstructed when reloading.
        if len(self.articulations) == 0:
            del json_friendly_dict["articulations"]
        if len(self.noteheads) == 1 and self.noteheads[0] == "normal":
            del json_friendly_dict["noteheads"]
        if len(self.notations) == 0:
            del json_friendly_dict["notations"]
        if len(self.texts) == 0:
            del json_friendly_dict["texts"]
        if len(self.playback_adjustments) == 0:
            del json_friendly_dict["playback_adjustments"]
        if self["spelling_policy"] is None:
            del json_friendly_dict["spelling_policy"]

        return json_friendly_dict

    @classmethod
    def _from_dict(cls, json_dict):
        return cls(**json_dict)

    def __repr__(self):
        # this simplifies the properties dictionary to only the parts that deviate from the defaults
        return repr(self._to_dict())
