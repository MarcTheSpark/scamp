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

# ---------------------------------------------------- NOTEHEADS ----------------------------------------------------

notehead_name_to_lilypond_type = {
    "normal": "#'default",
    "diamond": "#'diamond",
    "harmonic": "#'harmonic",
    "harmonic-black": "#'harmonic-black",
    "harmonic-mixed": "#'harmonic-mixed",
    "triangle": "#'triangle",
    "slash": "#'slash",
    "cross": "#'cross",
    "x": "#'cross",
    "circle-x": "#'xcircle",
    "xcircle": "#'xcircle",
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
    "none": "#'none",
}


def get_lilypond_notehead_tweaks(notehead_string: str):
    """
    Parse notehead string (possibly with color) and return lilypond tweak commands.

    Returns:
        tuple: (tweak_string, comment_string or None)
        tweak_string contains all the \tweak commands needed
    """
    notehead_string = notehead_string.strip()

    # Extract color if present
    color = None
    if '[#' in notehead_string and notehead_string.endswith(']'):
        parts = notehead_string.split('[#')
        notehead_string = parts[0].strip()
        color = parts[1].rstrip(']')

    notehead_string = notehead_string.lower()
    base_notehead = notehead_string.replace("filled", "").replace("open", "").strip()

    if base_notehead not in notehead_name_to_lilypond_type:
        raise ValueError("Notehead type {} not recognized".format(notehead_string))

    if notehead_string not in notehead_name_to_lilypond_type:
        logging.warning("\"Filled\" and \"open\" do not apply to lilypond output. "
                        "Reverting to \"{}\"".format(base_notehead))
        style = notehead_name_to_lilypond_type[base_notehead]
    else:
        style = notehead_name_to_lilypond_type[notehead_string]

    tweaks = []
    comment = None

    if style is None:
        logging.warning("Notehead type \"{}\" not available for lilypond output; "
                        "reverting to standard notehead".format(notehead_string))
        comment = "{} notehead was desired".format(notehead_string)
    elif '|' in style:
        # Handle the pipe-separated comment
        style_part, comment = style.split('|', 1)
        tweaks.append(rf"\tweak style {style_part}")
    elif style != '#\'default':
        tweaks.append(rf"\tweak style {style}")

    if color:
        r = int(color[0:2], 16) / 255
        g = int(color[2:4], 16) / 255
        b = int(color[4:6], 16) / 255
        tweaks.append(rf"\tweak color #(rgb-color {r:.3f} {g:.3f} {b:.3f})")

    return ' '.join(tweaks) if tweaks else '', comment


def _set_abjad_note_head_styles(self, abjad_note_or_chord):
    from . import abjad_facade as af

    note_heads = af.get_noteheads(abjad_note_or_chord)

    for note_head, note_head_string in zip(note_heads, self.properties.noteheads):
        tweak_string, comment = get_lilypond_notehead_tweaks(note_head_string)

        if tweak_string:
            af.tweak(note_head, tweak_string)

        if comment:
            af.attach(af.create_lilypond_comment(comment), abjad_note_or_chord)


notehead_name_to_xml_type = {
    "normal": "normal",
    "diamond": "diamond",
    "harmonic": "open mi",
    "harmonic-black": "filled mi",
    "harmonic-mixed": "mi",
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
    notehead_string = notehead_string.strip()

    # Extract color if present
    color = None
    if '[#' in notehead_string and notehead_string.endswith(']'):
        # Split off the color annotation
        parts = notehead_string.split('[')
        notehead_string = parts[0].strip()
        color = parts[1].rstrip(']')

    notehead_string = notehead_string.lower()
    base_notehead = notehead_string.replace("filled", "").replace("open", "").strip()

    if base_notehead not in notehead_name_to_xml_type:
        raise ValueError("Notehead type {} not recognized".format(notehead_string))
    else:
        base_notehead = notehead_name_to_xml_type[base_notehead]

    # Create notehead with optional color
    if color:
        out = pymusicxml.Notehead(base_notehead, color=color)
    else:
        out = pymusicxml.Notehead(base_notehead)

    if notehead_string.startswith("filled"):
        out.filled = "yes"
    elif notehead_string.startswith("open"):
        out.filled = "no"

    return out


all_noteheads = list(notehead_name_to_xml_type.keys())
all_noteheads.extend(["filled " + notehead_name for notehead_name in all_noteheads])
all_noteheads.extend(["open " + notehead_name for notehead_name in all_noteheads
                      if not notehead_name.startswith("filled")])


# -------------------------------------------------- ARTICULATIONS --------------------------------------------------


articulation_to_xml_element_name = {
    "staccato": "staccato",
    "staccatissimo": "staccatissimo",
    "marcato": "strong-accent",
    "tenuto": "tenuto",
    "accent": "accent"
}

all_articulations = list(articulation_to_xml_element_name.keys())


# ---------------------------------------------------- NOTATIONS ---------------------------------------------------


notations_to_xml_notations_element = {
    "tremolo": pymusicxml.Tremolo(3),
    "tremolo1": pymusicxml.Tremolo(1),
    "tremolo2": pymusicxml.Tremolo(2),
    "tremolo3": pymusicxml.Tremolo(3),
    "tremolo4": pymusicxml.Tremolo(4),
    "tremolo5": pymusicxml.Tremolo(5),
    "tremolo6": pymusicxml.Tremolo(6),
    "tremolo7": pymusicxml.Tremolo(7),
    "tremolo8": pymusicxml.Tremolo(8),
    "down-bow": pymusicxml.DownBow(),
    "up-bow": pymusicxml.UpBow(),
    "open-string": pymusicxml.OpenString(),
    "harmonic": pymusicxml.Harmonic(),
    "stopped": pymusicxml.Stopped(),
    "snap-pizzicato": pymusicxml.SnapPizzicato(),
    "arpeggiate": pymusicxml.Arpeggiate(),
    "arpeggiate up": pymusicxml.Arpeggiate("up"),
    "arpeggiate down": pymusicxml.Arpeggiate("down"),
    "non-arpeggiate": pymusicxml.NonArpeggiate(),
    "fermata": pymusicxml.Fermata(),
    "turn": pymusicxml.Turn(),
    "mordent": pymusicxml.Mordent(),
    "inverted mordent": pymusicxml.Mordent(inverted=True),
    "trill mark": pymusicxml.TrillMark(),
}

notations_to_lilypond_articulations = {
    "up-bow": "upbow",
    "down-bow": "downbow",
    "open-string": "open",
    "harmonic": "flageolet",
    "snap-pizzicato": "snappizzicato",
    "trill mark": "trill",
    "stopped": "stopped",
    "turn": "turn",
    "mordent": "mordent",
    "inverted mordent": "prall",
}

all_notations = list(notations_to_xml_notations_element.keys())


def attach_abjad_notation_to_note(abjad_note, notation_string):
    from . import abjad_facade as af
    notation_string = notation_string.lower()
    # markup vs otherwise
    # fix tremolo to be consistent number of slashes
    to_attach = None
    if notation_string in notations_to_lilypond_articulations:
        to_attach = af.create_articulation(notations_to_lilypond_articulations[notation_string])
    elif "tremolo" in notation_string:
        num_slashes = int(notation_string[-1]) if len(notation_string) == 8 else 3
        to_attach = af.create_stem_tremolo(2 ** (2 + af.get_written_duration(abjad_note).flag_count() + num_slashes))
    elif "arpeggiate" in notation_string:
        to_attach = af.create_arpeggio() if notation_string == "arpeggiate" \
            else af.create_arpeggio(direction=af.direction_up()) if notation_string == "arpeggiate up" \
            else af.create_arpeggio(direction=af.direction_down()) if notation_string == "arpeggiate down" \
            else None
    elif notation_string == "fermata":
        to_attach = af.create_fermata()
    af.attach(to_attach, abjad_note)


xml_barline_to_lilypond = {
    "double": "||",
    "end": "|.",
    "regular": "|",
    "dotted": ";",
    "dashed": "!",
    "heavy": ".",
    "light-light": "||",
    "light-heavy": "|.",
    "heavy-light": ".|",
    "heavy-heavy": "..",
    "tick": "'",
    "short": "'",  # this bar line type does not exist in LilyPond, it seems, so just do a tick
    "none": ""
}

xml_accidental_name_to_lilypond = {
    "flat-flat": r"\doubleflat",
    "flat": r"\flat",
    "natural": r"\natural",
    "sharp": r"\sharp",
    "double-sharp": r"\doublesharp"
}

