"""
Module containing start and stop spanner objects in SCAMP, such as :class:`StartHairpin`, :class:`StopHairpin`,
:class:`StartSlur` and :class:`StopSlur`. These are notations that belong to a range of notes rather that a
single note.
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
from abc import ABC, abstractmethod
from collections import defaultdict
from typing import Any
from ._dependencies import abjad
from ._engraving_translations import xml_accidental_name_to_lilypond
from .utilities import SavesToJSON, NoteProperty
import pymusicxml


class Spanner(ABC, SavesToJSON, NoteProperty):

    """
    Base class for all spanner notations, i.e. notations that cover more than one note.

    :param label: Each spanner can have a label that distinguishes it from other spanners of the same type.
        For example, consider the sequence of: start slur, start slur, stop slur, stop slur. Is this a small
        slur inside of a large one, or two interlocking slurs. The label clarifies. In practice, this is
        only really functional in musicXML export, where it is converted to a number.
    :param formatting: Each spanner has various types of individually specific formatting, such as a trill
        accidental or bracket text. This is passed along in a dictionary, and largely follows formatting
        from the MusicXML standard.
    """

    START_MID_OR_STOP = NotImplemented
    FORMATTING_SLOTS = NotImplemented

    def __init__(self, label: Any = 0, **formatting):
        self.label = label
        self.formatting = defaultdict(lambda: None, **formatting)

    def _to_dict(self) -> dict:
        return {"label": self.label, **self.formatting}

    @classmethod
    def _from_dict(cls, json_dict):
        return cls(**json_dict)

    @abstractmethod
    def to_pymusicxml(self):
        """Converts this to a pymusicxml spanner type."""
        pass

    @abstractmethod
    def to_abjad(self):
        """Converts this to an abjad indicator."""
        pass

    def _get_xml_consistent_formatting(self):
        return {k: v for k, v in self.formatting.items() if k in self.FORMATTING_SLOTS}

    def _get_abjad_direction(self):
        return abjad().Up if self.formatting["placement"] == "above" \
            else abjad().Down if self.formatting["placement"] == "below" else None

    def __eq__(self, other):
        if not isinstance(other, type(self)):
            return False
        return hash(self) == hash(other)

    def __hash__(self):
        return hash((self.label, frozenset(self.formatting.items())))

    def __repr__(self):
        if self.label == 0 and len(self.formatting) == 0:
            return f"{type(self).__name__}()"
        return "{}({})".format(type(self).__name__, ", ".join(f"{key}={repr(value)}"
                                                              for key, value in self._to_dict().items()))


class StartSlur(Spanner):

    """
    Start slur spanner type.

    :param label: See :class:`Spanner`.
    :param formatting: See :class:`Spanner`. Doesn't take any special formatting.
    """

    START_MID_OR_STOP = "start"
    FORMATTING_SLOTS = {}

    def to_pymusicxml(self):
        return pymusicxml.StartSlur(label=self.label, **self._get_xml_consistent_formatting())

    def to_abjad(self):
        return abjad().StartSlur(direction=self._get_abjad_direction())


class StopSlur(Spanner):

    """
    Stop slur spanner type.

    :param label: See :class:`Spanner`.
    :param formatting: See :class:`Spanner`. Doesn't take any special formatting.
    """

    START_MID_OR_STOP = "stop"
    FORMATTING_SLOTS = {}

    def to_pymusicxml(self):
        return pymusicxml.StopSlur(label=self.label, **self._get_xml_consistent_formatting())

    def to_abjad(self):
        return abjad().StopSlur()


class StartPhrasingSlur(Spanner):

    """
    Phrasing slurs are an additional type of slur available in LilyPond useful for creating long, overarching
    slurs that can have smaller, regular slurs inside of them. In MusicXML export, no distinction is made here:
    instead phrasing slurs are just rendered as slurs, albeit slurs that are kept from interfering with other
    slurs via a unique label. Basically, just use regular slurs for articulation and phrasing slurs for longer
    phrasing and don't worry about those details, and it'll work out fine.

    :param label: See :class:`Spanner`.
    :param formatting: See :class:`Spanner`. Doesn't take any special formatting.
    """

    START_MID_OR_STOP = "start"
    FORMATTING_SLOTS = {}

    def __init__(self, label: Any = 0, **formatting):
        super().__init__(f"phrasing{label}", **formatting)

    def to_pymusicxml(self):
        return pymusicxml.StartSlur(label=self.label, **self._get_xml_consistent_formatting())

    def to_abjad(self):
        return abjad().StartPhrasingSlur(direction=self._get_abjad_direction())


class StopPhrasingSlur(Spanner):

    """
    Stop spanner for a phrasing slur. See :class:`StartPhrasingSlur`.

    :param label: See :class:`Spanner`.
    :param formatting: See :class:`Spanner`. Doesn't take any special formatting.
    """

    START_MID_OR_STOP = "stop"
    FORMATTING_SLOTS = {}

    def __init__(self, label: Any = 0, **formatting):
        super().__init__(f"phrasing{label}", **formatting)

    def to_pymusicxml(self):
        return pymusicxml.StopSlur(label=self.label, **self._get_xml_consistent_formatting())

    def to_abjad(self):
        return abjad().StopPhrasingSlur()


class StartHairpin(Spanner):

    """
    Start hairpin spanner.

    :param label: See :class:`Spanner`.
    :param formatting: See :class:`Spanner`. Formatting can consist of {"placement": "above"/"below",
        "hairpin_type": "crescendo"/"diminuendo", "niente": True/False}
    """

    START_MID_OR_STOP = "start"
    FORMATTING_SLOTS = {"placement", "hairpin_type", "niente"}

    def to_pymusicxml(self):
        return pymusicxml.StartHairpin(label=self.label, **self._get_xml_consistent_formatting())

    def to_abjad(self):
        if self.formatting["hairpin_type"] == "crescendo":
            shape = "<" if "niente" not in self.formatting or self.formatting["niente"] is False else "o<"
        else:
            shape = ">" if "niente" not in self.formatting or self.formatting["niente"] is False else ">o"
        return abjad().StartHairpin(shape=shape, direction=self._get_abjad_direction())


class StopHairpin(Spanner):

    """
    Stop hairpin spanner.

    :param label: See :class:`Spanner`.
    :param formatting: See :class:`Spanner`. Formatting can consist of {"placement": "above"/"below",
        "hairpin_type": "crescendo"/"diminuendo", "niente": True/False}
    """

    START_MID_OR_STOP = "stop"
    FORMATTING_SLOTS = {"placement", "hairpin_type", "niente"}

    def to_pymusicxml(self):
        return pymusicxml.StopHairpin(label=self.label, **self._get_xml_consistent_formatting())

    def to_abjad(self):
        return abjad().StopHairpin()


class StartBracket(Spanner):

    """
    Start bracket spanner (e.g. a text bracket with a hook).

    :param label: See :class:`Spanner`.
    :param formatting: See :class:`Spanner`. Formatting can consist of {"placement": "above"/"below", "text": [string],
        "line_end": "up"/"down"/"both"/"arrow"/"none", "line_type": "solid"/"dashed"/"dotted"/"wavy"}
    """

    START_MID_OR_STOP = "start"
    FORMATTING_SLOTS = {"placement", "text", "line_end", "line_type"}

    def to_pymusicxml(self):
        return pymusicxml.StartBracket(label=self.label, **self._get_xml_consistent_formatting())

    def to_abjad(self):
        style = ("dashed-line" if "line_type" in self.formatting and self.formatting["line_type"] == "dashed" else "solid-line") + \
                ("-with-hook" if self.formatting["line_end"] is None
                 else "-with-up-hook" if "up" in self.formatting["line_end"]
                 else "-with-arrow" if "arrow" in self.formatting["line_end"]
                 else "-with-hook")

        left_text = rf"""- \tweak bound-details.left.text \markup \concat """ \
                    rf"""{{ "{self.formatting["text"]}" \hspace #0.5 }}""" if "text" in self.formatting else None

        return abjad().StartTextSpan(
            left_text=left_text if "text" in self.formatting else None,
            # TODO: left broken text is broken, can't handle a literal in abjad 3.4. when we update abjad, fix this
            # left_broken_text=abjad().Markup(f"({self.formatting['text']})") if "text" in self.formatting else None,
            right_text=self.formatting["right_text"],
            style=style,
            direction=self._get_abjad_direction()
        )


class StopBracket(Spanner):

    """
    Stop bracket spanner.

    :param label: See :class:`Spanner`.
    :param formatting: See :class:`Spanner`. Formatting can consist of {"placement": "above"/"below", "text": [string],
        "line_end": "up"/"down"/"both"/"arrow"/"none", "line_type": "solid"/"dashed"/"dotted"/"wavy"}
    """

    START_MID_OR_STOP = "stop"
    FORMATTING_SLOTS = {"placement", "text", "line_end"}

    def to_pymusicxml(self):
        return pymusicxml.StopBracket(label=self.label, **self._get_xml_consistent_formatting())

    def to_abjad(self):
        return abjad().StopTextSpan()


class StartDashes(Spanner):

    """
    Start dashes spanner.

    :param label: See :class:`Spanner`.
    :param formatting: See :class:`Spanner`. Formatting can consist of {"placement": "above"/"below", "text": [string],
        "dash_length": [number of pixels], "space_length": [number of pixels]}
    """

    START_MID_OR_STOP = "start"
    FORMATTING_SLOTS = {"placement", "text", "dash_length", "space_length"}

    def to_pymusicxml(self):
        return pymusicxml.StartDashes(label=self.label, **self._get_xml_consistent_formatting())

    def to_abjad(self):
        return abjad().StartTextSpan(
            left_text=abjad().Markup(self.formatting["text"]) if "text" in self.formatting else None,
            left_broken_text=abjad().Markup(f"({self.formatting['text']})") if "text" in self.formatting else None,
            right_text=self.formatting["right_text"],
            direction=self._get_abjad_direction()
        )

    def _get_abjad_direction(self):
        # since dashes is generally used for stuff like "cresc.---" or "dim.---", it should generally default to
        # below the staff, so we need to override this method for dashes particularly
        return abjad().Up if self.formatting["placement"] == "above" else abjad().Down


class StopDashes(Spanner):
    """
    Stop dashes spanner.

    :param label: See :class:`Spanner`.
    :param formatting: See :class:`Spanner`. Formatting can consist of {"placement": "above"/"below", "text": [string]}
    """

    START_MID_OR_STOP = "stop"
    FORMATTING_SLOTS = {"placement", "text"}

    def to_pymusicxml(self):
        return pymusicxml.StopDashes(label=self.label, **self._get_xml_consistent_formatting())

    def to_abjad(self):
        return abjad().StopTextSpan()


class StartTrill(Spanner):

    """
    Start trill spanner.

    :param label: See :class:`Spanner`.
    :param formatting: See :class:`Spanner`. Formatting can consist of {"placement": "above"/"below",
        "accidental": "flat-flat"/"flat"/"natural"/"sharp"/"double-sharp" }
    """

    START_MID_OR_STOP = "start"
    FORMATTING_SLOTS = {"placement", "accidental"}

    def to_pymusicxml(self):
        return pymusicxml.StartTrill(label=self.label, **self._get_xml_consistent_formatting())

    def to_abjad(self):
        # TODO: When we upgrade to abjad 3.8, this should be done with an abjad().bundle call
        if self.formatting["accidental"] is not None:
            return abjad().LilyPondLiteral(
                rf'\tweak bound-details.left.text \markup{{ '
                rf'\musicglyph #"scripts.trill" \raise #0.65 \teeny '
                rf'{xml_accidental_name_to_lilypond[self.formatting["accidental"]]} }} \startTrillSpan',
                format_slot="after"
            )
        else:
            return abjad().StartTrillSpan()


class StopTrill(Spanner):
    """
    Stop trill spanner.

    :param label: See :class:`Spanner`.
    :param formatting: See :class:`Spanner`. Formatting can consist of {"placement": "above"/"below"}
    """

    START_MID_OR_STOP = "stop"
    FORMATTING_SLOTS = {"placement"}

    def to_pymusicxml(self):
        return pymusicxml.StopTrill(label=self.label, **self._get_xml_consistent_formatting())

    def to_abjad(self):
        return abjad().StopTrillSpan()


class StartPedal(Spanner):

    r"""
    Start piano pedal spanner.

    :param label: See :class:`Spanner`.
    :param formatting: See :class:`Spanner`. Formatting can consist of {"placement": "above"/"below",
        "line": True/False, "sign": True/False}. Line and sign control whether or not the pedal is done with "Ped./\*"
        markings, brackets, or a mixture of both. Note that this only works for MusicXML output. For lilypond output,
        you will need manually add a formatting block that declares which style is being used globally.
    """

    START_MID_OR_STOP = "start"
    FORMATTING_SLOTS = {"placement", "line", "sign"}

    def to_pymusicxml(self):
        return pymusicxml.StartPedal(label=self.label, **self._get_xml_consistent_formatting())

    def to_abjad(self):
        return abjad().StartPianoPedal()


class ChangePedal(Spanner):

    """
    Change piano pedal spanner.

    :param label: See :class:`Spanner`.
    :param formatting: See :class:`Spanner`. Formatting can consist of {"placement": "above"/"below",
        "line": True/False, "sign": True/False}.
    """

    START_MID_OR_STOP = "mid"
    FORMATTING_SLOTS = {"placement", "line", "sign"}

    def to_pymusicxml(self):
        return pymusicxml.ChangePedal(label=self.label, **self._get_xml_consistent_formatting())

    def to_abjad(self):
        return [abjad().StopPianoPedal(), abjad().StartPianoPedal()]


class StopPedal(Spanner):
    """
    Stop piano pedal spanner.

    :param label: See :class:`Spanner`.
    :param formatting: See :class:`Spanner`. Formatting can consist of {"placement": "above"/"below",
        "line": True/False, "sign": True/False}.
    """

    START_MID_OR_STOP = "stop"
    FORMATTING_SLOTS = {"placement", "line", "sign"}

    def to_pymusicxml(self):
        return pymusicxml.StopPedal(label=self.label, **self._get_xml_consistent_formatting())

    def to_abjad(self):
        abjad_stop_pedal = abjad().StopPianoPedal()
        return abjad_stop_pedal
