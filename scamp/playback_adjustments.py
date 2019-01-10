from .utilities import SavesToJSON
from .engraving_translations import *


# TODO: would be great if this included preset switches


class ParamPlaybackAdjustment(SavesToJSON):

    def __init__(self, multiply=1, add=0):
        self.multiply = multiply
        self.add = add

    @classmethod
    def set_to(cls, value):
        return cls(0, value)

    @classmethod
    def scale(cls, value):
        return cls(value)

    def adjust_value(self, param_value):
        # in case the param value is a Envelope, it's best to leave out the multiply if it's zero
        # for instance, if param_value is a Envelope, multiply is zero and add is a Envelope,
        # you would end up trying to add two Envelopes, which we don't allow
        return self.add if self.multiply == 0 else param_value * self.multiply + self.add

    def to_json(self):
        return self.__dict__

    @classmethod
    def from_json(cls, json_object):
        return cls(**json_object)

    def __repr__(self):
        return "PlaybackParamAdjustment({}, {})".format(self.multiply, self.add)


class NotePlaybackAdjustment(SavesToJSON):

    def __init__(self, pitch_adjustment=None, volume_adjustment=None, length_adjustment=None):
        assert pitch_adjustment is None or isinstance(pitch_adjustment, ParamPlaybackAdjustment)
        assert volume_adjustment is None or isinstance(volume_adjustment, ParamPlaybackAdjustment)
        assert length_adjustment is None or isinstance(length_adjustment, ParamPlaybackAdjustment)
        self.pitch_adjustment = pitch_adjustment
        self.volume_adjustment = volume_adjustment
        self.length_adjustment = length_adjustment

    @classmethod
    def scale_params(cls, pitch_scale=1, volume_scale=1, length_scale=1):
        """Constructs a NotePlaybackAdjustment that scales the parameters"""
        return cls(ParamPlaybackAdjustment.scale(pitch_scale) if pitch_scale != 1 else None,
                   ParamPlaybackAdjustment.scale(volume_scale) if volume_scale != 1 else None,
                   ParamPlaybackAdjustment.scale(length_scale) if length_scale != 1 else None)

    @classmethod
    def set_params(cls, pitch=None, volume=None, length=None):
        """Constructs a NotePlaybackAdjustment that directly resets the parameters"""
        return cls(ParamPlaybackAdjustment.set_to(pitch) if pitch is not None else None,
                   ParamPlaybackAdjustment.set_to(volume) if volume is not None else None,
                   ParamPlaybackAdjustment.set_to(length) if length is not None else None)

    def adjust_parameters(self, pitch, volume, length):
        return self.pitch_adjustment.adjust_value(pitch) if self.pitch_adjustment is not None else pitch, \
               self.volume_adjustment.adjust_value(volume) if self.volume_adjustment is not None else volume, \
               self.length_adjustment.adjust_value(length) if self.length_adjustment is not None else length

    def to_json(self):
        json_dict = {}
        if self.pitch_adjustment is not None:
            json_dict["pitch_adjustment"] = self.pitch_adjustment.to_json()
        if self.volume_adjustment is not None:
            json_dict["volume_adjustment"] = self.volume_adjustment.to_json()
        if self.length_adjustment is not None:
            json_dict["length_adjustment"] = self.length_adjustment.to_json()
        return json_dict

    @classmethod
    def from_json(cls, json_object):
        return cls(**{
            adjustment_name: ParamPlaybackAdjustment.from_json(json_object[adjustment_name])
            for adjustment_name in json_object
        })

    def __repr__(self):
        return "NotePlaybackAdjustment({}, {}, {})".format(
            self.pitch_adjustment, self.volume_adjustment, self.length_adjustment
        )


class PlaybackDictionary(dict, SavesToJSON):

    all_articulations = list(articulation_to_xml_element_name.keys())
    all_noteheads = list(notehead_name_to_xml_type.keys())
    all_noteheads.extend(["filled " + notehead_name for notehead_name in all_noteheads])
    all_noteheads.extend(["open " + notehead_name for notehead_name in all_noteheads
                          if not notehead_name.startswith("filled")])
    all_notations = list(notations_to_xml_notations_element.keys())

    def __init__(self, **kwargs):
        # make sure there is an entry for every notehead and articulation
        if "articulations" not in kwargs:
            kwargs["articulations"] = {x: None for x in PlaybackDictionary.all_articulations}
        else:
            kwargs["articulations"] = {x: kwargs["articulations"][x] if x in kwargs["articulations"] else None
                                       for x in PlaybackDictionary.all_articulations}
        if "noteheads" not in kwargs:
            kwargs["noteheads"] = {x: None for x in PlaybackDictionary.all_noteheads}
        else:
            kwargs["noteheads"] = {x: kwargs["noteheads"][x] if x in kwargs["noteheads"] else None
                                   for x in PlaybackDictionary.all_noteheads}
        if "notations" not in kwargs:
            kwargs["notations"] = {x: None for x in PlaybackDictionary.all_notations}
        else:
            kwargs["notations"] = {x: kwargs["notations"][x] if x in kwargs["notations"] else None
                                   for x in PlaybackDictionary.all_notations}

        super().__init__(**kwargs)

    def set(self, playback_property: str, adjustment: NotePlaybackAdjustment):
        if "notehead" in playback_property:
            playback_property = playback_property.replace("notehead", "").replace(" ", "").lower()
        if playback_property in PlaybackDictionary.all_noteheads:
            self["noteheads"][playback_property] = adjustment
        elif playback_property in PlaybackDictionary.all_articulations:
            self["articulations"][playback_property] = adjustment
        elif playback_property in PlaybackDictionary.all_notations:
            self["notations"][playback_property] = adjustment
        else:
            raise ValueError("Playback property not understood.")

    def get(self, playback_property: str):
        if "notehead" in playback_property:
            playback_property = playback_property.replace("notehead", "").replace(" ", "").lower()
        if playback_property in PlaybackDictionary.all_noteheads:
            return self["noteheads"][playback_property]
        elif playback_property in PlaybackDictionary.all_articulations:
            return self["articulations"][playback_property]
        elif playback_property in PlaybackDictionary.all_notations:
            return self["notations"][playback_property]
        else:
            raise ValueError("Playback property not found.")

    def to_json(self):
        return {
            key: value.to_json() if hasattr(value, "to_json")
            else PlaybackDictionary.to_json(value) if isinstance(value, dict)
            else value for key, value in self.items() if value is not None
        }

    @classmethod
    def from_json(cls, json_object):
        # convert all adjustments from dictionaries to NotePlaybackAdjustments
        for notation_category in json_object:
            for notation_name in json_object[notation_category]:
                if json_object[notation_category][notation_name] is not None:
                    json_object[notation_category][notation_name] = \
                        NotePlaybackAdjustment.from_json(json_object[notation_category][notation_name])
        return cls(**json_object)

    def __repr__(self):
        return "PlaybackDictionary(articulations={}, noteheads={}, notations={})".format(
            self["articulations"], self["noteheads"], self["notations"]
        )
