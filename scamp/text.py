"""
Module containing utilities for representing text in SCAMP, currently containing the :class:`StaffText` class.
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

from ._dependencies import abjad
from .utilities import SavesToJSON, NoteProperty
import pymusicxml


class StaffText(SavesToJSON, NoteProperty):

    """
    Represents text that will be attached to the staff at a given note.
    Place this object in the fourth `properties` argument of :func:`~scamp.instruments.ScampInstrument.play_note`,
    either alone, or under the "text" key.

    :param text: the text to display
    :param italic: whether or not to make text italic
    :param bold: whether or not to make text bold
    :param placement: placement relative to the staff; either "above" of "below"
    :ivar text: the text to display
    :ivar italic: whether or not to make text italic
    :ivar bold: whether or not to make text bold
    :ivar placement: placement relative to the staff; either "above" of "below"
    """

    def __init__(self, text: str, italic: bool = False, bold: bool = False, placement: str = "above"):

        if placement not in ("above", "below"):
            raise ValueError("StaffText placement must be either \"above\" or \"below\".")
        self.text = text
        self.italic = italic
        self.bold = bold
        self.placement = placement

    @classmethod
    def from_string(cls, string: str):
        """
        Interprets a string as a staff text. For now, it just looks for 1, 2, or 3 leading and trailing asterisks or
        underscores to make the whole text italic, bold or bold-italic respectively. (This only works on the whole
        text.)

        :param string: the text, possible with leading and trailing asterisks/underscores
        """
        if string.startswith("***") and string.endswith("***") or string.startswith("___") and string.endswith("___"):
            return cls(string[3:-3], bold=True, italic=True)
        if string.startswith("**") and string.endswith("**") or string.startswith("__") and string.endswith("__"):
            return cls(string[2:-2], bold=True)
        if string.startswith("*") and string.endswith("*") or string.startswith("_") and string.endswith("_"):
            return cls(string[1:-1], italic=True)
        return cls(string)

    def to_pymusicxml(self) -> pymusicxml.TextAnnotation:
        """Converts this to a pymusicxml TextAnnotation object."""
        return pymusicxml.TextAnnotation(self.text, placement=self.placement, italic=self.italic, bold=self.bold)

    def to_abjad(self) -> 'abjad.Markup':
        """Converts this to an abjad Markup object."""
        out = abjad().Markup(self.text, direction=abjad().Up if self.placement == "above" else abjad().Down)
        if self.italic:
            out = out.italic()
        if self.bold:
            out = out.bold()
        return out

    def _to_dict(self) -> dict:
        json_dict = {"text": self.text}
        if self.italic:
            json_dict["italic"] = True
        if self.bold:
            json_dict["bold"] = True
        if self.placement != "above":
            json_dict["placement"] = self.placement
        return json_dict

    @classmethod
    def _from_dict(cls, json_dict):
        return cls(**json_dict)

    def __eq__(self, other):
        if not isinstance(other, StaffText):
            return False
        return self._to_dict() == other._to_dict()

    def __repr__(self):
        return "StaffText({}{}{}{})".format(
            "\"{}\"".format(self.text),
            ", italic={}".format(self.italic) if self.italic else "",
            ", bold={}".format(self.bold) if self.bold else "",
            ", placement=\"{}\"".format(self.placement) if self.placement != "above" else ""
        )
