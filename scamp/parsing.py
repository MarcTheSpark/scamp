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

from . import _engraving_translations
from expenvelope import Envelope
from arpeggio.cleanpeg import ParserPEG
from arpeggio import visit_parse_tree, PTNodeVisitor, NoMatch
import pymusicxml


def _join_with_quotes_and_slashes(list_of_strings):
    return " / ".join('"{}"'.format(x) for x in list_of_strings)


grammar = r"""
number = r'[+-]?([0-9]*[.])?[0-9]+'
list_expression = "[" (list_expression / number) ("," (list_expression / number))* "]"
number_or_list = list_expression / number

param_playback_adjustment = ("*" number_or_list r'[+-]' number_or_list) / (r'[=*+-]' number_or_list)
note_playback_adjustment = r'pitch|volume|length' param_playback_adjustment ("," r'pitch|volume|length' param_playback_adjustment)*
playback_adjustments_key = r'playback_adjustments?' ":"
playback_adjustments = playback_adjustments_key? note_playback_adjustment + ("/" note_playback_adjustment)*

articulations_key = r'articulations?' ":"
articulation_value = {all_articulations}
articulations = articulations_key? articulation_value ("/" articulation_value)*

notations_key = r'notations?' ":"
notation_value = {all_notations}
notations = notations_key? notation_value ("/" notation_value)*

noteheads_key = r'noteheads?' ":"
notehead_value = {all_noteheads}
noteheads = noteheads_key? notehead_value ("/" notehead_value)*

dynamics_key = r'dynamics?' ":"
dynamics_value = ({all_dynamics}) &("," / EOF)
dynamics = dynamics_key? dynamics_value ("/" dynamics_value)*

texts_key = r'texts?' ":"
text_expression = r'\'.*\'' / r'\".*\"' / r'[^,:]+'
texts = texts_key? text_expression ("/" text_expression)*

accidental = r'sharp|flat|[#bsf]'
white_key = r'[a-fA-F]'
mode = "major" / "minor" / "ionian" / "dorian" / "phrygian" / "lydian" / "mixolydian" / "aeolean" / "locrian"
spelling_policy_key = ("spelling" / "spelling_policy" / "key") ":"
tonality = (white_key r'[-_]*' accidental? r'[-_]*' mode?)
spelling_policy = spelling_policy_key? ("flats" / "sharps" / accidental / tonality) &("," / EOF)

voice = "voice" ":" r'[^,]*' &("," / EOF)

extra_playback_parameter = r'param_\w+' ":" number_or_list

property = articulations / notations / noteheads / playback_adjustments / spelling_policy / 
           dynamics / extra_playback_parameter / voice / texts
properties = property ("," property)* EOF
""".format(
    # Note: we reverse the lists of articulations, notations, and noteheads so that items like "tremolo3" are searched
    # before "tremolo". This way is doesn't match the "tremolo" part of "tremolo3", and then throw an error at the "3"
    all_articulations=_join_with_quotes_and_slashes(sorted(_engraving_translations.all_articulations, reverse=True)),
    all_notations=_join_with_quotes_and_slashes(sorted(_engraving_translations.all_notations, reverse=True)),
    all_noteheads=_join_with_quotes_and_slashes(sorted(_engraving_translations.all_noteheads, reverse=True)),
    all_dynamics=_join_with_quotes_and_slashes(sorted(pymusicxml.Dynamic.STANDARD_TYPES, reverse=True))
)


class PropertiesVisitor(PTNodeVisitor):

    def visit_number(self, node, children):
        return eval(str(node))

    def visit_list_expression(self, node, children):
        return [eval(x) if isinstance(x, str) else x for x in children]

    def visit_number_or_list(self, node, children):
        if isinstance(children[0], list):
            env = Envelope.from_list(children[0])
            env.parsed_from_list = True
            return env
        else:
            return children[0]

    def visit_playback_adjustments_key(self, node, children): return None

    def visit_articulations_key(self, node, children): return None

    def visit_notations_key(self, node, children): return None

    def visit_noteheads_key(self, node, children): return None

    def visit_dynamics_key(self, node, children): return None

    def visit_spelling_policy_key(self, node, children): return None

    def visit_texts_key(self, node, children): return None

    def visit_articulations(self, node, children): return {"articulations": list(children)}

    def visit_notations(self, node, children): return {"notations": list(children)}

    def visit_noteheads(self, node, children): return {"noteheads": list(children)}

    def visit_dynamics(self, node, children): return {"dynamics": list(children)}

    def visit_extra_playback_parameter(self, node, children): return {children[0]: children[-1]}

    def visit_texts(self, node, children):
        from .text import StaffText
        text_expressions = [
            text_expression[1:-1] if text_expression.startswith("'") and text_expression.endswith("'")
                                     or text_expression.startswith('"') and text_expression.endswith('"')
            else text_expression for text_expression in children
        ]
        return {"text": [StaffText.from_string(te) for te in text_expressions]}

    def visit_playback_adjustments(self, node, children): return {"playback_adjustments": list(children)}

    def visit_note_playback_adjustment(self, node, children):
        from .playback_adjustments import NotePlaybackAdjustment
        pitch_adjustment = volume_adjustment = length_adjustment = None
        for which_param, adjustment in zip(children[::2], children[1::2]):
            if which_param == "pitch":
                pitch_adjustment = adjustment
            elif which_param == "volume":
                volume_adjustment = adjustment
            elif which_param == "length":
                length_adjustment = adjustment
        return NotePlaybackAdjustment(pitch_adjustment=pitch_adjustment, volume_adjustment=volume_adjustment,
                                      length_adjustment=length_adjustment, scale_envelopes_to_length=True)

    def visit_param_playback_adjustment(self, node, children):
        from .playback_adjustments import ParamPlaybackAdjustment
        if children[0] == "*":
            return ParamPlaybackAdjustment(multiply=children[1])
        elif children[0] == "+":
            return ParamPlaybackAdjustment(add=children[1])
        elif children[0] == "-":
            return ParamPlaybackAdjustment(add=-children[1])
        elif children[0] == "=":
            return ParamPlaybackAdjustment(multiply=0, add=children[1])
        else:
            # it's the * and +/- one, but the * has been taken out, since it's a literals
            return ParamPlaybackAdjustment(multiply=children[0],
                                           add=-children[2] if children[1] == "-" else children[2])

    def visit_tonality(self, node, children):
        return "".join(term for term in children if "-" not in term and "_" not in term)

    def visit_spelling_policy(self, node, children):
        from .spelling import SpellingPolicy
        return {"spelling_policy": SpellingPolicy.from_string(children[0])}

    def visit_voice(self, node, children):
        return {"voice": children[-1]}

    def visit_properties(self, node, children):
        return PropertiesVisitor.merge_dicts(*children)

    @staticmethod
    def merge_dicts(*dicts):
        out = {}
        for d in dicts:
            for key in d:
                if key in out and isinstance(out[key], list):
                    out[key].extend(d[key])
                else:
                    out[key] = d[key]
        return out


_properties_parser = ParserPEG(grammar, "properties")
_properties_visitor = PropertiesVisitor()


def parse_note_properties(note_properties_string):
    parse_tree = _properties_parser.parse(note_properties_string)
    properties_dict = visit_parse_tree(parse_tree, _properties_visitor)
    if "noteheads" not in properties_dict:
        properties_dict["noteheads"] = ["normal"]
    return properties_dict


def parse_spelling_policy(spelling_policy_string):
    try:
        parse_tree = _properties_parser.parse(spelling_policy_string)
        properties_dict = visit_parse_tree(parse_tree, _properties_visitor)
    except NoMatch:
        raise ValueError("String could not be interpreted as a SpellingPolicy")

    if 'spelling_policy' not in properties_dict:
        raise ValueError("String could not be interpreted as a SpellingPolicy")
    return visit_parse_tree(parse_tree, _properties_visitor)['spelling_policy']


def parse_note_playback_adjustment(note_playback_adjustment_string):
    try:
        parse_tree = _properties_parser.parse(note_playback_adjustment_string)
        properties_dict = visit_parse_tree(parse_tree, _properties_visitor)
    except NoMatch:
        raise ValueError("String could not be interpreted as a NotePlaybackAdjustment")

    if 'playback_adjustments' not in properties_dict:
        raise ValueError("String could not be interpreted as a NotePlaybackAdjustment")
    return visit_parse_tree(parse_tree, _properties_visitor)['playback_adjustments'][0]


def parse_property_key_and_value(note_property_string):
    parse_tree = _properties_parser.parse(note_property_string)
    properties_dict = visit_parse_tree(parse_tree, _properties_visitor)
    if len(properties_dict) != 1:
        raise ValueError("String must describe a single property.")
    else:
        for key, value in properties_dict.items():
            if hasattr(value, '__len__'):
                if len(value) != 1:
                    raise ValueError("String must describe a single property.")
                value = value[0]
            # kind of a weird way to just return the one and only key/value pair
            return key, value
