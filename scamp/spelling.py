"""
Module containing the :class:`SpellingPolicy` class, which describes how pitches should be spelled.
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

import functools
from .utilities import SavesToJSON, NoteProperty
from typing import Sequence, Tuple, Union
import pymusicxml


##################################################################################################################
#                                           Spelling-Related Constants
##################################################################################################################


_c_standard_spellings = ((0, 0), (0, 1), (1, 0), (2, -1), (2, 0), (3, 0),
                         (3, 1), (4, 0), (5, -1), (5, 0), (6, -1), (6, 0))
_c_phrygian_spellings = ((0, 0), (1, -1), (1, 0), (2, -1), (2, 0), (3, 0),
                         (3, 1), (4, 0), (5, -1), (5, 0), (6, -1), (6, 0))
_sharp_spellings = ((0, 0), (0, 1), (1, 0), (1, 1), (2, 0), (3, 0), (3, 1), (4, 0), (4, 1), (5, 0), (5, 1), (6, 0))
_flat_spellings = ((0, 0), (1, -1), (1, 0), (2, -1), (2, 0), (3, 0), (4, -1), (4, 0), (5, -1), (5, 0), (6, -1), (6, 0))
_sharp_spellings_even_white_keys = ((6, 1), (0, 1), (0, 2), (1, 1), (1, 2), (2, 1),
                                    (3, 1), (3, 2), (4, 1), (4, 2), (5, 1), (5, 2))
_flat_spellings_even_white_keys = ((1, -2), (1, -1), (2, -2), (2, -1), (3, -1), (4, -2),
                                   (4, -1), (5, -2), (5, -1), (6, -2), (6, -1), (0, -1))
_step_names = ('c', 'd', 'e', 'f', 'g', 'a', 'b')
_step_pitch_classes = (0, 2, 4, 5, 7, 9, 11)
_step_circle_of_fifths_positions = (0, 2, 4, -1, 1, 3, 5)  # number of sharps or flats for the white keys
_sharp_order = (3, 0, 4, 1, 5, 2, 6)  # order in which sharps are added to a key signature
_flat_order = tuple(reversed(_sharp_order))


##################################################################################################################
#                                             SpellingPolicy Class
##################################################################################################################


class SpellingPolicy(SavesToJSON, NoteProperty):

    """
    Object that translates pitches or pitch classes to the actual spelling used in a score

    :param step_alteration_pairs: a list of 12 (step, alteration) tuples showing how to spell each pitch class.
        The step corresponds to the letter-name of the note, and the alteration to its accidental. So (3, -1)
        represents an E-flat.
    :ivar step_alteration_pairs: list of 12 (step, alteration) tuples showing how to spell each pitch class.
    """

    def __init__(self, step_alteration_pairs: Sequence[Tuple[int, int]] = _c_standard_spellings):

        self.step_alteration_pairs = step_alteration_pairs

    """
    Note that functools.lru_cache results in the same classmethod calls returning identical objects
    This is valuable because if we play a bunch of notes with properties="spelling: D major", then each time
    that string is converted to a SpellingPolicy class, it gets to reuse the same instance.
    """

    @classmethod
    @functools.lru_cache()
    def all_sharps(cls, including_white_keys: bool = False) -> 'SpellingPolicy':
        """
        Constructs a sharps-only SpellingPolicy

        :param including_white_keys: if True, even white keys like D will be spelled as C-double-sharp
        """
        return cls(_sharp_spellings_even_white_keys if including_white_keys else _sharp_spellings)

    @classmethod
    @functools.lru_cache()
    def all_flats(cls, including_white_keys: bool = False) -> 'SpellingPolicy':
        """
        Constructs a flats-only SpellingPolicy

        :param including_white_keys: if True, even white keys like D will be spelled as E-double-flat
        """
        return cls(_flat_spellings_even_white_keys if including_white_keys else _flat_spellings)

    @classmethod
    @functools.lru_cache()
    def from_circle_of_fifths_position(cls, num_sharps_or_flats: int, avoid_double_accidentals: bool = False,
                                       template: Sequence[Tuple[int, int]] = _c_standard_spellings) -> 'SpellingPolicy':
        """
        Constructs a spelling policy by transposing a template around the circles of fifths

        :param num_sharps_or_flats: how many steps sharp or flat to transpose around the circle of fifths. For instance,
            if set to 4, our tonic is E, and if set to -3, our tonic is Eb
        :param avoid_double_accidentals: if true, replaces double sharps and flats with simpler spelling
        :param template: by default, uses sharp-2, flat-3, sharp-4, flat-6, and flat-7
        """
        if num_sharps_or_flats == 0:
            return cls(template)

        new_spellings = []
        # translate each step, alteration pair to what it would be in the new key
        for step, alteration in template:
            new_step = (step + 4 * num_sharps_or_flats) % 7
            # new alteration adds to the c alteration (key_alteration // 7) for each time round the circle of fifths
            # and (key_alteration % 7 > sharp_order.index(new_step)) checks to see if we've added this sharp or flat yet
            new_alteration = alteration + num_sharps_or_flats // 7 + \
                             (num_sharps_or_flats % 7 > _sharp_order.index(new_step))

            while avoid_double_accidentals and abs(new_alteration) > 1:
                if new_alteration > 0:
                    new_alteration -= 1 if new_step in (2, 6) else 2
                    new_step = (new_step + 1) % 7
                else:
                    new_alteration += 1 if new_step in (3, 0) else 2
                    new_step = (new_step - 1) % 7
            new_spellings.append((new_step, new_alteration))

        return cls(tuple(sorted(new_spellings, key=lambda x: (template.index((x[0], 0)) + x[1]) % 12)))

    @classmethod
    @functools.lru_cache()
    def from_string(cls, string_initializer: str) -> 'SpellingPolicy':
        """
        Constructs a SpellingPolicy from several possible input string formats

        :param string_initializer: one of the following:
            - a key center (case insensitive), such as "C#" or "f" or "Gb"
            - a key center followed by a mode, such as "g minor" or "Bb locrian". Most modes to not alter the
            way spelling is done, but certain modes like phrygian and locrian do.
            - "flat"/"b" or "sharp"/"#", indicating that any note, even a white key, is to be expressed with the
            specified accidental. Most useful for spelling known individual notes
            - "flats"/"sharps" indicating that black keys will be spelled with the specified accidental, but white
            keys will remain unaltered. (Turns out "flats" is equivalent to "Bb" and "sharps" is equivalent to "A".)
        """
        if string_initializer in ("flat", "b"):
            return SpellingPolicy.all_flats(including_white_keys=True)
        elif string_initializer in ("sharp", "#"):
            return SpellingPolicy.all_sharps(including_white_keys=True)
        elif string_initializer == "flats":
            return SpellingPolicy.all_flats(including_white_keys=False)
        elif string_initializer == "sharps":
            return SpellingPolicy.all_sharps(including_white_keys=False)
        else:
            # most modes don't change anything about how spelling is done, since we default to flat-3, sharp-4,
            # flat-6, and flat-7. The only exceptions are phrygian and locrian, since they have a flat-2 instead of
            # a sharp-1. As a result, we have to use a different template for them.
            string_initializer_processed = string_initializer.lower().replace(" ", "").replace("-", "").\
                replace("_", "").replace("major", "").replace("minor", "").replace("ionian", "").\
                replace("dorian", "").replace("lydian", "").replace("mixolydian", "").replace("aeolean", "")

            if "phrygian" in string_initializer_processed:
                string_initializer_processed = string_initializer_processed.replace("phrygian", "")
                template = _c_phrygian_spellings
            elif "locrian" in string_initializer_processed:
                string_initializer_processed = string_initializer_processed.replace("phrygian", "")
                template = _flat_spellings
            else:
                template = _c_standard_spellings

            try:
                num_sharps_or_flats = \
                    _step_circle_of_fifths_positions[_step_names.index(string_initializer_processed[0])]
            except ValueError:
                raise ValueError("Bad spelling policy initialization string. Use only 'sharp', 'flat', "
                                 "or the name of the desired key center (e.g. 'G#' or 'Db') with optional mode.")

            if string_initializer_processed[1:].startswith(("b", "flat", "f")):
                num_sharps_or_flats -= 7
            elif string_initializer_processed[1:].startswith(("#", "sharp", "s")):
                num_sharps_or_flats += 7
            return SpellingPolicy.from_circle_of_fifths_position(num_sharps_or_flats, template=template)

    @classmethod
    def interpret(cls, obj: Union['SpellingPolicy', str, tuple]) -> 'SpellingPolicy':
        """
        Interpret an object of unknown type as a SpellingPolicy

        :param obj: an object to interpret as a SpellingPolicy; accepts SpellingPolicy, string, or tuple of alterations
        :return: a SpellingPolicy
        """
        if isinstance(obj, SpellingPolicy):
            return obj
        elif isinstance(obj, str):
            return cls.from_string(obj)
        elif isinstance(obj, tuple):
            return cls(tuple(tuple(x) for x in obj))
        else:
            raise ValueError("Spelling policy not understood.")

    def resolve_name_octave_and_alteration(self, midi_num: int) -> Tuple[str, int, int]:
        """
        For a given pitch, determine its name, octave and alteration under this SpellingPolicy.

        :param midi_num: a MIDI pitch value
        :return: a tuple of (name, octave, alteration)
        """
        rounded_midi_num = int(round(midi_num))
        octave = int(rounded_midi_num / 12) - 1
        pitch_class = rounded_midi_num % 12
        step, alteration = self.step_alteration_pairs[pitch_class]
        if _step_pitch_classes[step] + alteration < 0:
            # if we have Cb, the octave will be interpreted incorrectly from the midi number, so we compensate
            octave += 1
        elif _step_pitch_classes[step] + alteration > 11:
            # same kind of correction, but for B#
            octave -= 1
        name = _step_names[step]
        # add back in any potential quarter tonal deviation
        # (round the different between midi_num and rounded_midi_num to the nearest multiple of 0.5)
        if rounded_midi_num != midi_num:
            alteration += round(2 * (midi_num - rounded_midi_num)) / 2
        return name, octave, alteration

    def resolve_abjad_pitch(self, midi_num: int) -> 'abjad.NamedPitch':
        """
        Convert a given MIDI pitch to an abjad NamedPitch according to this SpellingPolicy

        :param midi_num: a MIDI pitch value
        """
        from scamp._dependencies import abjad
        name, octave, alteration = self.resolve_name_octave_and_alteration(midi_num)
        return abjad().NamedPitch(name, accidental=alteration, octave=octave)

    def resolve_music_xml_pitch(self, midi_num: int) -> 'pymusicxml.Pitch':
        """
        Convert a given MIDI pitch to an abjad pymusicxml Pitch object according to this SpellingPolicy

        :param midi_num: a MIDI pitch value
        """
        name, octave, alteration = self.resolve_name_octave_and_alteration(midi_num)
        return pymusicxml.Pitch(name.upper(), octave, alteration)

    def _to_dict(self) -> dict:
        # check to see this SpellingPolicy is identical to one made from one of the following string initializers
        # if so, save it that way instead, for simplicity
        for string_initializer in ("C", "G", "D", "A", "E", "B", "F#", "Db", "Ab", "Eb", "Bb", "F", "b", "#"):
            if self.step_alteration_pairs == SpellingPolicy.from_string(string_initializer).step_alteration_pairs:
                return {"key": string_initializer}
        # otherwise, save the entire spelling
        return {"step_alterations": self.step_alteration_pairs}

    @classmethod
    def _from_dict(cls, json_dict):
        if "key" in json_dict:
            return cls.from_string(json_dict["key"])
        return cls(json_dict["step_alterations"])

    def __repr__(self):
        return "SpellingPolicy({})".format(self.step_alteration_pairs)
