from .playback_adjustments import *
from .utilities import SavesToJSON
from .settings import playback_settings, engraving_settings
from .spelling import SpellingPolicy
from expenvelope import Envelope
from copy import deepcopy
import logging
import json


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


class NotePropertiesDictionary(dict, SavesToJSON):

    def __init__(self, **kwargs):
        if "articulations" not in kwargs:
            kwargs["articulations"] = []
        if "noteheads" not in kwargs:
            kwargs["noteheads"] = ["normal"]
        if "notations" not in kwargs:
            kwargs["notations"] = []
        if "text" not in kwargs:
            kwargs["text"] = []
        if "playback adjustments" not in kwargs:
            kwargs["playback adjustments"] = []
        if "spelling_policy" not in kwargs:
            kwargs["spelling_policy"] = None
        if "temp" not in kwargs:
            # this is a throwaway directory that is not kept when we save to json
            kwargs["temp"] = {}

        super().__init__(**kwargs)
        self._convert_params_to_envelopes_if_needed()

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
        elif isinstance(properties, NotePlaybackAdjustment):
            return NotePropertiesDictionary.from_list([properties])
        elif isinstance(properties, list):
            return NotePropertiesDictionary.from_list(properties)
        elif properties is None:
            return cls()
        else:
            assert isinstance(properties, dict), "Properties argument wrongly formatted."
            return cls(**properties)

    @classmethod
    def from_string(cls, properties_string):
        assert isinstance(properties_string, str)
        return NotePropertiesDictionary.from_list(_split_string_at_outer_commas(properties_string))

    @classmethod
    def from_list(cls, properties_list):
        assert isinstance(properties_list, (list, tuple))
        properties_dict = cls()

        for note_property in properties_list:
            if isinstance(note_property, NotePlaybackAdjustment):
                properties_dict["playback adjustments"].append(note_property)
            elif isinstance(note_property, str):
                # if there's a colon, it represents a key / value pair, e.g. "articulation: staccato"
                if ":" in note_property:
                    colon_index = note_property.index(":")
                    key, value = note_property[:colon_index].replace(" ", "").lower(), \
                                 note_property[colon_index+1:].strip().lower()
                    if key in ("articulation", "articulations"):
                        if value in PlaybackDictionary.all_articulations:
                            properties_dict["articulations"].append(value)
                        else:
                            logging.warning("Articulation {} not understood".format(value))
                    elif key == "noteheads":
                        # For specifying multiple different notehead types in a chord, use the plural key "noteheads"
                        # and specify the types separated by forward slashes
                        properties_dict["noteheads"] = []
                        for notehead in value.split("/"):
                            notehead = notehead.strip()
                            if notehead in PlaybackDictionary.all_noteheads:
                                properties_dict["noteheads"].append(notehead)
                            else:
                                properties_dict["noteheads"].append("normal")
                                logging.warning("Notehead {} not understood".format(notehead))
                    elif key == "notehead":
                        # (for a chord, this sets all noteheads to the same type)
                        if value in PlaybackDictionary.all_noteheads:
                            properties_dict["noteheads"] = [value]
                        else:
                            logging.warning("Notehead {} not understood".format(value))
                    elif key in ("notation", "notations"):
                        if value in PlaybackDictionary.all_notations:
                            properties_dict["notations"].append(value)
                        else:
                            logging.warning("Notation {} not understood".format(value))
                    elif key in ("key", "spelling", "spellingpolicy", "spelling_policy", "spell"):
                        try:
                            properties_dict["spelling_policy"] = SpellingPolicy.from_string(value)
                        except ValueError:
                            logging.warning("Spelling policy \"{}\" not understood".format(value))
                    elif key.startswith("param_") or key.endswith("_param"):
                        properties_dict[key] = json.loads(value)
                    elif key == "voice":
                        properties_dict["voice"] = value
                else:
                    # otherwise, we try to figure out what kind of property we're dealing with
                    note_property = note_property.replace(" ", "")
                    if note_property in PlaybackDictionary.all_articulations:
                        properties_dict["articulations"].append(note_property)
                    elif note_property in PlaybackDictionary.all_noteheads:
                        properties_dict["noteheads"] = [note_property]
                    elif note_property in PlaybackDictionary.all_notations:
                        properties_dict["notations"].append(note_property)
                    elif note_property in ("#", "b", "sharps", "flats"):
                        properties_dict["spelling_policy"] = SpellingPolicy.from_string(note_property)

        properties_dict._convert_params_to_envelopes_if_needed()
        return properties_dict

    def _convert_params_to_envelopes_if_needed(self):
        # if we've been given extra parameters of playback, and their values are envelopes written as lists, etc.
        # this converts them all to Envelope objects
        for key, value in self.items():
            if key.startswith("param_") or key.endswith("_param") and hasattr(value, "__len__"):
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
    def text(self):
        return self["text"]

    @text.setter
    def text(self, value):
        self["text"] = value

    @property
    def playback_adjustments(self):
        return self["playback adjustments"]

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
        Applies both explicit and (if flag is set) derived playback adjustments to the given pitch, volume, and length
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
               self.text == other_properties_dict.text

    def to_json(self):
        json_friendly_dict = dict(deepcopy(self))
        json_friendly_dict["playback adjustments"] = [x.to_json() for x in self.playback_adjustments]
        del json_friendly_dict["temp"]

        # remove entries that contain no information for conciseness. They will be reconstructed when reloading.
        if len(self.articulations) == 0:
            del json_friendly_dict["articulations"]
        if len(self.noteheads) == 1 and self.noteheads[0] == "normal":
            del json_friendly_dict["noteheads"]
        if len(self.notations) == 0:
            del json_friendly_dict["notations"]
        if len(self.text) == 0:
            del json_friendly_dict["text"]
        if len(self.playback_adjustments) == 0:
            del json_friendly_dict["playback adjustments"]
        if self["spelling_policy"] is None:
            del json_friendly_dict["spelling_policy"]

        return json_friendly_dict

    @classmethod
    def from_json(cls, json_object):
        # if the object has playback adjustments convert all adjustments from dictionaries to NotePlaybackAdjustments
        if "playback adjustments" in json_object:
            json_object["playback adjustments"] = [NotePlaybackAdjustment.from_json(x)
                                                   for x in json_object["playback adjustments"]]
        if "spelling_policy" in json_object:
            json_object["spelling_policy"] = SpellingPolicy.from_json(json_object["spelling_policy"])
        return cls(**json_object)

    def __repr__(self):
        # this simplifies the properties dictionary to only the parts that deviate from the defaults
        return repr(self.to_json())
