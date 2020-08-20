"""
Module containing dictionaries and functions for translating between different systems of music engraving.
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

from xml.etree import ElementTree
import pymusicxml
import logging


length_to_note_type = {
    8.0: "breve",
    4.0: "whole",
    2.0: "half",
    1.0: "quarter",
    0.5: "eighth",
    0.25: "16th",
    1.0/8: "32nd",
    1.0/16: "64th",
    1.0/32: "128th"
}


notehead_name_to_lilypond_type = {
    "normal": "default",
    "diamond": "diamond",
    "harmonic": "harmonic",
    "harmonic black": "harmonic black",
    "harmonic mixed": "harmonic mixed",
    "triangle": "triangle",
    "slash": "slash",
    "cross": "cross",
    "x": "cross",
    "circle-x": "xcircle",
    "xcircle": "xcircle",
    "inverted triangle": None,
    "square": None,
    "arrow down": None,
    "arrow up": None,
    "circled": None,
    "slashed": None,
    "back slashed": None,
    "cluster": None,
    "circle dot": None,
    "left triangle": None,
    "rectangle": None,
    "do": None,
    "re": None,
    "mi": None,
    "fa": None,
    "fa up": None,
    "so": None,
    "la": None,
    "ti": None,
    "none": "none",
}


def get_lilypond_notehead_name(notehead_string: str):
    notehead_string = notehead_string.lower().strip()
    base_notehead = notehead_string.replace("filled", "").replace("open", "").strip()
    if base_notehead not in notehead_name_to_lilypond_type:
        # This error is raised if a notehead is asked for that wouldn't have been recognized for xml output either
        raise ValueError("Notehead type {} not recognized".format(notehead_string))

    elif notehead_string not in notehead_name_to_lilypond_type:
        logging.warning("\"Filled\" and \"open\" do not apply to lilypond output. "
                        "Reverting to \"{}\"".format(base_notehead))
        out = notehead_name_to_lilypond_type[base_notehead]

    else:
        out = notehead_name_to_lilypond_type[notehead_string]

    if out is None:
        logging.warning("Notehead type \"{}\" not available for lilypond output; "
                        "reverting to standard notehead".format(notehead_string))
        return "default|{} notehead was desired".format(notehead_string)
    else:
        return out


notehead_name_to_xml_type = {
    "normal": "normal",
    "diamond": "diamond",
    "harmonic": "open mi",
    "harmonic black": "filled mi",
    "harmonic mixed": "mi",
    "triangle": "triangle",
    "slash": "slash",
    "cross": "cross",
    "x": "x",
    "circle-x": "circle-x",
    "xcircle": "circle-x",
    "inverted triangle": "inverted triangle",
    "square": "square",
    "arrow down": "arrow down",
    "arrow up": "arrow up",
    "circled": "circled",
    "slashed": "slashed",
    "back slashed": "back slashed",
    "cluster": "cluster",
    "circle dot": "circle dot",
    "left triangle": "left triangle",
    "rectangle": "rectangle",
    "do": "do",
    "re": "re",
    "mi": "mi",
    "fa": "fa",
    "fa up": "fa up",
    "so": "so",
    "la": "la",
    "ti": "ti",
    "none": "none",
}


def get_xml_notehead(notehead_string: str):
    notehead_string = notehead_string.lower().strip()
    base_notehead = notehead_string.replace("filled", "").replace("open", "").strip()
    if base_notehead not in notehead_name_to_xml_type:
        raise ValueError("Notehead type {} not recognized".format(notehead_string))
    else:
        base_notehead = notehead_name_to_xml_type[base_notehead]
    out = pymusicxml.Notehead(base_notehead)
    if notehead_string.startswith("filled"):
        out.filled = "yes"
    elif notehead_string.startswith("open"):
        out.filled = "no"
    return out


articulation_to_xml_element_name = {
    "staccato": "staccato",
    "staccatissimo": "staccatissimo",
    "marcato": "strong-accent",
    "tenuto": "tenuto",
    "accent": "accent"
}


def generate_nested_element(*args):
    out = this_element = None
    for element_info in args:
        if isinstance(element_info, str):
            out = this_element = ElementTree.Element(element_info) if out is None \
                else ElementTree.SubElement(out, element_info)
        else:
            this_element = ElementTree.Element(element_info[0]) if out is None \
                else ElementTree.SubElement(this_element, element_info[0])
            for extra_info in element_info[1:]:
                if isinstance(extra_info, dict):
                    this_element.attrib = extra_info
                elif isinstance(extra_info, str):
                    this_element.text = extra_info
    return out


notations_to_xml_notations_element = {
    "tremolo1": generate_nested_element("ornaments", ("tremolo", {"type": "single"}, "1")),
    "tremolo2": generate_nested_element("ornaments", ("tremolo", {"type": "single"}, "2")),
    "tremolo3": generate_nested_element("ornaments", ("tremolo", {"type": "single"}, "3")),
    "tremolo4": generate_nested_element("ornaments", ("tremolo", {"type": "single"}, "4")),
    "tremolo5": generate_nested_element("ornaments", ("tremolo", {"type": "single"}, "5")),
    "tremolo8": generate_nested_element("ornaments", ("tremolo", {"type": "single"}, "1")),
    "tremolo16": generate_nested_element("ornaments", ("tremolo", {"type": "single"}, "2")),
    "tremolo32": generate_nested_element("ornaments", ("tremolo", {"type": "single"}, "3")),
    "tremolo64": generate_nested_element("ornaments", ("tremolo", {"type": "single"}, "4")),
    "tremolo128": generate_nested_element("ornaments", ("tremolo", {"type": "single"}, "5")),
}