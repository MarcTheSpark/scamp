"""
Module containing classes that deal with music notation. These classes represent the music hierarchically; in order from
largest to smallest: :class:`Score`, :class:`StaffGroup`, :class:`Staff`, :class:`Voice`, :class:`Measure`,
:class:`Voice`, :class:`Tuplet`, and :class:`NoteLike`. One important role of the classes in this module is to
provide export functionality to both MusicXML and LilyPond.
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

from numbers import Real
from .settings import quantization_settings, engraving_settings
from expenvelope import Envelope
from .quantization import QuantizationRecord, QuantizationScheme, QuantizedMeasure, TimeSignature
from . import performance as performance_module  # to distinguish it from variables named performance
from .utilities import prime_factor, floor_x_to_pow_of_y, is_x_pow_of_y, ceil_to_multiple, floor_to_multiple
from ._engraving_translations import length_to_note_type, get_xml_notehead, get_lilypond_notehead_name, \
    articulation_to_xml_element_name, notations_to_xml_notations_element
from .note_properties import NoteProperties
from .text import StaffText
import pymusicxml
from pymusicxml.music_xml_objects import _XMLNote, MusicXMLComponent
from ._dependencies import abjad
import math
from fractions import Fraction
from copy import deepcopy
from itertools import accumulate, count
import textwrap
from collections import namedtuple
from abc import ABC, abstractmethod
import logging
from ._metric_structure import MetricStructure
from typing import Sequence, Type, Union, Tuple, Optional, Iterator
from clockblocks import TempoEnvelope


##################################################################################################################
#                                             Assorted Utilities
##################################################################################################################


def _is_undotted_length(length):
    return length in length_to_note_type


def _get_basic_length_and_num_dots(length):
    length = Fraction(length).limit_denominator()
    if _is_undotted_length(length):
        return length, 0
    else:
        dots_multiplier = 1.5
        dots = 1
        while not _is_undotted_length(length / dots_multiplier):
            dots += 1
            dots_multiplier = (2.0 ** (dots + 1) - 1) / 2.0 ** dots
            if dots > engraving_settings.max_dots_allowed:
                raise ValueError("Duration length of {} does not resolve to single note type.".format(length))
        return length / dots_multiplier, dots


def _is_single_note_length(length):
    try:
        _get_basic_length_and_num_dots(length)
        return True
    except ValueError:
        return False


def _length_to_undotted_constituents(length):
    # fix any floating point inaccuracies
    length = Fraction(length).limit_denominator()
    length_parts = []
    while length > 0:
        this_part = floor_x_to_pow_of_y(length, 2.0)
        length -= this_part
        length_parts.append(this_part)
    return length_parts


def _get_beat_division_hierarchy(beat_length, beat_divisor, small_to_big=True):
    # In general, it's best to divide a beat into the smaller prime factors first. For instance, a 6 tuple is probably
    # easiest as two groups of 3 rather than 3 groups of 2. (This is definitely debatable and context dependent.)
    # An special case occurs when the beat naturally wants to divide a certain way. For instance, a beat of length 1.5
    # divided into 6 will prefer to divide into 3s first and then 2s.

    # first, get the divisor prime factors from big to small (or small to big if set)
    divisor_factors = sorted(prime_factor(beat_divisor), reverse=not small_to_big)

    # then get the natural divisors of the beat length from big to small
    natural_factors = sorted(prime_factor(Fraction(beat_length).limit_denominator().numerator), reverse=True)

    # now for each natural factor
    for natural_factor in natural_factors:
        # if it's a factor of the divisor
        if natural_factor in divisor_factors:
            # then pop it and move it to the front
            divisor_factors.pop(divisor_factors.index(natural_factor))
            divisor_factors.insert(0, natural_factor)
            # (Note that we sorted the natural factors from big to small so that the small ones get
            # pushed to the front last and end up at the very beginning of the queue)

    return MetricStructure.from_string("*".join(str(x) for x in divisor_factors), True).get_beat_depths()


def _worsen_hierarchy_tuples(hierarchy, how_much=1, in_place=True):
    """
    Takes a beat hierarchy list and bumps everything surrounding a tuple up by how_much at each layer of structure.
    Essentially, this increases the distance between the layers, making tuplet subdivisions act more like subdivisions
    of 4 than subdivisions of 2.

    :param hierarchy: the original hierarchy list
    :param how_much, how much to worsen tuples more than 2 by
    :param in_place: modify hierarchy in place
    :return: the altered hierarchy list (also alters in place)
    """
    if not in_place:
        hierarchy = list(hierarchy)
    for level in reversed(range(1, max(hierarchy) + 1)):
        last_lower_value_at = None
        streak = 0
        for i, value in enumerate(hierarchy):
            if value < level:
                # check if we had a streak
                if streak > 1:
                    # if so, that indicates a tuple a this level of hierarchy. We boost everything since we
                    # saw a lower level, including higher numbers than the current level
                    for j in range(last_lower_value_at + 1, i):
                        hierarchy[j] += how_much
                # ... regardless, reset the streak counter, and last time we saw a lower level
                streak = 0
                last_lower_value_at = i
            elif value == level:
                streak += 1
        if streak > 1:
            for j in range(last_lower_value_at + 1, len(hierarchy)):
                hierarchy[j] += how_much

    return hierarchy


# TODO: MEMOIZE THE SHIT OUT OF THIS!!!
def _get_beat_division_grids(beat_hierarchy):
    out = []
    for thresh in range(max(beat_hierarchy)):
        out.append([x for x in range(len(beat_hierarchy)) if beat_hierarchy[x] <= thresh])
    return out


# should maybe memoize?
def _is_single_note_viable_grouping(length_in_subdivisions, max_dots=1):
    """
    This tests if a note that is length_in_subdivisions subdivisions long can be represented by a single note.
    For instance, suppose the subdivision is a 16th note: if length_in_subdivisions is 7, we're asking whether we
    can represent, with one notehead, a not of length 7 16th notes. The answer is False with max_dots = 1, but
    True with max_dots = 2, since a double-dotted quarter satisfies our requirement.

    :param length_in_subdivisions: how many subdivisions we wish to combine
    :param max_dots: max dots we are allowing
    """
    dot_multipliers = [2 - 2**(-x) for x in range(max_dots+1)]
    for dot_multiplier in dot_multipliers:
        if Fraction(math.log2(length_in_subdivisions / dot_multiplier)).limit_denominator().denominator == 1:
            return True
    return False


def _get_best_recombination_given_beat_hierarchy(note_division_points, beat_hierarchy_list, is_rest=False):
    """
    Takes a list of points on an isochronous grid representing the start and end times of the components of a note,
        along with a list of the beat hierarchies for that grid. Returns a merged list of component start and end
        times, in which important division points are preserved and less important ones are removed.

    :param note_division_points: list of the points on the isochronous grid representing note component starts and ends
    :param beat_hierarchy_list: the result of _get_beat_division_hierarchy; a list of values for each beat in an
        isochronous grid, where 0 is the most important beat (always the downbeat), 1 is the next most important kind
        of beat, etc.
    :param is_rest: changes the settings, by default in such a way that less recombination happens
    :return: a new, better, I dare say shinier, list of note division points.
    """
    # the factor that the badness goes up from one rung of the beat hierarchy to the next.
    # A high value makes greater differentiation between important and less important beats, probably
    # leading to less recombination in favor of clearer delineation of the beat structure.
    beat_hierarchy_spacing = engraving_settings.rest_beat_hierarchy_spacing if is_rest \
        else engraving_settings.beat_hierarchy_spacing
    # ranging from 0 to 1, this penalizes using more than one component to represent a note.
    # It acts as a counterbalance to beat_hierarchy_spacing, as it encourages recombination. The balance of the two
    # parameters needs to be correct if we want to get notation that expresses the beat hierarchy, but with as few
    # tied notes as possible.
    num_divisions_penalty = engraving_settings.rest_num_divisions_penalty if is_rest \
        else engraving_settings.num_divisions_penalty

    adjusted_hierarchies = [beat_hierarchy_spacing ** x for x in beat_hierarchy_list]

    # if we have long notes made up of a ton of parts, we would run into number crunching hell trying all the
    # possible recombinations. So instead, we break the note division points list into subgroups no longer than 5
    # and then get the best recombination for each subgroup, and stick them all together.
    subgroups = _break_up_large_division_points_list(note_division_points, beat_hierarchy_list, 5)

    best_option = ()
    best_score = 0

    for subgroup in subgroups:
        best_subgroup_option, best_subgroup_score = _get_best_subgroup_recombination_option(
            subgroup, adjusted_hierarchies, num_divisions_penalty)
        best_option += best_subgroup_option
        best_score += best_subgroup_score

    return best_option, best_score


def _break_up_large_division_points_list(division_points, hierarchies, max_subgroup_length=8):
    if len(division_points) > max_subgroup_length:
        # break at the division point with the lowest (i.e. most important) hierarchy value
        i = division_points.index(max(*division_points[1:-1], key=lambda x: -hierarchies[x]))
        return _break_up_large_division_points_list(division_points[:i], hierarchies, max_subgroup_length) + \
               _break_up_large_division_points_list(division_points[i:], hierarchies, max_subgroup_length)
    else:
        return division_points,


def _get_best_subgroup_recombination_option(note_division_points, adjusted_hierarchies, num_divisions_penalty):
    # if there's only one division point in this subgroup, then there's no way of recombining it!
    if len(note_division_points) == 1:
        return tuple(note_division_points), 0

    # translate time-points on the isochronous grid to durations in isochronous units after the start of the note
    component_lengths = [division - last_division
                         for last_division, division in zip(note_division_points[:-1], note_division_points[1:])]
    assert all(_is_single_note_viable_grouping(x, max_dots=engraving_settings.max_dots_allowed)
               for x in component_lengths), "Somehow we got an division of a note into un-notatable components"

    # get every possible combination of these components that keeps each component representable as a single note
    recombination_options_lengths = [
        option for option in _get_recombination_options(*component_lengths)
        if all(_is_single_note_viable_grouping(component, max_dots=engraving_settings.max_dots_allowed)
               for component in option)
    ]

    # now, finally, we make ourselves a list options for division-point lists, each of which represents a recombination
    # option. These are now time-points (rather than durations), so we can check them against the beat_hierarchy_list
    # to see which one finds the best balance between expressing the metric structure and doing so with few components
    recombination_options = [tuple(note_division_points[0] + x for x in accumulate((0, ) + option))
                             for option in recombination_options_lengths]

    if len(recombination_options) == 1:
        return recombination_options[0], 0

    best_score = float("inf")
    best_option = None
    num_beats = len(adjusted_hierarchies)
    for option in recombination_options:
        # adjusted_hierarchies[x] represents the badness of a given division point, since we want to divide on
        # important beats, and important beats have low values in the beat_hierarchy_list
        # if num_divisions_penalty is 0, we're dividing by the number of scores, so it's basically average badness
        # if num_divisions_penalty is 1, we're dividing by 1, so it's total badness
        score = sum(adjusted_hierarchies[x % num_beats] for x in option) / len(option) ** (1 - num_divisions_penalty)
        if score < best_score:
            best_option = option
            best_score = score
        elif score == best_score:
            if _get_num_bad_crossings(option, adjusted_hierarchies) < \
                    _get_num_bad_crossings(best_option, adjusted_hierarchies):
                best_option = option
                best_score = score
    return best_option, best_score


def _get_num_bad_crossings(recombination_option, hierarchies):
    # we generally want to avoid crossing important beats with components that start or end with less important ones
    # e.g. in 9/8, with hierarchies [0, 2, 2, 1, 2, 2, 1, 2, 2], the tie combination (2, 3, 9) should be preferable
    # to the combination (2, 6, 9) since even though they land on the same kinds of beats, the latter option has a
    # component from 2 to 6 that crosses the important beat 3 but starts on the weak beat 2

    for start_segment, end_segment in zip(recombination_option[:-1], recombination_option[1:]):
        # it's not looking through each segment!
        threshold = max(hierarchies[start_segment], hierarchies[end_segment % len(hierarchies)])
        return sum(hierarchies[x] < threshold for x in range(start_segment+1, end_segment))


def _get_recombination_options(*component_lengths):
    if len(component_lengths) == 1:
        return component_lengths,
    else:
        return _get_recombination_options(component_lengths[0] + component_lengths[1], *component_lengths[2:]) + \
               tuple((component_lengths[0], ) + x for x in _get_recombination_options(*component_lengths[1:]))


def _join_same_source_abjad_note_group(same_source_group):
    # look pairwise to see if we need to tie or gliss
    # sometimes a note will gliss, then sit at a static pitch

    gliss_present = False
    for note_pair in zip(same_source_group[:-1], same_source_group[1:]):
        if isinstance(note_pair[0], abjad().Note) and note_pair[0].written_pitch == note_pair[1].written_pitch or \
                isinstance(note_pair[0], abjad().Chord) and note_pair[0].written_pitches == note_pair[1].written_pitches:
            abjad().tie(abjad().Selection(note_pair))
            # abjad().attach(abjad().Tie(), abjad().Selection(note_pair))
        else:
            # abjad().glissando(abjad().Selection(note_pair))
            abjad().attach(abjad().LilyPondLiteral("\glissando", "after"), note_pair[0])

            # abjad().attach(abjad().Glissando(), abjad().Selection(note_pair))
            gliss_present = True

    if gliss_present:
        # if any of the segments gliss, we might attach a slur
        abjad().slur(abjad().Selection(same_source_group))
        # abjad().attach(abjad().Slur(), abjad().Selection(same_source_group))


# generates unique ids for gliss slurs that won't conflict with manual slurs
_xml_gliss_slur_id_counter = count()


def _join_same_source_xml_note_group(same_source_group):
    available_gliss_numbers = list(range(1, 7))
    # since each gliss needs to be associated with an unambiguous number, here we keep track of which
    # glisses we've started and which numbers are still free / have been freed up by a gliss that ended
    glisses_started_notes = []
    glisses_started_numbers = []
    gliss_present = False
    for i, this_note_or_chord in enumerate(same_source_group):
        if isinstance(this_note_or_chord, pymusicxml.Note):
            if i < len(same_source_group) - 1:
                # not the last note of the group, so it starts a tie or gliss
                next_note_or_chord = same_source_group[i + 1]
                if this_note_or_chord.pitch == next_note_or_chord.pitch:
                    # it's a tie
                    this_note_or_chord.starts_tie = True
                else:
                    # it's a gliss
                    this_note_or_chord.starts_tie = False
                    if len(available_gliss_numbers) > 0:
                        this_gliss_number = available_gliss_numbers.pop(0)
                        this_note_or_chord.notations.append(pymusicxml.StartGliss(this_gliss_number))
                        glisses_started_notes.append(this_note_or_chord)
                        glisses_started_numbers.append(this_gliss_number)
                    else:
                        logging.warning("Ran out of available numbers to assign glisses in XML output. "
                                        "Some glisses will be omitted")
                    gliss_present = True
            if i > 0:
                # not the first note of the group, so it ends a tie or gliss
                last_note_or_chord = same_source_group[i - 1]
                if this_note_or_chord.pitch == last_note_or_chord.pitch:
                    # it's a tie
                    this_note_or_chord.ends_tie = True
                else:
                    # it's a gliss
                    this_note_or_chord.ends_tie = False
                    which_start_gliss = glisses_started_notes.index(last_note_or_chord)
                    # if which_start_gliss is -1, it means we couldn't find the start gliss
                    # this is because we ran out of gliss numbers in starting the gliss
                    if which_start_gliss >= 0:
                        glisses_started_notes.pop(which_start_gliss)
                        gliss_number = glisses_started_numbers.pop(which_start_gliss)
                        this_note_or_chord.notations.append(pymusicxml.StopGliss(gliss_number))
                        available_gliss_numbers.append(gliss_number)
                        available_gliss_numbers.sort()
                    gliss_present = True
        elif isinstance(this_note_or_chord, pymusicxml.Chord):
            next_note_or_chord = same_source_group[i + 1] if i < len(same_source_group) - 1 else None
            last_note_or_chord = same_source_group[i - 1] if i > 0 else None

            for j, note in enumerate(this_note_or_chord.notes):
                if next_note_or_chord is not None:
                    # find the corresponding note in the next chord
                    next_note = next_note_or_chord.notes[j]
                    if note.pitch == next_note.pitch:
                        # this note starts a tie to the corresponding note in the next chord
                        note.starts_tie = True
                    else:
                        # this note starts a gliss to the corresponding note in the next chord
                        note.starts_tie = False
                        if len(available_gliss_numbers) > 0:
                            this_gliss_number = available_gliss_numbers.pop(0)
                            note.notations.append(pymusicxml.StartGliss(this_gliss_number))
                            glisses_started_notes.append(note)
                            glisses_started_numbers.append(this_gliss_number)
                        else:
                            logging.warning("Ran out of available numbers to assign glisses in XML output. "
                                            "Some glisses will be omitted.")
                        gliss_present = True
                if last_note_or_chord is not None:
                    # find the corresponding note in the last chord
                    last_note = last_note_or_chord.notes[j]
                    if note.pitch == last_note.pitch:
                        # this note ends a tie from the corresponding note in the last chord
                        note.stops_tie = True
                    else:
                        # this note ends a gliss from the corresponding note in the last chord
                        note.stops_tie = False
                        # find the gliss that was started by the corresponding note in the previous chord
                        try:
                            which_start_gliss = glisses_started_notes.index(last_note)
                            glisses_started_notes.pop(which_start_gliss)
                            gliss_number = glisses_started_numbers.pop(which_start_gliss)
                            note.notations.append(pymusicxml.StopGliss(gliss_number))
                            # return this gliss number to the pool of available numbers
                            available_gliss_numbers.append(gliss_number)
                            available_gliss_numbers.sort()
                        except ValueError:
                            # if this is false, the start of the gliss couldn't be found, which suggests that we ran
                            # out of available numbers to assign to the glisses. So we skip the StopGliss notation
                            pass
                        gliss_present = True

    if gliss_present:
        # this unique id will get intelligently converted to a number from 1 to 6 by pymusicxml
        slur_id = "glissSlur{}".format(next(_xml_gliss_slur_id_counter))
        # add slur notation to the very first note and last note
        same_source_group[0].notations.append(pymusicxml.StartSlur(slur_id))
        same_source_group[-1].notations.append(pymusicxml.StopSlur(slur_id))


def _get_clef_from_average_pitch_and_clef_choices(average_pitch: float,
                                                  clef_choices: Sequence[Union[str, Tuple[str, Real]]]) -> str:
    # find the clef whose pitch center is closest to the average pitch
    closest_clef = None
    closest_distance = float("inf")
    for clef_choice in clef_choices:
        if isinstance(clef_choice, (tuple, list)):
            # clef_choice can either be a tuple of (clef name, clef pitch center)
            clef, clef_pitch_center = clef_choice
        else:
            # ...or just the clef name, in which case look up the default pitch center
            clef, clef_pitch_center = clef_choice, engraving_settings.clef_pitch_centers[clef_choice]
        dist = abs(clef_pitch_center - average_pitch)
        if dist < closest_distance:
            closest_clef = clef
            closest_distance = dist

    return closest_clef

##################################################################################################################
#                                             Abstract Classes
##################################################################################################################


class ScoreComponent(ABC):

    """
    Abstract class from which all of the user-facing classes in this module inherit. Provides a consistent interface
    for wrapping any object up as a Score and converting to LilyPond and MusicXML output.
    """

    #: LilyPond code to define stemless notes when we're rendering a full score (goes outside the lilypond context)
    _outer_stemless_def = r"""% Definition to improve score readability
stemless = {
    \once \override Beam.stencil = ##f
    \once \override Flag.stencil = ##f
    \once \override Stem.stencil = ##f
}"""

    #: LilyPond code to define stemless notes when we're rendering only part of a score (goes inside lilypond context)
    _inner_stemless_def = r"""% Definition to improve score readability
    #(define stemless 
        (define-music-function (parser location)
            ()
            #{
                \once \override Beam.stencil = ##f
                \once \override Flag.stencil = ##f
                \once \override Stem.stencil = ##f
            #})
        )
    """

    #: LilyPond code to customize glissando appearance
    _gliss_overrides = [
        r"% Make the glisses a little thicker, make sure they have at least a little length, and allow line breaks",
        r"\override Score.Glissando.minimum-length = #4",
        r"\override Score.Glissando.springs-and-rods = #ly:spanner::set-spacing-rods",
        r"\override Score.Glissando.thickness = #2",
        r"\override Score.Glissando #'breakable = ##t",
        "\n"
    ]

    #: LilyPond markup function for microtonal pitch annotations
    _pitch_annotation_function = r"""
#(define-markup-command (pitch-annotation layout props text) (markup?)
  "Command for creating a microtonal pitch annotation."
  (interpret-markup layout props
    (markup 
     (#:smaller #:italic (string-append "(" text ")"))
     )
    )
  )
    """

    @abstractmethod
    def _to_abjad(self) -> 'abjad().Component':
        """
        Convert this to the abjad version of the component.
        The reason this is a protected member is that the user-facing "to_abjad" takes the output of this function
        and adds some necessary LilyPond overrides and definitions.
        """
        pass

    @abstractmethod
    def to_music_xml(self) -> MusicXMLComponent:
        """
        Convert this score component to its corresponding pymusicxml component
        """
        pass

    def export_music_xml(self, file_path: str, pretty_print: bool = True) -> None:
        """
        Convert and wrap as a MusicXML score, and save to the given path.

        :param file_path: file path to save to
        :param pretty_print: whether or not to take the extra space and format the file with indentations, etc.
        """
        self.to_music_xml().export_to_file(file_path, pretty_print=pretty_print)

    def print_music_xml(self, pretty_print: bool = True) -> None:
        """
        Convert and wrap as a MusicXML score, and print the resulting XML.

        :param pretty_print: whether or not to take the extra space and format the file with indentations, etc.
        """
        print(self.to_music_xml().to_xml(pretty_print=pretty_print))

    def show_xml(self) -> None:
        """
        Convert and wrap as a MusicXML score, and open it up in notation software.
        (The software to use is defined in engraving_settings.show_music_xml_command_line.)
        """
        try:
            self.to_music_xml().view_in_software(engraving_settings.show_music_xml_command_line)
        except OSError:
            raise Exception("Command \"{}\" for showing musicXML failed. Either install the relevant program, or \n"
                            "change the value of \"show_music_xml_command_line\" in the engraving_settings to use "
                            "your program of choice.".format(engraving_settings.show_music_xml_command_line))

    def to_abjad(self) -> 'abjad().Component':
        """
        Convert this score component to its corresponding abjad component
        """
        assert abjad() is not None, "Abjad is required for this operation."
        abjad_object = self._to_abjad()
        lilypond_code = format(abjad_object)
        if r"\glissando" in lilypond_code:
            for gliss_override in ScoreComponent._gliss_overrides:
                abjad().attach(abjad().LilyPondLiteral(gliss_override), abjad_object, "opening")

        if r"\stemless" in lilypond_code:
            abjad().attach(abjad().LilyPondLiteral(ScoreComponent._inner_stemless_def), abjad_object, "opening")

        if r"\pitch-annotation" in lilypond_code:
            abjad().attach(abjad().LilyPondLiteral(ScoreComponent._pitch_annotation_function), abjad_object, "opening")

        return abjad_object

    def to_abjad_lilypond_file(self) -> 'abjad().LilyPondFile':
        """
        Convert and wrap as a abjad.LilyPondFile object
        """
        assert abjad() is not None, "Abjad is required for this operation."

        title = self.title if hasattr(self, "title") else None
        composer = self.composer if hasattr(self, "composer") else None
        abjad_object = self._to_abjad()
        lilypond_code = format(abjad_object)

        if r"\glissando" in lilypond_code:
            for gliss_override in ScoreComponent._gliss_overrides:
                abjad().attach(abjad().LilyPondLiteral(gliss_override), abjad_object, "opening")

        abjad_lilypond_file = abjad().LilyPondFile.new(
            music=abjad_object
        )

        # if we're actually producing the lilypond file itself, then we put the simpler
        # definition of stemless outside of the main score object.
        if r"\stemless" in lilypond_code:
            abjad_lilypond_file.items.insert(-1, ScoreComponent._outer_stemless_def)

        if r"\pitch-annotation" in lilypond_code:
            abjad_lilypond_file.items.insert(-1, ScoreComponent._pitch_annotation_function)

        if title is not None:
            abjad_lilypond_file.header_block.title = abjad().Markup(title)
        if composer is not None:
            abjad_lilypond_file.header_block.composer = abjad().Markup(composer)

        return abjad_lilypond_file

    def export_lilypond(self, file_path) -> None:
        """
        Convert and wrap as a LilyPond (.ly) file, and save to the given path.

        :param file_path: file path to save to
        """
        with open(file_path, "w") as output_file:
            output_file.write(format(self.to_abjad_lilypond_file()))

    def to_lilypond(self, wrap_as_file=False) -> str:
        """
        Convert to LilyPond code.

        :param wrap_as_file: if True, wraps this object up as a full LilyPond file, ready for compilation. If False,
            we just get the code for the component itself.
        :return: a string containing the LilyPond code
        """
        assert abjad() is not None, "Abjad is required for this operation."
        return format(self.to_abjad_lilypond_file() if wrap_as_file else self.to_abjad())

    def print_lilypond(self, wrap_as_file=False) -> None:
        """
        Convert and print LilyPond code.

        :param wrap_as_file: if True, wraps this object up as a full LilyPond file, ready for compilation. If False,
            we just get the code for the component itself.
        """
        print(self.to_lilypond(wrap_as_file=wrap_as_file))

    def show(self) -> None:
        """
        Using the abjad.show command, generates and opens a PDF of the music represented by this component
        """
        assert abjad() is not None, "Abjad is required for this operation."
        abjad().show(self.to_abjad_lilypond_file())


class ScoreContainer(ABC):
    """
    Abstract class representing a ScoreComponent that contains other components.
    (e.g. A Measure contains Voices)

    :param contents: the ScoreComponents contained within this container
    :param contents_argument_name: name of the property that fetches the contents. E.g. a score should have "parts",
        and a Staff should have "measures". The class should define that property and point it to self._contents.
        This is basically just used in __repr__ so that we don't have to implement it separately for each subclass.
    :param allowable_child_types: Type or list of types that should be allowed as child components. For instance, a
        Score can have Staff and StaffGroup children; a Measure can only have Voices.
    :param extra_field_names: again this is basically just used in __repr__ so that we don't have to implement it
        separately for each subclass.
    """

    def __init__(self, contents: Sequence[ScoreComponent], contents_argument_name: str,
                 allowable_child_types: Union[Type, Tuple[Type, ...]], extra_field_names=()):
        self._contents = contents if contents is not None else []
        self._contents_argument_name = contents_argument_name
        self._extra_field_names = extra_field_names
        self._allowable_child_types = allowable_child_types
        assert isinstance(self._contents, list) and all(isinstance(x, allowable_child_types) for x in self._contents)

    def __contains__(self, item):
        return item in self._contents

    def __delitem__(self, i):
        del self._contents[i]

    def __getitem__(self, argument):
        return self._contents.__getitem__(argument)

    def __iter__(self):
        return iter(self._contents)

    def __len__(self):
        return len(self._contents)

    def __setitem__(self, i, item):
        assert isinstance(item, self._allowable_child_types), "Incompatible child type"
        self._contents[i] = item

    def append(self, item: ScoreComponent) -> None:
        """
        Add a child ScoreComponent of the appropriate type
        """
        assert isinstance(item, self._allowable_child_types), "Incompatible child type"
        self._contents.append(item)

    def extend(self, items) -> None:
        """
        Add several child ScoreComponents of the appropriate type
        """
        assert hasattr(items, "__len__")
        assert all(isinstance(item, self._allowable_child_types) for item in items), "Incompatible child type"
        self._contents.extend(items)

    def index(self, item) -> int:
        """
        Get the index of the given child ScoreComponent
        """
        return self._contents.index(item)

    def insert(self, index, item) -> None:
        """
        Insert a child ScoreComponent at the given index.
        """
        assert isinstance(item, self._allowable_child_types), "Incompatible child type"
        return self._contents.insert(index, item)

    def pop(self, i=-1) -> ScoreComponent:
        """
        Pop and return the child ScoreComponent at the given index.
        """
        return self._contents.pop(i)

    def remove(self, item) -> None:
        """
        Remove the given child ScoreComponent.
        """
        return self._contents.remove(item)

    def __repr__(self):
        extra_args_string = "" if not hasattr(self, "_extra_field_names") \
            else ", ".join("{}={}".format(x, repr(self.__dict__[x])) for x in self._extra_field_names)
        if len(extra_args_string) > 0:
            extra_args_string += ", "
        contents_string = "\n" + textwrap.indent(",\n".join(str(x) for x in self._contents), "   ") + "\n" \
            if len(self._contents) > 0 else ""
        return "{}({}{}=[{}])".format(
            self.__class__.__name__,
            extra_args_string,
            self._contents_argument_name,
            contents_string
        )


##################################################################################################################
#                                             User-Facing Classes
##################################################################################################################


class Score(ScoreComponent, ScoreContainer):

    """
    Representation of a score in traditional western notation.
    Exportable as either LilyPond or MusicXML.

    :param parts: A list of parts represented by either StaffGroup or Staff objects
    :param title: title to be used
    :param composer: composer to be used
    :param tempo_envelope: a TempoEnvelope function describing how the tempo changes over time
    :ivar title: title to be used in the score
    :ivar composer: composer to be written on the score
    :ivar tempo_envelope: a TempoEnvelope function describing how the tempo changes over time
    """

    def __init__(self, parts: Sequence[Union['Staff', 'StaffGroup']] = None, title: str = None,
                 composer: str = None, tempo_envelope: TempoEnvelope = None):
        ScoreContainer.__init__(self, parts, "parts", (StaffGroup, Staff), ("title", "composer"))
        self.title = title
        self.composer = composer
        self.tempo_envelope = tempo_envelope

    @property
    def parts(self) -> Sequence[Union['StaffGroup', 'Staff']]:
        """
        List of parts (StaffGroup or Staff objects).
        """
        return self._contents

    @property
    def staves(self) -> Sequence['Staff']:
        """
        List of all staves in this score, expanding out those inside of StaffGroups.
        """
        # returns all the staves of all the parts in the score
        out = []
        for part in self.parts:
            if isinstance(part, StaffGroup):
                out.extend(part.staves)
            else:
                assert isinstance(part, Staff)
                out.append(part)
        return out

    def length(self) -> float:
        """
        Length of this score in beats. (i.e. end beat of the last measure in any of the parts)
        """
        return max(staff.length() for staff in self.staves)

    @classmethod
    def from_performance(cls, performance: 'performance_module.Performance',
                         quantization_scheme: QuantizationScheme = None, time_signature: Union[str, Sequence] = None,
                         bar_line_locations: Sequence[float] = None, max_divisor: int = None,
                         max_divisor_indigestibility: int = None, simplicity_preference: float = None,
                         title: str = "default", composer: str = "default") -> 'Score':
        """
        Builds a new Score from a Performance (list of note events in continuous time and pitch). In the process,
        the music must be quantized, for which two different options are available: one can either pass a
        QuantizationScheme to the first argument, which is very flexible but rather verbose to create, or one can
        specify arguments such as time_signature and max_divisor directly.

        :param performance: The Performance object we are building the score from.
        :param quantization_scheme: The quantization scheme to be used when converting this performance into a score. If
            this is defined, none of the other quantization-related arguments should be defined.
        :param time_signature: the time signature to be used, represented as a string, e.g. "3/4",  or a tuple,
            e.g. (3, 2). Alternatively, a list of time signatures can be given. If this list ends in "loop", then the
            pattern specified by the list will be looped. For example, ["4/4", "2/4", "3/4", "loop"] will cause the
            fourth measure to be in "4/4", the fifth in "2/4", etc. If the list does not end in "loop", all measures
            after the final time signature specified will continue to be in that time signature.
        :param bar_line_locations: As an alternative to defining the time signatures, a list of numbers representing
            the bar line locations can be given. For instance, [4.5, 6.5, 8, 11] would result in bars of time signatures
            9/8, 2/4, 3/8, and 3/4
        :param max_divisor: The largest divisor that will be allowed to divide the beat.
        :param max_divisor_indigestibility: Indigestibility, devised by composer Clarence Barlow, is a measure of the
            "primeness" of a beat divisor, and therefore of its complexity from the point of view of a performer. For
            instance, it is easier to divide a beat in 8 than in 7, even though 7 is a smaller number. See Clarence's
            paper here: https://mat.ucsb.edu/Publications/Quantification_of_Harmony_and_Metre.pdf. By setting a max
            indigestibility, we can allow larger divisions of the beat, but only so long as they are easy ones. For
            instance, a max_divisor of 16 and a max_divisor_indigestibility of 8 would allow the beat to be divided
            in 1, 2, 3, 4, 5, 6, 8, 9, 10, 12, and 16.
        :param simplicity_preference: This defines the degree to which the quantizer will favor simple divisors. The
            higher the simplicity preference, the more precisely the notes have to fit for you to get a divisor like 7.
            Simplicity preference can range from 0 (in which case the divisor is chosen simply based on the lowest
            error) to infinity, with a typical value somewhere around 1.
        :param title: Title of the piece to be printed on the score.
        :param composer: Composer of the piece to be printed on the score.
        :return: the resulting Score object, which can then be rendered either as XML or LilyPond
        """

        params = (time_signature, bar_line_locations, max_divisor, max_divisor_indigestibility, simplicity_preference)

        if quantization_scheme is None:
            if any(x is not None for x in params):
                quantization_scheme = QuantizationScheme.from_attributes(
                    time_signature=time_signature, bar_line_locations=bar_line_locations, max_divisor=max_divisor,
                    max_divisor_indigestibility=max_divisor_indigestibility, simplicity_preference=simplicity_preference
                )
            elif not performance.is_quantized():
                quantization_scheme = QuantizationScheme.from_time_signature(
                    quantization_settings.default_time_signature)

        elif any(x is not None for x in params):
            raise AttributeError("Either the quantization_scheme or one or more of the quantization-related arguments "
                                 "can be defined, but not both.")

        return Score.from_quantized_performance(
            performance if quantization_scheme is None else performance.quantized(quantization_scheme),
            title=title, composer=composer
        )

    @classmethod
    def from_quantized_performance(cls, performance: 'performance_module.Performance',
                                   title: str = "default", composer: str = "default") -> 'Score':
        """
        Constructs a new Score from an already quantized Performance.
        
        :param performance: the quantized Performance to convert into a new score
        :param title: title to give the score
        :param composer: composer to put on the score
        """
        if not performance.is_quantized():
            raise ValueError("Performance was not quantized.")
        contents = []
        for part in performance.parts:
            if engraving_settings.ignore_empty_parts and part.num_measures() == 0:
                # if this is an empty part, and we're not including empty parts, skip it
                continue
            staff_group = StaffGroup.from_quantized_performance_part(part)
            if len(staff_group.staves) > 1:
                contents.append(staff_group)
            elif len(staff_group.staves) == 1:
                contents.append(staff_group.staves[0])
        out = cls(
            contents,
            title=engraving_settings.get_default_title() if title == "default" else title,
            composer=engraving_settings.get_default_composer() if composer == "default" else composer,
            tempo_envelope=performance.tempo_envelope
        )
        if engraving_settings.pad_incomplete_parts:
            out._pad_incomplete_parts()
        return out

    def _pad_incomplete_parts(self):
        """
        Adds measures to parts that end early so that they last the full length of the piece.
        """
        staves = self.staves
        longest_staff = max(staves, key=lambda staff: len(staff.measures))
        longest_staff_length = len(longest_staff.measures)
        for staff in self.staves:
            while len(staff.measures) < longest_staff_length:
                corresponding_measure_in_long_staff = longest_staff.measures[len(staff.measures)]
                staff.measures.append(Measure.empty_measure(corresponding_measure_in_long_staff.time_signature,
                                                            corresponding_measure_in_long_staff.show_time_signature))

    def _get_tempo_key_points_and_guide_marks(self):
        """
        Returns a list of where the key tempo points are and a list of tuples representing the locations of any
        guide marks and the tempos that they indicate at those point. The reason for this is that occasionally a
        guide mark might be indicating the final tempo of a rit or accel, but be placed a tiny bit before that moment
        so as not to conflict with another tempo marking upon arrival.
        """
        # the tempo needs to be expressly stated at the beginning, at any change of tempo direction,
        # at the start of any stable plateau (i.e. saddle point) and at the end of the tempo envelope if not redundant
        key_points = [0.0] + self.tempo_envelope.local_extrema(include_saddle_points=True)

        # if the last segment changes tempo, we need to notate its end tempo
        if self.tempo_envelope.value_at(key_points[-1]) != self.tempo_envelope.end_level():
            key_points.append(self.tempo_envelope.end_time())

        # toss out all key points that are beyond the length of the score
        score_length = self.length()
        key_points = [x for x in key_points if x <= score_length]
        # if the score ends in the middle of an accel or rit, add a key point there
        if score_length not in key_points:
            last_key_point_before_end = max(x for x in key_points if x < score_length)
            if self.tempo_envelope.value_at(last_key_point_before_end) != self.tempo_envelope.value_at(score_length):
                key_points.insert(key_points.index(last_key_point_before_end) + 1, score_length)

        guide_marks = []
        if engraving_settings.tempo.include_guide_marks:
            for left_key_point, right_key_point in zip(key_points[:-1], key_points[1:]):
                last_tempo = self.tempo_envelope.tempo_at(left_key_point)
                t = ceil_to_multiple(left_key_point, engraving_settings.tempo.guide_mark_resolution)
                while t < floor_to_multiple(right_key_point, engraving_settings.tempo.guide_mark_resolution):
                    # guide_mark_sensitivity is the proportional change in tempo needed for a guide mark
                    sensitivity_factor = 1 + engraving_settings.tempo.guide_mark_sensitivity
                    current_tempo = self.tempo_envelope.tempo_at(t)
                    if not last_tempo / sensitivity_factor < current_tempo < last_tempo * sensitivity_factor:
                        guide_marks.append((t, self.tempo_envelope.tempo_at(t)))
                        last_tempo = current_tempo
                    t += engraving_settings.tempo.guide_mark_resolution
        else:
            # no guide marks, but we still need to give a special indication when there is a sudden
            # jump in tempo that happens after an accel or a rit. that ends at a different tempo
            for last_point, key_point in zip(key_points[:-1], key_points[1:]):
                if self.tempo_envelope.tempo_at(key_point) != self.tempo_envelope.tempo_at(key_point, True) \
                        and self.tempo_envelope.tempo_at(key_point, True) != self.tempo_envelope.tempo_at(last_point):
                    # if the tempo is different approached from the left and from the right, then this is a
                    # sudden change of tempo, and if it happens after an accel or rit, we need to indicate where
                    # that accel or rit ended before jumping tempo.
                    guide_mark_location = (key_point - min(0.25, (key_point - last_point) / 2))
                    guide_marks.append((guide_mark_location, self.tempo_envelope.tempo_at(key_point, True)))

        return key_points, guide_marks

    def _to_abjad(self):
        abjad_score = abjad().Score([part._to_abjad() for part in self.parts])
        # tempo markings will be attached to the top staff.
        # Here we sort out whether or not that staff is part of a staff group or not
        top_staff = abjad_score[0][0] if isinstance(abjad_score[0], abjad().StaffGroup) else abjad_score[0]

        # go through and add all of the tempo marks to the xml score
        key_points, guide_marks = self._get_tempo_key_points_and_guide_marks()

        measure_start = 0  # running counter of the beat at the start of the measure
        rit_or_accel_spanner_start = None  # for storing the starting leaf of a rit or accel spanner

        # go through each measure and add the tempo annotations
        for abjad_measure, score_measure in zip(top_staff, self.staves[0].measures):
            # if there's no more key points or guide marks, we're done
            if len(key_points) + len(guide_marks) == 0:
                break

            # filter down to the key points and guide marks in this measure
            key_point_and_guide_mark_displacements = [
                x - measure_start for x in key_points + [x[0] for x in guide_marks]
                if 0 <= x - measure_start < score_measure.length
            ]

            tempo_voice, mark_beats_to_skip_objects = Score._make_skip_voice_and_dict_from_mark_displacements(
                score_measure, key_point_and_guide_mark_displacements, measure_start
            )
            if len(key_point_and_guide_mark_displacements) == 0:
                # there's no tempo stuff to deal with in this measure, but if we're in the middle of a spanner,
                # then we need to keep the tempo voice going
                if rit_or_accel_spanner_start is not None:
                    abjad_measure.append(tempo_voice)
                measure_start += score_measure.length
                continue

            abjad_measure.append(tempo_voice)

            # figure out which kind of note to use as the metronome mark beat in this measure, e.g. dotted quarter in
            # compound meter. Basically if all the beats are the same length, and it's a viable note length, we use
            # that; otherwise we just use quarters
            measure_beat_lengths = score_measure.time_signature.beat_lengths
            metronome_mark_beat_length = \
                measure_beat_lengths[0] if all(x == measure_beat_lengths[0] for x in measure_beat_lengths) \
                                           and _is_single_note_length(measure_beat_lengths[0]) else 1.0

            # loop through the key points until there are none left or there are none left in this measure
            while len(key_points) > 0 and key_points[0] - measure_start < score_measure.length:
                key_point = key_points.pop(0)
                this_point_skip_object = mark_beats_to_skip_objects[key_point]

                # if we had started an accel or rit spanner, end it here
                if rit_or_accel_spanner_start is not None:
                    start_text_span, span_start_skip_object, markup_text = rit_or_accel_spanner_start
                    abjad().text_spanner([span_start_skip_object, this_point_skip_object],
                                         start_text_span=start_text_span)

                    tempo_spanner_override = r"""\once \override TextSpanner.bound-details.left-broken.text = "({})"
\once \override TextSpanner.bound-details.right.attach-dir = #-2""".format(markup_text)

                    abjad().attach(abjad().LilyPondLiteral(tempo_spanner_override, "opening"), span_start_skip_object)

                    rit_or_accel_spanner_start = None

                # figure out the tempo we're at, and the tempo we're going to next
                key_point_tempo = self.tempo_envelope.tempo_at(key_point)
                next_key_point_tempo = self.tempo_envelope.tempo_at(key_points[0]) if len(key_points) > 0 else None
                # figure out whether accel or rit to the next key point, or if none is needed
                change_indicator = None if next_key_point_tempo is None or next_key_point_tempo == key_point_tempo \
                    else "accel." if next_key_point_tempo > key_point_tempo else "rit."

                # add the metronome mark, adjusting the tempo based on the metronome_mark_beat_length
                # (note: for some reason abjad insists on either integer tempos or some nonsense involving custom
                # tempo markups in order to allow floats)
                abjad().attach(
                    abjad().MetronomeMark(
                        abjad().Duration(0.25 * metronome_mark_beat_length),
                        round(key_point_tempo / metronome_mark_beat_length)
                    ),
                    this_point_skip_object
                )

                # start the accel or rit spanner if needed
                if change_indicator is not None:
                    markup = abjad().Markup(change_indicator)
                    # to construct it later, we need to the StartTextSpan object and the skip object where it starts
                    rit_or_accel_spanner_start = abjad().StartTextSpan(left_text=markup), \
                                                 this_point_skip_object, change_indicator

            # loop through the guide marks until there are none left or there are none left in this measure
            while len(guide_marks) > 0 and guide_marks[0][0] - measure_start < score_measure.length:
                guide_mark_location, guide_mark_tempo = guide_marks.pop(0)
                this_point_skip_object = mark_beats_to_skip_objects[guide_mark_location]
                guide_mark_override = r"""\once \override Score.MetronomeMark.font-size = #-5"""
                abjad().attach(
                    abjad().MetronomeMark(
                        abjad().Duration(0.25 * metronome_mark_beat_length),
                        round(guide_mark_tempo / metronome_mark_beat_length),
                        textual_indication=" "  # this results in parentheses, though the space is unfortunate
                    ),
                    this_point_skip_object
                )
                abjad().attach(abjad().LilyPondLiteral(guide_mark_override, "opening"), this_point_skip_object)

            measure_start += score_measure.length

        return abjad_score

    @staticmethod
    def _make_skip_voice_and_dict_from_mark_displacements(score_measure, displacements, measure_start):
        """
        Returns a measure of tempo voice filled with skip objects, and a dictionary pointing the time points of the
        various tempo marks to their associated skip objects.
        """
        if len(displacements) == 0:
            skip_length = 1 / Fraction(score_measure.length / 4).denominator
            return abjad().Voice(
                [abjad().Skip(0.25 * skip_length)
                 for _ in range(int(round(score_measure.length / skip_length)))], name="TempoVoice"
            ), None

        # length of the skips in quarter notes
        min_skip = 1 / Fraction(score_measure.length).denominator
        while max(x % min_skip for x in displacements) > 0.05:
            min_skip /= 2

        skips = [abjad().Skip(0.25 * min_skip) for _ in range(int(round(score_measure.length / min_skip)))]

        # maps the beat of any of the key points and guide marks we will run into to the skip object
        # that most nearly approximates its position
        mark_beats_to_skip_objects = {x + measure_start: skips[int(x / min_skip)] for x in displacements}

        def combine_skips_as_possible(chunk, combination_size):
            # chunk is a list of skip objects of the same size, and combination size is the size we want to try to
            # merge them together into (in whole notes, using the abjad duration standard)
            if len(chunk) == 1:
                return chunk
            out = []
            skips_per_sub_chunk = int(round(combination_size / (0.25 * min_skip)))
            for sub_chunk in (chunk[i: i + skips_per_sub_chunk] for i in range(0, len(chunk), skips_per_sub_chunk)):
                if not any(x in mark_beats_to_skip_objects.values() for x in sub_chunk[1:]):
                    # we can combine the skips so long as none except the first are locations where tempo marks occur
                    combined_skip = abjad().Skip(combination_size)
                    # if a tempo mark occurs at the first skip in the chunk, we can still combine it, but we have to be
                    # careful to remap the mark_beats_to_skip_objects dictionary to point to the new combined skip
                    for x in mark_beats_to_skip_objects:
                        if mark_beats_to_skip_objects[x] == sub_chunk[0]:
                            mark_beats_to_skip_objects[x] = combined_skip
                    out.append(combined_skip)
                else:
                    out.extend(combine_skips_as_possible(sub_chunk, combination_size / 2))
            return out

        # 1 / Fraction(score_measure.length / 4).denominator gives the length (in whole notes, following the abjad
        # duration standard) of the largest un-dotted note that divides the measure. This starts by trying to chunk
        # the skips into those, then tries smaller and smaller chunks as needed
        skips = combine_skips_as_possible(skips, 1 / Fraction(score_measure.length / 4).denominator)

        # add a tempo voice filled with skip objects to attach tempo markings to
        tempo_voice = abjad().Voice(skips, name="TempoVoice")

        return tempo_voice, mark_beats_to_skip_objects

    def to_music_xml(self) -> pymusicxml.Score:
        xml_score = pymusicxml.Score([part.to_music_xml() for part in self. parts], self.title, self.composer)

        # go through and add all of the tempo marks to the xml score
        key_points, guide_marks = self._get_tempo_key_points_and_guide_marks()

        measure_start = 0  # running counter of the beat at the start of the measure
        # go through each measure and add the tempo annotations
        for xml_measure, score_measure in zip(xml_score.parts[0].measures, self.staves[0].measures):
            # if there's no more key points or guide marks, we're done
            if len(key_points) + len(guide_marks) == 0:
                break
            # list of annotations we're adding to this measure
            this_measure_annotations = []

            # figure out which kind of note to use as the metronome mark beat in this measure, e.g. dotted quarter in
            # compound meter. Basically if all the beats are the same length, and it's a viable note length, we use
            # that; otherwise we just use quarters
            measure_beat_lengths = score_measure.time_signature.beat_lengths
            metronome_mark_beat_length = \
                measure_beat_lengths[0] if all(x == measure_beat_lengths[0] for x in measure_beat_lengths) \
                                           and _is_single_note_length(measure_beat_lengths[0]) else 1.0

            # loop through the key points until there are none left or there are none left in this measure
            while len(key_points) > 0 and key_points[0] - measure_start < score_measure.length:
                key_point = key_points.pop(0)
                key_point_tempo = self.tempo_envelope.tempo_at(key_point)
                next_key_point_tempo = self.tempo_envelope.tempo_at(key_points[0]) if len(key_points) > 0 else None
                # figure out whether accel or rit to the next key point, or if none is needed
                change_indicator = None if next_key_point_tempo is None or next_key_point_tempo == key_point_tempo \
                    else "accel." if next_key_point_tempo > key_point_tempo else "rit."

                # add the metronome mark, adjusting the tempo based on the metronome_mark_beat_length
                this_measure_annotations.append(
                    (pymusicxml.MetronomeMark(metronome_mark_beat_length,
                                              round(key_point_tempo / metronome_mark_beat_length, 1)),
                     key_point - measure_start)
                )

                # add the accel or rit if needed
                if change_indicator is not None:
                    this_measure_annotations.append((pymusicxml.TextAnnotation(change_indicator, italic=True),
                                                     key_point - measure_start))

            # loop through the guide marks until there are none left or there are none left in this measure
            while len(guide_marks) > 0 and guide_marks[0][0] - measure_start < score_measure.length:
                guide_mark_location, guide_mark_tempo = guide_marks.pop(0)
                # add the guide mark
                this_measure_annotations.append(
                    (pymusicxml.MetronomeMark(metronome_mark_beat_length,
                                              round(guide_mark_tempo / metronome_mark_beat_length, 1),
                                              parentheses="yes", font_size="5"),
                     guide_mark_location - measure_start)
                )

            # sort and add all the annotations to the pymusicxml.Measure object
            this_measure_annotations.sort(key=lambda x: x[1])
            xml_measure.directions_with_displacements = this_measure_annotations
            measure_start += score_measure.length
        return xml_score


# used in arranging voices in a part
_NumberedVoiceFragment = namedtuple("_NumberedVoiceFragment", "voice_num start_measure_num measures_with_quantizations")
_NamedVoiceFragment = namedtuple("_NamedVoiceFragment", "average_pitch start_measure_num measures_with_quantizations")


class StaffGroup(ScoreComponent, ScoreContainer):

    """
    Representation of a StaffGroup (used for the multiple staves of a single instrument)

    :param staves: a list of Staff objects in this group
    :param name: the name of the staff group on the score
    """

    def __init__(self, staves: Sequence['Staff'], name: str = None,
                 clef_choices: Sequence[Union[str, Tuple[str, Real]]] = None):
        ScoreContainer.__init__(self, staves, "staves", Staff)
        self._name = name
        self.clef_choices = engraving_settings.clefs_by_instrument["default"] if clef_choices is None else clef_choices
        self._set_clefs()

    @property
    def name(self) -> str:
        """
        Name of the staff group on the score.
        """
        return self._name

    @name.setter
    def name(self, value):
        self._name = value
        for i, staff in enumerate(self.staves):
            staff.name = value if i == 0 else "{} ({})".format(value, i + 1)

    @property
    def staves(self):
        """
        List of staves in this score.
        """
        return self._contents

    @classmethod
    def from_quantized_performance_part(cls, quantized_performance_part: 'performance_module.PerformancePart') \
                                        -> 'StaffGroup':
        """
        Constructs a new StaffGroup from an already quantized PerformancePart.

        :param quantized_performance_part: an already quantized PerformancePart
        """
        assert quantized_performance_part.is_quantized()

        fragments = StaffGroup._separate_voices_into_fragments(quantized_performance_part)
        measure_voice_grid = StaffGroup._create_measure_voice_grid(fragments, quantized_performance_part.num_measures())
        staff_group_name = quantized_performance_part.name
        if quantized_performance_part.name_count() > 0:
            staff_group_name += " [{}]".format(quantized_performance_part.name_count() + 1)

        return StaffGroup._from_measure_voice_grid(
            measure_voice_grid, quantized_performance_part._get_longest_quantization_record(),
            name=staff_group_name, clef_choices=quantized_performance_part.clef_preference
        )

    @staticmethod
    def _construct_voice_fragment(voice_name, notes, start_measure_num, measure_quantizations):
        average_pitch = sum(note.average_pitch() for note in notes) / len(notes)

        # split the notes into measures, breaking notes that span a barline in two
        # save each to measures_with_quantizations, in a tuple along with the corresponding quantization
        measures_with_quantizations = []
        for measure_quantization in measure_quantizations:
            measure_end_beat = measure_quantization.start_beat + measure_quantization.measure_length
            this_measure_notes = []
            remaining_notes = []
            for note in notes:
                # check if the note starts in the measure
                if measure_quantization.start_beat <= note.start_beat < measure_end_beat:
                    # check if it straddles the following barline
                    if note.end_beat > measure_end_beat:
                        first_half, second_half = note.split_at_beat(measure_end_beat)
                        this_measure_notes.append(first_half)
                        remaining_notes.append(second_half)
                    else:
                        # note is fully within the measure
                        this_measure_notes.append(note)
                else:
                    # if it happens in a later measure, save it for later
                    remaining_notes.append(note)
            notes = remaining_notes
            measures_with_quantizations.append((this_measure_notes, measure_quantization))

        # then decide based on the name of the voice whether it is from a numbered voice, which gets treated differently
        try:
            # numbered voice
            voice_num = int(voice_name)
            return _NumberedVoiceFragment(voice_num - 1, start_measure_num, measures_with_quantizations)
        except ValueError:
            # not a numbered voice, so we want to order voices mostly by pitch
            return _NamedVoiceFragment(average_pitch, start_measure_num, measures_with_quantizations)

    @staticmethod
    def _separate_voices_into_fragments(quantized_performance_part):
        """
        Splits the part's voices into fragments where divisions occur whenever there is a measure break at a rest.
        If there's a measure break but not a rest, we're probably in the middle of a melodic gesture, so don't want to
        separate. If there's a rest but not a measure break then we should also probably keep the notes together in a
        single voice, since they were specified to be in the same voice.

        :param quantized_performance_part: a quantized PerformancePart
        :return: a tuple of (numbered_fragments, named_fragments), where the numbered_fragments come from numbered voices
            and are of the form (voice_num, notes_list, start_measure_num, end_measure_num, measure_quantization_schemes),
            while the named_fragments are of the form (notes_list, start_measure_num, end_measure_num,
            measure_quantization_schemes)
        """
        fragments = []

        for voice_name, note_list in quantized_performance_part.voices.items():
            # first we make an enumeration iterator for the measures
            if len(note_list) == 0:
                continue

            note_list = deepcopy(note_list)

            quantization_record = quantized_performance_part.voice_quantization_records[voice_name]
            assert isinstance(quantization_record, QuantizationRecord)
            measure_quantization_iterator = enumerate(quantization_record.quantized_measures)

            # the idea is that we build a current_fragment up until we encounter a rest at a barline
            # when that happens, we save the old fragment and start a new one
            current_fragment = []
            fragment_measure_quantizations = []
            current_measure_num, current_measure = next(measure_quantization_iterator)
            fragment_start_measure = 0

            for performance_note in note_list:
                # update so that current_measure is the measure that performance_note starts in
                while performance_note.start_beat >= current_measure.start_beat + current_measure.measure_length:
                    # we're past the old measure, so increment to next measure
                    current_measure_num, current_measure = next(measure_quantization_iterator)
                    # if this measure break coincides with a rest, then we start a new fragment
                    if len(current_fragment) > 0 and current_fragment[-1].end_beat < performance_note.start_beat:
                        fragments.append(StaffGroup._construct_voice_fragment(
                            voice_name, current_fragment, fragment_start_measure, fragment_measure_quantizations
                        ))
                        # reset all the fragment-building variables
                        current_fragment = []
                        fragment_measure_quantizations = []
                        fragment_start_measure = current_measure_num
                    elif len(current_fragment) == 0:
                        # don't mark the start measure until we actually have a note!
                        fragment_start_measure = current_measure_num

                # add the new note to the current fragment
                current_fragment.append(performance_note)

                # make sure that fragment_measure_quantizations has a copy of the measure this note starts in
                if len(fragment_measure_quantizations) == 0 or fragment_measure_quantizations[-1] != current_measure:
                    fragment_measure_quantizations.append(current_measure)

                # now we move forward to the end of the note, and update the measure we're on
                # (Note the > rather than a >= sign. For the end of the note, it has to actually cross the barline.)
                while performance_note.end_beat > current_measure.start_beat + current_measure.measure_length:
                    current_measure_num, current_measure = next(measure_quantization_iterator)
                    # when we cross into a new measure, add it to the measure quantizations
                    fragment_measure_quantizations.append(current_measure)

            # once we're done going through the voice, save the last fragment and move on
            if len(current_fragment) > 0:
                fragments.append(StaffGroup._construct_voice_fragment(
                    voice_name, current_fragment, fragment_start_measure, fragment_measure_quantizations)
                )

        return fragments

    @staticmethod
    def _create_measure_voice_grid(fragments, num_measures):
        numbered_fragments = []
        named_fragments = []
        while len(fragments) > 0:
            fragment = fragments.pop()
            if isinstance(fragment, _NumberedVoiceFragment):
                numbered_fragments.append(fragment)
            else:
                named_fragments.append(fragment)

        measure_grid = [[] for _ in range(num_measures)]

        def is_cell_free(which_measure, which_voice):
            return len(measure_grid[which_measure]) <= which_voice or measure_grid[which_measure][which_voice] is None

        # sort by measure number (i.e. fragment[2]) then by voice number (i.e. fragment[0])
        numbered_fragments.sort(key=lambda frag: (frag.start_measure_num, frag.voice_num))
        # sort by measure number, then by highest to lowest pitch, then by longest to shortest fragment
        named_fragments.sort(key=lambda frag: (frag.start_measure_num, -frag.average_pitch,
                                               -len(frag.measures_with_quantizations)))

        for fragment in numbered_fragments:
            assert isinstance(fragment, _NumberedVoiceFragment)
            measure_num = fragment.start_measure_num
            for measure_with_quantization in fragment.measures_with_quantizations:
                while len(measure_grid[measure_num]) <= fragment.voice_num:
                    measure_grid[measure_num].append(None)
                measure_grid[measure_num][fragment.voice_num] = measure_with_quantization
                measure_num += 1

        for fragment in named_fragments:
            assert isinstance(fragment, _NamedVoiceFragment)
            measure_range = range(fragment.start_measure_num,
                                  fragment.start_measure_num + len(fragment.measures_with_quantizations))
            voice_num = 0
            while not all(is_cell_free(measure_num, voice_num) for measure_num in measure_range):
                voice_num += 1

            measure_num = fragment.start_measure_num
            for measure_with_quantization in fragment.measures_with_quantizations:
                while len(measure_grid[measure_num]) <= voice_num:
                    measure_grid[measure_num].append(None)
                measure_grid[measure_num][voice_num] = measure_with_quantization
                measure_num += 1

        return measure_grid

    @classmethod
    def _from_measure_voice_grid(cls, measure_bins, quantization_record: QuantizationRecord, name: str = None,
                                 clef_choices: Sequence[Union[str, Tuple[str, Real]]] = None):
        """
        Creates a StaffGroup with Staves that accommodate engraving_settings.max_voices_per_part voices each

        :param measure_bins: a list of voice lists (can be many voices each)
        :param quantization_record: a QuantizationRecord
        :param name: name for the staff group; the staves will get named, e.g. "piano [1]", "piano [2]", etc.
        """
        num_staffs_required = 1 if len(measure_bins) == 0 else \
            int(max(math.ceil(len(x) / engraving_settings.max_voices_per_part) for x in measure_bins))

        # create a bunch of dummy bins for the different measures of each staff
        #             measures ->      staffs -v
        # [ [None, None, None, None, None, None, None, None],
        #   [None, None, None, None, None, None, None, None] ]
        staves = [[None] * len(measure_bins) for _ in range(num_staffs_required)]

        for measure_num, measure_voices in enumerate(measure_bins):
            # this breaks up the measure's voices into groups of length max_voices_per_part
            # (the last group might have fewer)
            voice_groups = [measure_voices[i:i + engraving_settings.max_voices_per_part]
                            for i in range(0, len(measure_voices), engraving_settings.max_voices_per_part)]

            for staff_num in range(len(staves)):
                # for each staff, check if this measure has enough voices to even reach that staff
                if staff_num < len(voice_groups):
                    # if so, let's take a look at our voices for this measure
                    this_voice_group = voice_groups[staff_num]
                    if all(x is None for x in this_voice_group):
                        # if all the voices are empty, this staff is empty for this measure. Put None to indicate that
                        staves[staff_num][measure_num] = None
                    else:
                        # otherwise, there's something there, so put tne voice group in the slot
                        staves[staff_num][measure_num] = this_voice_group
                else:
                    # if not, put None there to indicate an empty measure
                    staves[staff_num][measure_num] = None

        # At this point, each entry in the staves / measures matrix is either
        #   (1) None, indicating an empty measure
        #   (2) a list of voices, each of which is either:
        #       - a list of PerformanceNotes or
        #       - None, in the case of an empty voice

        if all(len(x) == 0 for x in staves):
            # empty staff group; none of its staves have any contents
            return cls([Staff([])])

        return cls(
            [
                Staff._from_measure_bins_of_voice_lists(
                    staff, quantization_record.time_signatures,
                    name=name + " ({})".format(str(i + 1)) if len(staves) > 1 else name
                )
                for i, staff in enumerate(staves)
            ], name=name, clef_choices=clef_choices
        )

    def _set_clefs(self):
        if engraving_settings.clef_selection_policy == "part-wise":
            average_pitch = 0
            num_notes = 0
            for staff in self.staves:
                for measure in staff.measures:
                    for voice in measure:
                        for note in voice.iterate_notes(include_rests=False):
                            average_pitch += note.average_pitch()
                            num_notes += 1
            if num_notes > 0:
                average_pitch /= num_notes
                clef_choice = _get_clef_from_average_pitch_and_clef_choices(average_pitch, self.clef_choices)
                for staff in self.staves:
                    staff.measures[0].clef = clef_choice
        else:
            assert engraving_settings.clef_selection_policy == "measure-wise"
            for staff in self.staves:
                last_clef_used = None
                for i, measure in enumerate(staff.measures):
                    this_measure_clef = measure.get_appropriate_clef(self.clef_choices)
                    if this_measure_clef is not None:
                        # there are some pitches in this measure from which to choose a clef
                        if last_clef_used is None:
                            # if we haven't yet encountered a measure with any pitches in it, set the clef for
                            # the first measure to the this clef, which is the best clef once we start getting pitches
                            last_clef_used = staff.measures[0].clef = this_measure_clef
                        elif this_measure_clef != last_clef_used:
                            # otherwise we simply check if this clef is new information. If it's different from the
                            # clef in the last measure, then we set this measure to explicitly change it
                            last_clef_used = measure.clef = this_measure_clef

    def _to_abjad(self):
        return abjad().StaffGroup([staff._to_abjad() for staff in self.staves])

    def to_music_xml(self) -> pymusicxml.PartGroup:
        return pymusicxml.PartGroup([staff.to_music_xml() for staff in self.staves])


class Staff(ScoreComponent, ScoreContainer):

    """
    Representation of a single staff of a western-notated score

    :param measures: Chronological list of Measure objects contained in this staff
    :param name: Name of this staff in the score
    """

    def __init__(self, measures: Sequence['Measure'], name: str = None):
        ScoreContainer.__init__(self, measures, "measures", Measure)
        self.name = name

    @property
    def measures(self) -> Sequence['Measure']:
        """Chronological list of Measure objects contained in this staff"""
        return self._contents

    def length(self) -> float:
        """
        Length of this Staff in beats. (i.e. end beat of its last measure)
        """
        return sum(m.length for m in self.measures[:-1]) + self.measures[-1].non_empty_length()

    @classmethod
    def _from_measure_bins_of_voice_lists(cls, measure_bins, time_signatures: Sequence[TimeSignature],
                                          name: str = None) -> 'Staff':
        """
        Constructs a Staff from a specially formatted list of measures

        :param measure_bins: Expects a list of measure bins each of which is either:

            (1) None, indicating an empty measure
            (2) a list of voices, each of which is either:
                - a list of PerformanceNotes or
                - None, in the case of an empty voice

            This format is constructed inside of StaffGroup._from_measure_voice_grid
        :param time_signatures: list of TimeSignature objects for each measure
        """
        # Expects a list of measure bins formatted as outputted by StaffGroup._from_measure_bins_of_voice_lists
        #   (1) None, indicating an empty measure
        #   (2) a list of voices, each of which is either:
        #       - a list of PerformanceNotes or
        #       - None, in the case of an empty voice
        time_signature_changes = [True] + [time_signatures[i - 1] != time_signatures[i]
                                           for i in range(1, len(time_signatures))]
        return cls([Measure.from_list_of_performance_voices(measure_content, time_signature, show_time_signature)
                    if measure_content is not None else Measure.empty_measure(time_signature, show_time_signature)
                    for measure_content, time_signature, show_time_signature in zip(measure_bins, time_signatures,
                                                                                    time_signature_changes)], name=name)

    def _to_abjad(self):
        # from the point of view of the source_id_dict (which helps us connect tied notes), the staff is
        # always going to be the top level call. There's no need to propagate the source_id_dict any further upward
        source_id_dict = {}
        contents = [measure._to_abjad(source_id_dict) for measure in self.measures]
        for same_source_group in source_id_dict.values():
            _join_same_source_abjad_note_group(same_source_group)
        abjad_staff = abjad().Staff(contents, name=self.name)
        abjad().setting(abjad_staff).instrument_name = abjad().Scheme(self.name, force_quotes=True)
        return abjad_staff

    def to_music_xml(self) -> pymusicxml.Part:
        source_id_dict = {}
        measures = [measure.to_music_xml(source_id_dict) for measure in self.measures]
        for same_source_group in source_id_dict.values():
            _join_same_source_xml_note_group(same_source_group)
        return pymusicxml.Part(self.name, measures)


_voice_names = [r'voiceOne', r'voiceTwo', r'voiceThree', r'voiceFour']
_voice_literals = [r'\voiceOne', r'\voiceTwo', r'\voiceThree', r'\voiceFour']


class Measure(ScoreComponent, ScoreContainer):
    """
    Representation of a single measure within in a Staff

    :param voices: list of voices in this measure, in numbered order
    :param time_signature: the time signature for this measure
    :param show_time_signature: whether or not to show the time signature. By default, when scamp is turning a
        quantized Performance into a Score, this will be set to true when the time signature changes and False
        otherwise.
    :param clef: Which clef to use for the measure. If none, clef is left unspecified.
    :ivar time_signature: the time signature for this measure
    :ivar show_time_signature: Whether or not to display the time signature
    :ivar clef: Which clef to use for the measure. If none, clef is left unspecified.
    """

    def __init__(self, voices: Sequence['Voice'], time_signature: TimeSignature, show_time_signature: bool = True,
                 clef: Optional[str] = None):

        ScoreContainer.__init__(self, voices, "voices", (Voice, type(None)), ("time_signature", "show_time_signature"))
        self.time_signature = time_signature
        self.show_time_signature = show_time_signature
        if clef is not None and clef not in engraving_settings.clef_pitch_centers:
            raise ValueError("Clef \"{}\" was not understood.".format(clef))
        self.clef = clef

    @property
    def voices(self) -> Sequence['Voice']:
        """List of Voices within this measure, in numbered order"""
        return self._contents

    @property
    def length(self) -> float:
        """Length of this measure in quarter notes"""
        return self.time_signature.measure_length()

    def non_empty_length(self) -> float:
        """
        Length of the part of this measure that has something in it. (i.e. the length not counting trailing rests that
        aren't part of a tuplet)
        """
        return max(v.non_empty_length() for v in self.voices)

    @classmethod
    def empty_measure(cls, time_signature: TimeSignature, show_time_signature: bool = True) -> 'Measure':
        """
        Constructs an empty measure (one voice with a bar rest)

        :param time_signature: the time signature for this measure
        :param show_time_signature: Whether or not to display the time signature
        """
        return cls([Voice.empty_voice(time_signature)], time_signature, show_time_signature=show_time_signature)

    @classmethod
    def from_list_of_performance_voices(cls, voices_list, time_signature: TimeSignature,
                                        show_time_signature: bool = True) -> 'Measure':
        """
        Constructs a Measure for a specially formatted list of voices

        :param voices_list: list consisting of elements each of which is either:
            - a (list of PerformanceNotes, measure quantization record) tuple for an active voice
            - None, for an empty voice
        :param time_signature: the time signature for this measure
        :param show_time_signature: Whether or not to display the time signature
        """
        # voices_list
        if all(voice_content is None for voice_content in voices_list):
            # if all the voices are empty, just make an empty measure
            return cls.empty_measure(time_signature, show_time_signature=show_time_signature)
        else:
            voices = []
            for i, voice_content in enumerate(voices_list):
                if voice_content is None:
                    if i == 0:
                        # an empty first voice should be expressed as a bar rest
                        voices.append(Voice.empty_voice(time_signature))
                    else:
                        # an empty other voice can just be ignored. Put a placeholder of None
                        voices.append(None)
                else:
                    # should be a (list of PerformanceNotes, measure quantization record) tuple
                    voices.append(Voice.from_performance_voice(*voice_content))
            return cls(voices, time_signature, show_time_signature=show_time_signature)

    def get_appropriate_clef(self, clef_choices: Sequence[Union[str, Tuple[str, Real]]]):
        # find the average pitch of this measure
        average_pitch = 0
        num_notes = 0
        for voice in self.voices:
            if voice is None:
                continue
            for note in voice.iterate_notes(include_rests=False):
                average_pitch += note.average_pitch()
                num_notes += 1

        if num_notes == 0:
            # return none if there's no pitches to speak of
            return None

        average_pitch /= num_notes

        return _get_clef_from_average_pitch_and_clef_choices(average_pitch, clef_choices)

    def _to_abjad(self, source_id_dict=None):
        is_top_level_call = True if source_id_dict is None else False
        source_id_dict = {} if source_id_dict is None else source_id_dict
        abjad_measure = abjad().Container()

        for i, voice in enumerate(self.voices):
            if voice is None:
                continue
            abjad_voice = self.voices[i]._to_abjad(source_id_dict)

            if i == 0 and self.show_time_signature:
                # TODO: this seems to break in abjad when the measure starts with a tuplet, so for now, a klugey fix
                # abjad().attach(self.time_signature.to_abjad(), abjad_voice[0])
                abjad().attach(abjad().LilyPondLiteral(r"\time {}".format(self.time_signature.as_string()), "opening"),
                               abjad_voice)
            if len(self.voices) > 1:
                abjad().attach(abjad().LilyPondLiteral(_voice_literals[i]), abjad_voice)
            abjad_voice.name = _voice_names[i]
            abjad_measure.append(abjad_voice)
        abjad_measure.simultaneous = True

        if is_top_level_call:
            for same_source_group in source_id_dict.values():
                _join_same_source_abjad_note_group(same_source_group)

        if self.clef is not None:
            # attach the clef to the first note of the first voice
            abjad().attach(abjad().Clef(self.clef), abjad().select(abjad_measure).leaf(0))

        return abjad_measure

    def to_music_xml(self, source_id_dict=None) -> pymusicxml.Measure:
        is_top_level_call = True if source_id_dict is None else False
        source_id_dict = {} if source_id_dict is None else source_id_dict

        xml_voices = [voice.to_music_xml(source_id_dict) if voice is not None else None
                      for voice in self.voices]
        time_signature = (self.time_signature.numerator, self.time_signature.denominator) \
            if self.show_time_signature else None

        if is_top_level_call:
            for same_source_group in source_id_dict.values():
                _join_same_source_xml_note_group(same_source_group)

        return pymusicxml.Measure(xml_voices, time_signature=time_signature, clef=self.clef)


class Voice(ScoreComponent, ScoreContainer):

    """
    Representation of a single voice within a single measure of a single staff of music.

    :param contents: list of Tuplet or NoteLike objects in this voice
    :param time_signature: the time signature of the measure to which this voice belongs
    :ivar time_signature: the time signature of the measure to which this voice belongs
    """

    def __init__(self, contents: Sequence[Union['Tuplet', 'NoteLike']], time_signature: TimeSignature):

        ScoreContainer.__init__(self, contents, "contents", (Tuplet, NoteLike), ("time_signature", ))
        self.time_signature = time_signature

    @property
    def contents(self) -> Sequence[Union['Tuplet', 'NoteLike']]:
        """list of Tuplet or NoteLike objects in this voice"""
        return self._contents

    def iterate_notes(self, include_rests: bool = False) -> Iterator['NoteLike']:
        """
        Iterate through the notes (and possibly rests) within this Voice

        :param include_rests: Whether or not to include rests
        """
        for note_or_tuplet in self.contents:
            if isinstance(note_or_tuplet, NoteLike):
                if include_rests or not note_or_tuplet.is_rest():
                    yield note_or_tuplet
            else:
                for note in note_or_tuplet.contents:
                    if include_rests or not note.is_rest():
                        yield note

    def non_empty_length(self) -> float:
        """
        Length of the part of this voice that has something in it. (i.e. the length not counting trailing rests that
        aren't part of a tuplet)
        """
        non_empty_length = self.time_signature.measure_length()
        for note_or_tuplet in reversed(self.contents):
            if isinstance(note_or_tuplet, NoteLike) and note_or_tuplet.is_rest():
                non_empty_length -= note_or_tuplet.written_length
            else:
                break
        return non_empty_length

    @classmethod
    def empty_voice(cls, time_signature: TimeSignature) -> 'Voice':
        """
        Constructs an empty voice containing simply a bar rest.

        :param time_signature: the time signature of the measure to which this voice belongs
        """
        return cls(None, time_signature)

    @classmethod
    def from_performance_voice(cls, notes: Sequence['performance_module.PerformanceNote'],
                               measure_quantization: QuantizedMeasure) -> 'Voice':
        """
        Constructs a Voice object from a list of PerformanceNotes

        (This is where a lot of the magic of converting performed notes to written symbols occurs.)

        :param notes: the list of PerformanceNotes played in this measure
        :param measure_quantization: the quantization used for this measure for this voice
        """
        length = measure_quantization.measure_length

        # split any notes that have a tuple length into segments of those lengths
        notes = [segment for note in notes for segment in note.split_at_length_divisions()]

        # change each PerformanceNote to have a start_beat relative to the start of the measure
        for note in notes:
            note.start_beat -= measure_quantization.start_beat

        notes = Voice._fill_in_rests(notes, length)
        # break notes that cross beat boundaries into two tied notes
        # later, some of these can be recombined, but we need to convert them to NoteLikes first

        notes = Voice._split_notes_at_beats(notes, [beat.start_beat_in_measure for beat in measure_quantization.beats])

        # construct the processed contents of this voice (made up of NoteLikes Tuplets)
        processed_beats = []
        for beat_quantization in measure_quantization.beats:
            notes_from_this_beat = []

            while len(notes) > 0 and \
                    notes[0].start_beat + 1e-10 < beat_quantization.start_beat_in_measure + beat_quantization.length:
                # go through all the notes in this beat
                notes_from_this_beat.append(notes.pop(0))

            processed_beats.append(Voice._process_and_convert_beat(notes_from_this_beat, beat_quantization))

        processed_contents = Voice._recombine_processed_beats(processed_beats, measure_quantization)

        # instantiate and return the constructed voice
        return cls(processed_contents, measure_quantization.time_signature)

    @staticmethod
    def _fill_in_rests(notes, total_length):
        notes_and_rests = []
        t = 0
        for note in notes:
            if t + 1e-10 < note.start_beat:
                notes_and_rests.append(performance_module.PerformanceNote(t, note.start_beat - t, None, None, {}))
            notes_and_rests.append(note)
            t = note.end_beat

        if t < total_length:
            notes_and_rests.append(performance_module.PerformanceNote(t, total_length - t, None, None, {}))
        return notes_and_rests

    @staticmethod
    def _split_notes_at_beats(notes, beats):
        for beat in beats:
            split_notes = []
            for note in notes:
                split_notes.extend(note.split_at_beat(beat))
            notes = split_notes
        return notes

    @staticmethod
    def _process_and_convert_beat(beat_notes, beat_quantization):
        beat_start = beat_notes[0].start_beat

        # this covers the case in which a single voice was quantized, some notes overlapped so it had to be split in
        # two, and the two voices were forced to share the same divisor. If this is one of those voices and it ended up
        # empty for this beat, or with a note that spanned the whole beat, divisor should just be None
        if all(note.pitch is None for note in beat_notes) or len(beat_notes) == 1:
            divisor = None
        else:
            divisor = beat_quantization.divisor

        if divisor is None:
            # if there's no beat divisor, then it should just be a note or rest of the full length of the beat
            assert len(beat_notes) == 1
            pitch, length, properties = beat_notes[0].pitch, beat_notes[0].length, beat_notes[0].properties

            if _is_single_note_length(length):
                return [NoteLike(pitch, length, properties)]
            else:
                constituent_lengths = _length_to_undotted_constituents(length)
                return [NoteLike(pitch, l, properties) for l in constituent_lengths]

        # otherwise, if the divisor requires a tuplet, we construct it
        tuplet = Tuplet.from_length_and_divisor(beat_quantization.length, divisor) if divisor is not None else None

        dilation_factor = 1 if tuplet is None else tuplet.dilation_factor()
        written_division_length = beat_quantization.length / divisor * dilation_factor

        # these versions go from small to big prime factors and vice-versa
        # so for one 6 is 3x2, for the other it's 2x3. We try both options in case one fits better
        beat_division_hierarchy = _get_beat_division_hierarchy(beat_quantization.length, divisor)
        beat_division_hierarchy2 = _get_beat_division_hierarchy(beat_quantization.length, divisor, False)

        # if they're identical (e.g. if there's only one type of prime anyway) we only need to care about one version
        if beat_division_hierarchy == beat_division_hierarchy2:
            beat_division_hierarchy2 = None

        # makes triplets get treated as worse than duplets
        _worsen_hierarchy_tuples(beat_division_hierarchy)
        if beat_division_hierarchy2 is not None:
            _worsen_hierarchy_tuples(beat_division_hierarchy2)

        note_list = tuplet.contents if tuplet is not None else []

        note_division_points_list = []
        if beat_division_hierarchy2 is not None:
            note_division_points_list2 = []
            hierarchy1_badness = 0
            hierarchy2_badness = 0

        for note in beat_notes:
            start_division = int(round((note.start_beat - beat_start) / beat_quantization.length * divisor))
            length_in_divisions = int(round(note.length_sum() / beat_quantization.length * divisor))
            end_division = start_division + length_in_divisions

            division_points1, score1 = Voice._get_division_points_for_note(
                start_division, end_division, beat_division_hierarchy, is_rest=note.pitch is None
            )
            note_division_points_list.append(division_points1)

            if beat_division_hierarchy2 is not None:
                division_points2, score2 = Voice._get_division_points_for_note(
                    start_division, end_division, beat_division_hierarchy2, is_rest=note.pitch is None
                )
                hierarchy1_badness += score1
                hierarchy2_badness += score2
                note_division_points_list2.append(division_points2)

        if beat_division_hierarchy2 is not None and hierarchy2_badness < hierarchy1_badness:
            note_division_points_list = note_division_points_list2

        for note, division_points in zip(beat_notes, note_division_points_list):
            written_length_components = [
                (div_point - last_div_point) * written_division_length
                for last_div_point, div_point in zip(division_points[:-1], division_points[1:])
            ]

            note_parts = []
            remainder = note
            for segment_length in written_length_components:

                split_note = remainder.split_at_beat(remainder.start_beat + segment_length / dilation_factor)
                if len(split_note) > 1:
                    this_segment, remainder = split_note
                else:
                    this_segment = split_note[0]

                note_parts.append(NoteLike(this_segment.pitch, segment_length, this_segment.properties))

            note_list.extend(note_parts)

        return [tuplet] if tuplet is not None else note_list

    @staticmethod
    def _get_division_points_for_note(start_division, end_division, beat_division_hierarchy, is_rest=False):
        beat_division_grids = _get_beat_division_grids(beat_division_hierarchy)[1:]
        current_division = start_division
        division_points = [current_division]

        go_again = True
        while go_again:
            go_again = False

            # starting with the widest grid, going down to the narrowest
            for beat_division_grid in beat_division_grids:
                # go through all the division points in this grid, and see if we can make it to them directly
                for division_point in beat_division_grid + [len(beat_division_hierarchy)]:
                    # if the division point is past where we are and not beyond the end of the note
                    # and if we can get there in a single note
                    if current_division < division_point <= end_division \
                            and _is_single_note_viable_grouping(division_point - current_division,
                                                                engraving_settings.max_dots_allowed):
                        division_points.append(division_point)
                        current_division = division_point
                        if division_point != end_division:
                            go_again = True
                        break
                else:
                    continue
                break

        if current_division < end_division:
            for x in _length_to_undotted_constituents(end_division - current_division):
                division_points.append(int(round(x)) + division_points[-1])

        division_points, score = _get_best_recombination_given_beat_hierarchy(
            division_points, beat_division_hierarchy, is_rest=is_rest
        )

        return division_points, score

    @staticmethod
    def _recombine_processed_beats(processed_beats, measure_quantization):
        """
        Recombine any full-beat notes that come from the same original source id where possible. E.g. make two full
        quarter-note beats into a half note, etc.

        :param processed_beats: list of beat bins (lists) of NoteLike objects
        :return: processed list of NoteLike objects
        """
        duple_subdivision, measure_beat_depths = measure_quantization.beat_depths

        measure_beat_depths = _worsen_hierarchy_tuples(measure_beat_depths, 2, in_place=False)

        combinable_groups = []
        current_group = []

        def hit_a_stopper():
            # ran into a note that can't combine with previous notes, so any current combinable group is ended
            nonlocal current_group, combinable_groups
            if len(current_group) > 1:
                combinable_groups.append(current_group)
                current_group = []
            elif len(current_group) == 1:
                combinable_groups.append(current_group[0])
                current_group = []

        t = 0
        for beat in processed_beats:
            if isinstance(beat[0], Tuplet):
                # we're only looking for non-tuplet combinations here, so a tuplet is a stopper
                hit_a_stopper()
                # it also doesn't start a new group
                combinable_groups.append(beat[0])
                t += beat[0].length()
                continue
            for note in beat:
                # to be combinable, first the note has to not be a gliss and be a duple length
                if is_x_pow_of_y(note.written_length.denominator, 2) and not note.does_glissando():
                    if len(current_group) == 0:
                        # if it's starting a group it has to be a rest or part of a single-source group
                        is_combinable = note.is_rest() or note.source_id() is not None
                    elif current_group[-1].is_rest():
                        # if it's joining a rest group, it must be a rest
                        is_combinable = note.is_rest()
                    else:
                        # if it's joining a note group, it must have the same id
                        is_combinable = current_group[-1].source_id() == note.source_id()
                else:
                    is_combinable = False

                if is_combinable:
                    note.properties["temp"]["beat_index"] = int(round(t / duple_subdivision))
                    current_group.append(note)
                else:
                    hit_a_stopper()
                    # even though this note can't combine with previous, it could be part of a new group
                    if is_x_pow_of_y(note.written_length.denominator, 2) and not note.does_glissando() \
                            and (note.is_rest() or note.source_id() is not None):
                        note.properties["temp"]["beat_index"] = int(round(t / duple_subdivision))
                        current_group.append(note)
                    else:
                        # ... or not
                        combinable_groups.append(note)
                t += note.written_length

        # the end of the measure is also a stopper
        hit_a_stopper()

        processed_contents = []
        for group in combinable_groups:
            if isinstance(group, list):
                note_division_points = [x.properties["temp"]["beat_index"] for x in group]
                note_division_points.append(note_division_points[-1] +
                                            int(round(group[-1].written_length / duple_subdivision)))

                recombined_division_points = Voice._try_all_sub_recombinations(
                    note_division_points, measure_beat_depths, group[0].is_rest()
                )

                merged_group = [group[0]]
                for note, division_point in zip(group[1:], note_division_points[1:-1]):
                    if division_point in recombined_division_points:
                        merged_group.append(note)
                    else:
                        merged_group[-1].merge_with(note)

                processed_contents.extend(merged_group)
            else:
                processed_contents.append(group)
        return processed_contents

    @staticmethod
    def _try_all_sub_recombinations(note_division_points, measure_beat_depths, is_rest=False):
        note_division_points = tuple(note_division_points) \
            if not isinstance(note_division_points, tuple) else note_division_points
        if len(note_division_points) < 3:
            return note_division_points
        recombo, _ = _get_best_recombination_given_beat_hierarchy(
            note_division_points, measure_beat_depths, is_rest=is_rest
        )
        if len(recombo) <= 3:
            return recombo
        else:
            recombo_size = len(recombo) - 1
            i = 0
            while i + recombo_size <= len(recombo):
                sub_recombo_attempt = recombo[:i] + Voice._try_all_sub_recombinations(
                    recombo[i: i + recombo_size], measure_beat_depths, is_rest=is_rest
                ) + recombo[i + recombo_size:]
                if recombo == sub_recombo_attempt:
                    i += 1
                else:
                    recombo = sub_recombo_attempt

        return recombo

    @staticmethod
    def _is_simple_mergeable_beat(beat_bin):
        # when recombining beats into longer notes, this tests for a beat simple enough to merge
        return len(beat_bin) == 1 and not isinstance(beat_bin[0], Tuplet) and not beat_bin[0].does_glissando() \
               and (beat_bin[0].is_rest() or beat_bin[0].source_id() is not None)

    def _to_abjad(self, source_id_dict=None):
        if len(self.contents) == 0:  # empty voice
            try:
                return abjad().Voice([abjad().MultimeasureRest(
                    (self.time_signature.numerator, self.time_signature.denominator)
                )])
            except abjad().exceptions.AssignabilityError:
                return abjad().Voice("R1 * {}/{}".format(self.time_signature.numerator,
                                                         self.time_signature.denominator))

        else:
            is_top_level_call = True if source_id_dict is None else False
            source_id_dict = {} if source_id_dict is None else source_id_dict
            abjad_components = [x._to_abjad(source_id_dict) for x in self.contents]
            if is_top_level_call:
                for same_source_group in source_id_dict.values():
                    _join_same_source_abjad_note_group(same_source_group)
            return abjad().Voice(abjad_components)

    def to_music_xml(self, source_id_dict=None) -> Sequence[Union[pymusicxml.BeamedGroup, _XMLNote]]:
        if len(self.contents) == 0:
            return [pymusicxml.BarRest(self.time_signature.numerator / self.time_signature.denominator * 4)]
        else:
            is_top_level_call = True if source_id_dict is None else False
            source_id_dict = {} if source_id_dict is None else source_id_dict

            t = next_beat_start = 0
            contents = list(self.contents)
            out = []
            for beat_length in self.time_signature.beat_lengths:
                next_beat_start += beat_length
                beat_group = []

                while len(contents) > 0 and t < next_beat_start:
                    this_item = contents.pop(0)
                    if isinstance(this_item, NoteLike):
                        beat_group.extend(this_item.to_music_xml(source_id_dict))
                        t += this_item.written_length
                    else:
                        assert isinstance(this_item, Tuplet)
                        if len(beat_group) > 0:
                            out.append(pymusicxml.BeamedGroup(beat_group))
                            beat_group = []
                        out.append(this_item.to_music_xml(source_id_dict))
                        t += this_item.length()

                if len(beat_group) > 0:
                    out.append(pymusicxml.BeamedGroup(beat_group))
            assert len(contents) == 0  # we should have gone through everything at this point

            if is_top_level_call:
                for same_source_group in source_id_dict.values():
                    _join_same_source_xml_note_group(same_source_group)

            return out


class Tuplet(ScoreComponent, ScoreContainer):
    """
    Representation of a Tuplet object within a single voice of music.
    Reads as: tuplet_divisions in the space of normal_divisions of division_length
    e.g. 7, 4, and 0.25 would mean '7 in the space of 4 sixteenth notes'

    :param tuplet_divisions: The new number that the tuplet is divided into
    :param normal_divisions: the normal number of divisions of division_length that would fill the time
    :param division_length: length in quarter notes of the tuplet note type
    :param contents: List of NoteLike objects (notes and rests) contained in this tuplet
    :ivar tuplet_divisions: The new number that the tuplet is divided into
    :ivar normal_divisions: the normal number of divisions of division_length that would fill the time
    :ivar division_length: length in quarter notes of the tuplet note type
    """

    def __init__(self, tuplet_divisions: int, normal_divisions: int, division_length: float,
                 contents: Sequence['NoteLike'] = None):
        ScoreContainer.__init__(self, contents, "contents", NoteLike,
                                ("tuplet_divisions", "normal_divisions", "division_length"))
        self.tuplet_divisions = tuplet_divisions
        self.normal_divisions = normal_divisions
        self.division_length = division_length

    @classmethod
    def from_length_and_divisor(cls, length: float, divisor: int) -> Optional['Tuplet']:
        """
        Constructs and returns the appropriate tuplet from the length and the divisor. Returns None if no tuplet needed.

        :param length: length of the beat in quarters
        :param divisor: divisor for the beat
        :return: a Tuplet, or None
        """
        beat_length_fraction = Fraction(length).limit_denominator()

        # 1.5 / 2 can be represented as two dotted 8ths or as a duple tuplet of 8ths.
        # if we don't want duple tuplets in compound time (i.e. beat lengths of 1.5, etc.),
        # then whenever the length of the beat division is duple, we don't use a tuplet.
        if not engraving_settings.allow_duple_tuplets_in_compound_time and \
                is_x_pow_of_y((beat_length_fraction / divisor).denominator, 2):
            return None

        # We have to figure out the ratio of tuplet divisions to normal divisions and the note type associated with
        # the normal divisions. E.g. consider a beat length of 1.5 and a tuplet of 11: normal_divisions gets set
        # initially to 3 and normal type gets set to 8, since it's 3 eighth notes long
        normal_divisions = beat_length_fraction.numerator
        # (if denominator is 1, normal type is quarter note, 2 -> eighth note, etc.)
        normal_type = 4 * beat_length_fraction.denominator

        # now, we keep dividing the beat in two until we're just about to divide it into more pieces than the divisor
        # so in our example, we start with 3 8th notes, then 6 16th notes, but we don't go up to 12 32nd notes, since
        # that is more than the beat divisor of 11. Now we know that we are looking at 11 in the space of 6 16th notes.
        while normal_divisions * 2 <= divisor:
            normal_divisions *= 2
            normal_type *= 2

        if normal_divisions == divisor:
            # if the beat divisor exactly equals the normal number, then we don't have a tuplet at all,
            # just a standard duple division. Return None to signify that
            return None
        else:
            # otherwise, construct a tuplet from our answer
            return cls(divisor, normal_divisions, 4.0 / normal_type)

    @property
    def contents(self) -> Sequence['NoteLike']:
        """List of NoteLike objects (notes and rests) contained in this tuplet"""
        return self._contents

    def dilation_factor(self) -> float:
        """
        Factor by which the amount of "room" in the tuplet is expanded. E.g. in a tripet, this factor is 3/2, since
        you can fit 3/2 as much stuff in there.
        """
        return self.tuplet_divisions / self.normal_divisions

    def length(self) -> float:
        """The actual length, in quarter notes, of the tuplet from the outside."""
        return self.normal_divisions * self.division_length

    def length_within_tuplet(self) -> float:
        """The length, in quarter notes, of the tuplet from the inside."""
        return self.tuplet_divisions * self.division_length

    def _to_abjad(self, source_id_dict=None):
        is_top_level_call = True if source_id_dict is None else False
        source_id_dict = {} if source_id_dict is None else source_id_dict
        abjad_notes = [note_like._to_abjad(source_id_dict) for note_like in self.contents]
        if is_top_level_call:
            for same_source_group in source_id_dict.values():
                _join_same_source_abjad_note_group(same_source_group)
        return abjad().Tuplet(abjad().Multiplier(self.normal_divisions, self.tuplet_divisions), abjad_notes)

    def to_music_xml(self, source_id_dict=None) -> pymusicxml.Tuplet:
        is_top_level_call = True if source_id_dict is None else False
        source_id_dict = {} if source_id_dict is None else source_id_dict
        xml_note_segments = [note_segment for note_like in self.contents
                             for note_segment in note_like.to_music_xml(source_id_dict)]
        if is_top_level_call:
            for same_source_group in source_id_dict.values():
                _join_same_source_xml_note_group(same_source_group)
        return pymusicxml.Tuplet(xml_note_segments, (self.tuplet_divisions, self.normal_divisions))


class NoteLike(ScoreComponent):
    """
    Represents a note, chord, or rest that can be notated without ties

    :param pitch: float if single pitch, Envelope if a glissando, tuple if a chord, None if a rest
    :param written_length: the notated length of the note, disregarding any tuplets it is part of
    :param properties: a properties dictionary, same as found in a PerformanceNote
    :ivar pitch: float if single pitch, Envelope if a glissando, tuple if a chord, None if a rest
    :ivar written_length: the notated length of the note, disregarding any tuplets it is part of
    :ivar properties: a properties dictionary, same as found in a PerformanceNote
    """

    def __init__(self, pitch: Union[Envelope, float, Tuple, None], written_length: float,
                 properties: NoteProperties):

        self.pitch = pitch
        self.written_length = Fraction(written_length).limit_denominator()
        self.properties = properties if isinstance(properties, NoteProperties) \
            else NoteProperties.from_unknown_format(properties)

    def is_rest(self) -> bool:
        """Returns whether or not this is a rest."""
        return self.pitch is None

    def is_chord(self) -> bool:
        """Returns whether or not this is a chord."""
        return isinstance(self.pitch, tuple)

    def does_glissando(self):
        """Returns whether or not this does a glissando."""
        return self.is_chord() and isinstance(self.pitch[0], Envelope) or isinstance(self.pitch, Envelope)

    def average_pitch(self) -> float:
        """
        Averages the pitch of this note, accounting for if it's a glissando or a chord

        :return: the averaged pitch as a float
        """
        if self.is_chord():
            # it's a chord, so take the average of its members
            return sum(x.average_level() if isinstance(x, Envelope) else x for x in self.pitch) / len(self.pitch)
        else:
            return self.pitch.average_level() if isinstance(self.pitch, Envelope) else self.pitch

    def _get_attack_articulations(self):
        # articulations to be placed on the main note
        return [a for a in self.properties.articulations if a not in engraving_settings.articulation_split_protocols
                or engraving_settings.articulation_split_protocols[a] in ("first", "both", "all")]

    def _get_release_articulations(self):
        # articulations to be placed on the last note of the gliss
        return [a for a in self.properties.articulations if a not in engraving_settings.articulation_split_protocols
                or engraving_settings.articulation_split_protocols[a] in ("last", "both", "all")]

    def _get_inner_articulations(self):
        # articulations to be placed on the inner notes of a gliss
        return [a for a in self.properties.articulations if a not in engraving_settings.articulation_split_protocols
                or engraving_settings.articulation_split_protocols[a] == "all"]

    def merge_with(self, other: 'NoteLike') -> 'NoteLike':
        """
        Merges other into this note, adding its length and combining its articulations

        :param other: another NoteLike
        :return: self, having been merged with other
        """
        if self.is_rest() and other.is_rest() or other.source_id() == self.source_id() is not None:
            self.properties.articulations.extend(other.properties.articulations)
            self.written_length += other.written_length
            self.properties["_starts_tie"] = other.properties.starts_tie()
        else:
            raise ValueError("Notes are not compatible for merger.")

    @staticmethod
    def _get_relevant_gliss_control_points(pitch_envelope, max_points_to_keep=None):
        """
        The idea here is that the control points that matter are the ones that aren't near others or an endpoint
        (temporal_relevance) and are a significant deviation in pitch from the assumed interpolated pitch if we
        didn't notate them (pitch_deviation).

        :param pitch_envelope: a pitch Envelope (gliss)
        :return: a list of the important control points
        """
        assert isinstance(pitch_envelope, Envelope)
        controls_to_check = pitch_envelope.times[1:-1] \
            if engraving_settings.glissandi.consider_non_extrema_control_points else pitch_envelope.local_extrema()

        relevant_controls = []
        left_bound = pitch_envelope.start_time()
        last_pitch = pitch_envelope.start_level()
        for control_point in controls_to_check:
            progress_to_endpoint = (control_point - left_bound) / (pitch_envelope.end_time() - left_bound)
            temporal_relevance = 1 - abs(0.5 - progress_to_endpoint) * 2
            # figure out how much the pitch at this control point deviates from just linear interpolation
            linear_interpolated_pitch = last_pitch + (pitch_envelope.end_level() - last_pitch) * progress_to_endpoint
            pitch_deviation = abs(pitch_envelope.value_at(control_point) - linear_interpolated_pitch)
            relevance = temporal_relevance * pitch_deviation
            if relevance > engraving_settings.glissandi.inner_grace_relevance_threshold:
                if max_points_to_keep is not None:
                    relevant_controls.append((relevance, control_point))
                else:
                    relevant_controls.append(control_point)
                left_bound = control_point
                last_pitch = pitch_envelope.value_at(control_point)

        if max_points_to_keep is not None:
            control_points = [x[1] for x in sorted(relevant_controls, reverse=True)[:max_points_to_keep]]
            control_points.sort()
            return control_points
        else:
            return relevant_controls

    def _get_grace_points(self, control_point_limit=None):
        pitch_curve = self.pitch[0] if self.is_chord() else self.pitch

        # if this note doesn't start a tie, then it's the last note of the glissando,
        # so if the settings say to do so, we include an end grace note
        include_end_point = not self.properties.starts_tie() and engraving_settings.glissandi.include_end_grace_note
        # in that case, it has to count towards the control point limit if there is one
        if control_point_limit is not None and include_end_point:
            control_point_limit -= 1

        grace_points = NoteLike._get_relevant_gliss_control_points(pitch_curve, control_point_limit) \
            if engraving_settings.glissandi.control_point_policy == "grace" else []

        if include_end_point:
            grace_points.append(pitch_curve.end_time())

        return grace_points

    def _to_abjad(self, source_id_dict=None):
        """
        Convert this NoteLike to an abjad note, chord, or rest, along with possibly some headless grace notes to
        represent important changes of direction in a glissando, if the glissando engraving setting are set to do so

        :param source_id_dict: a dictionary keeping track of which abjad notes come from the same original
            PerformanceNote. This is populated here when the abjad notes are generated, and then later, once a whole
            staff of notes has been generated, ties and glissandi are added accordingly.
        :return: an abjad note, chord, or rest, possibly with an attached AfterGraceContainer
        """
        # abjad duration
        duration = Fraction(self.written_length / 4).limit_denominator()
        # list of gliss grace notes, if applicable
        grace_notes = []

        if self.is_rest():
            abjad_object = abjad().Rest(duration)
        elif self.is_chord():
            abjad_object = abjad().Chord()
            abjad_object.written_duration = duration

            if self.does_glissando():
                # if it's a glissing chord, its noteheads are based on the start level
                abjad_object.note_heads = [self.properties.spelling_policy.resolve_abjad_pitch(x.start_level())
                                           for x in self.pitch]
                # Set the notehead
                self._set_abjad_note_head_styles(abjad_object)
                self._attach_abjad_microtonal_annotation(abjad_object, [p.start_level() for p in self.pitch])
                last_pitches = abjad_object.written_pitches

                grace_points = self._get_grace_points()

                # add a grace chord for each important turn around point in the gliss
                for t in grace_points:
                    grace_chord = abjad().Chord()
                    grace_chord.written_duration = 1/16
                    grace_chord.note_heads = [self.properties.spelling_policy.resolve_abjad_pitch(x.value_at(t))
                                              for x in self.pitch]
                    # Set the notehead
                    self._set_abjad_note_head_styles(grace_chord)
                    self._attach_abjad_microtonal_annotation(grace_chord, [p.value_at(t) for p in self.pitch])
                    # but first check that we're not just repeating the last grace chord
                    if grace_chord.written_pitches != last_pitches:
                        grace_notes.append(grace_chord)
                        last_pitches = grace_chord.written_pitches
            else:
                # if not, our job is simple
                abjad_object.note_heads = [self.properties.spelling_policy.resolve_abjad_pitch(x) for x in self.pitch]
                # Set the noteheads
                self._set_abjad_note_head_styles(abjad_object)
                # attach any microtonal annotations (if setting is flipped)
                self._attach_abjad_microtonal_annotation(abjad_object, self.pitch)

        elif self.does_glissando():
            # This is a note doing a glissando
            abjad_object = abjad().Note(self.properties.spelling_policy.resolve_abjad_pitch(self.pitch.start_level()),
                                        duration)
            # Set the notehead
            self._set_abjad_note_head_styles(abjad_object)
            # attach any microtonal annotations (if setting is flipped)
            self._attach_abjad_microtonal_annotation(abjad_object, self.pitch.start_level())

            last_pitch = abjad_object.written_pitch

            grace_points = self._get_grace_points()

            for t in grace_points:
                grace = abjad().Note(self.properties.spelling_policy.resolve_abjad_pitch(self.pitch.value_at(t)), 1 / 16)

                # Set the notehead
                self._set_abjad_note_head_styles(grace)
                # attach any microtonal annotations (if setting is flipped)
                self._attach_abjad_microtonal_annotation(grace, self.pitch.value_at(t))
                # but first check that we're not just repeating the last grace note pitch
                if last_pitch != grace.written_pitch:
                    grace_notes.append(grace)
                    last_pitch = grace.written_pitch
        else:
            # This is a simple note
            abjad_object = abjad().Note(self.properties.spelling_policy.resolve_abjad_pitch(self.pitch), duration)
            # Set the notehead
            self._set_abjad_note_head_styles(abjad_object)
            self._attach_abjad_microtonal_annotation(abjad_object, self.pitch)

        # Now we make, fill, and attach the abjad AfterGraceContainer, if applicable
        if len(grace_notes) > 0:
            for note in grace_notes:
                # this signifier, \stemless, is not standard lilypond, and is defined with
                # an override at the start of the score
                abjad().attach(abjad().LilyPondLiteral(r"\stemless"), note)
            grace_container = abjad().AfterGraceContainer(grace_notes)
            abjad().attach(grace_container, abjad_object)
        else:
            grace_container = None

        # this is where we populate the source_id_dict passed down to us from the top level "to_abjad()" call
        if source_id_dict is not None:
            # sometimes a note will not have a _source_id property defined, since it never gets broken into tied
            # components. However, if it's a glissando and there's stemless grace notes involved, we're going to
            # have to give it a _source_id so that it can share it with its grace notes
            if grace_container is not None and "_source_id" not in self.properties.temp:
                self.properties.temp["_source_id"] = performance_module.PerformanceNote.next_id()

            if "_source_id" in self.properties.temp:
                # here we take the new note that we're creating and add it to the bin in source_id_dict that
                # contains all the notes of the same source, so that they can be tied / joined by glissandi
                if self.properties.temp["_source_id"] in source_id_dict:
                    # this source_id is already associated with a leaf, so add it to the list
                    source_id_dict[self.properties.temp["_source_id"]].append(abjad_object)
                else:
                    # we don't yet have a record on this source_id, so start a list with this object under that key
                    source_id_dict[self.properties.temp["_source_id"]] = [abjad_object]

                # add any grace notes to the same bin as their parent
                if grace_container is not None:
                    source_id_dict[self.properties.temp["_source_id"]].extend(grace_container)

        self._attach_abjad_articulations(abjad_object, grace_container)
        self._attach_abjad_texts(abjad_object)
        return abjad_object

    def _attach_abjad_microtonal_annotation(self, note_object, pitch_or_pitches):
        if not engraving_settings.show_microtonal_annotations or \
                self.properties.ends_tie() and not self.does_glissando():
            # if this is not the first segment of the note, and it's not part of a gliss, don't do the annotations
            return
        if hasattr(pitch_or_pitches, '__len__'):
            if any(round(p, engraving_settings.microtonal_annotation_digits) != round(p) for p in pitch_or_pitches):
                abjad().attach(abjad().Markup(
                    abjad().MarkupCommand(
                        'pitch-annotation',
                        "; ".join(str(round(p, engraving_settings.microtonal_annotation_digits))
                                  for p in pitch_or_pitches)
                    ), direction=abjad().Up), note_object)
        else:
            if round(pitch_or_pitches, engraving_settings.microtonal_annotation_digits) != round(pitch_or_pitches):
                abjad().attach(abjad().Markup(
                    abjad().MarkupCommand(
                        'pitch-annotation', str(round(pitch_or_pitches, engraving_settings.microtonal_annotation_digits))
                    ), direction=abjad().Up), note_object)

    def _set_abjad_note_head_styles(self, abjad_note_or_chord):
        if isinstance(abjad_note_or_chord, abjad().Note):
            note_head_style = self.properties.noteheads[0]
            if note_head_style != "normal":
                lilypond_style = get_lilypond_notehead_name(note_head_style)
                # the pipe separates out a bit of comment text, which is used when the
                # desired notehead can't be displayed
                abjad().tweak(abjad_note_or_chord.note_head).style = lilypond_style.split("|")[0]
                if len(lilypond_style.split("|")) > 1:
                    abjad().attach(abjad().LilyPondComment(lilypond_style.split("|")[1]), abjad_note_or_chord)
        elif isinstance(abjad_note_or_chord, abjad().Chord):
            for chord_member, note_head_style in enumerate(self.properties.noteheads):
                if note_head_style != "normal":
                    lilypond_style = get_lilypond_notehead_name(note_head_style)
                    abjad().tweak(abjad_note_or_chord.note_heads[chord_member]).style = lilypond_style.split("|")[0]
                    if len(lilypond_style.split("|")) > 1:
                        abjad().attach(abjad().LilyPondComment(lilypond_style.split("|")[1]), abjad_note_or_chord)
        else:
            raise ValueError("Must be an abjad Note or Chord object")

    def _attach_abjad_articulations(self, abjad_note_or_chord, grace_container):
        if grace_container is None:
            # just a single notehead, so attach all articulations
            for articulation in self.properties.articulations:
                abjad().attach(abjad().Articulation(articulation), abjad_note_or_chord)
        else:
            # there's a gliss
            attack_notehead = abjad_note_or_chord if not self.properties.ends_tie() else None
            release_notehead = grace_container[-1] if not self.properties.starts_tie() else None
            inner_noteheads = ([] if attack_notehead is not None else [abjad_note_or_chord]) + \
                              [grace for grace in grace_container[:-1]] + \
                              ([] if release_notehead is not None else [grace_container[-1]])

            # only attach attack articulations to the main note
            if attack_notehead is not None:
                for articulation in self._get_attack_articulations():
                    abjad().attach(abjad().Articulation(articulation), abjad_note_or_chord)
            # attach inner articulations to all but the last notehead in the grace container
            for articulation in self._get_inner_articulations():
                for grace_note in inner_noteheads:
                    abjad().attach(abjad().Articulation(articulation), grace_note)
            # attach release articulations to the last notehead in the grace container
            if release_notehead is not None:
                for articulation in self._get_release_articulations():
                    abjad().attach(abjad().Articulation(articulation), grace_container[-1])

    def _attach_abjad_texts(self, abjad_note_or_chord):
        for text in self.properties.texts:
            assert isinstance(text, StaffText)
            abjad().attach(text.to_abjad(), abjad_note_or_chord)

    def to_music_xml(self, source_id_dict=None) -> Sequence[_XMLNote]:
        notations = [notations_to_xml_notations_element[x] for x in self.properties.notations
                     if x in notations_to_xml_notations_element]
        if self.is_rest():
            return pymusicxml.Rest(self.written_length),
        elif self.is_chord():
            start_pitches = tuple(p.start_level() if isinstance(p, Envelope) else p for p in self.pitch)

            directions = self._get_xml_microtonal_annotation(start_pitches)
            # add text annotations from properties
            if len(self.properties.texts) > 0:
                directions += tuple(text.to_pymusicxml() for text in self.properties.texts)

            out = [pymusicxml.Chord(
                tuple(self.properties.spelling_policy.resolve_music_xml_pitch(p) for p in start_pitches),
                self.written_length, ties=self._get_xml_tie_state(),
                noteheads=tuple(get_xml_notehead(notehead) if notehead != "normal" else None
                                for notehead in self.properties.noteheads),
                directions=directions, notations=notations
            )]
            if self.does_glissando():
                grace_points = self._get_grace_points(engraving_settings.glissandi.max_inner_graces_music_xml)
                for t in grace_points:
                    pitch_values = [p.value_at(t) if isinstance(p, Envelope) else p for p in self.pitch]
                    these_pitches = tuple(self.properties.spelling_policy.resolve_music_xml_pitch(p)
                                          for p in pitch_values)

                    # only add a grace chord if it differs in pitch from the last chord / grace chord
                    if these_pitches[0] != out[-1].pitches[0]:
                        out.append(pymusicxml.GraceChord(
                            these_pitches, 0.5, stemless=True,
                            noteheads=tuple(get_xml_notehead(notehead) if notehead != "normal" else None
                                            for notehead in self.properties.noteheads),
                            directions=self._get_xml_microtonal_annotation(pitch_values)
                        ))

        else:
            start_pitch = self.pitch.start_level() if isinstance(self.pitch, Envelope) else self.pitch

            directions = self._get_xml_microtonal_annotation(start_pitch)
            # add text annotations from properties
            if len(self.properties.texts) > 0:
                directions += tuple(text.to_pymusicxml() for text in self.properties.texts)

            out = [pymusicxml.Note(
                self.properties.spelling_policy.resolve_music_xml_pitch(start_pitch),
                self.written_length, ties=self._get_xml_tie_state(),
                notehead=(get_xml_notehead(self.properties.noteheads[0])
                          if self.properties.noteheads[0] != "normal" else None),
                directions=directions, notations=notations
            )]
            if self.does_glissando():
                grace_points = self._get_grace_points(engraving_settings.glissandi.max_inner_graces_music_xml)
                for t in grace_points:
                    this_pitch = self.properties.spelling_policy.resolve_music_xml_pitch(self.pitch.value_at(t))
                    # only add a grace note if it differs in pitch from the last note / grace note
                    if this_pitch != out[-1].pitch:
                        out.append(pymusicxml.GraceNote(
                            this_pitch, 0.5, stemless=True,
                            notehead=(get_xml_notehead(self.properties.noteheads[0])
                                      if self.properties.noteheads[0] != "normal" else None),
                            directions=self._get_xml_microtonal_annotation(self.pitch.value_at(t))
                        ))

        self._attach_articulations_to_xml_note_group(out)

        if source_id_dict is not None and self.does_glissando():
            # this is where we populate the source_id_dict passed down to us from the top level "to_music_xml()" call
            # sometimes a note will not have a _source_id property defined, since it never gets broken into tied
            # components. However, if it's a glissando and there's stemless grace notes involved, we're going to
            # have to give it a _source_id so that it can share it with its grace notes
            if "_source_id" not in self.properties.temp:
                self.properties.temp["_source_id"] = performance_module.PerformanceNote.next_id()

            # here we take the new note that we're creating and add it to the bin in source_id_dict that
            # contains all the notes of the same source, so that they can be joined by glissandi
            if self.properties.temp["_source_id"] in source_id_dict:
                # this source_id is already associated with a leaf, so add it to the list
                source_id_dict[self.properties.temp["_source_id"]].extend(out)
            else:
                # we don't yet have a record on this source_id, so start a list with this object under that key
                source_id_dict[self.properties.temp["_source_id"]] = list(out)

        return out

    def _get_xml_microtonal_annotation(self, pitch_or_pitches):
        if not engraving_settings.show_microtonal_annotations or \
                self.properties.ends_tie() and not self.does_glissando():
            # if this is not the first segment of the note, and it's not part of a gliss, don't do the annotations
            return ()
        if hasattr(pitch_or_pitches, '__len__'):
            # if any of the starting pitches are not integers, and we are showing microtonal annotations,
            # returns a text direction stating what the true pitches of the chord should be
            if any(round(p, engraving_settings.microtonal_annotation_digits) != round(p) for p in pitch_or_pitches):
                return pymusicxml.TextAnnotation("({})".format(
                    "; ".join(str(round(p, engraving_settings.microtonal_annotation_digits)) for p in pitch_or_pitches)
                ), italic=True),
            else:
                return ()
        else:
            # if the starting pitch is not an integer, and we are showing microtonal annotations,
            # add a text direction stating what the true pitch of the note should be
            if round(pitch_or_pitches, engraving_settings.microtonal_annotation_digits) != round(pitch_or_pitches):
                return pymusicxml.TextAnnotation(
                    "({})".format(round(pitch_or_pitches, engraving_settings.microtonal_annotation_digits)),
                    italic=True
                ),
            else:
                return ()

    @staticmethod
    def _attach_articulation_to_xml_note_or_chord(articulation, xml_note_or_chord):
        articulation = articulation_to_xml_element_name[articulation]
        if isinstance(xml_note_or_chord, pymusicxml.Note):
            xml_note_or_chord.articulations.append(articulation)
        else:
            assert isinstance(xml_note_or_chord, pymusicxml.Chord)
            xml_note_or_chord.notes[0].articulations.append(articulation)

    def _attach_articulations_to_xml_note_group(self, xml_note_group):
        if len(xml_note_group) > 1:
            # there's a gliss, and xml_note_group contains the main note followed by grace notes
            attack_notehead = xml_note_group[0] if not self.properties.ends_tie() else None
            release_notehead = xml_note_group[-1] if not self.properties.starts_tie() else None
            inner_noteheads = xml_note_group[1 if attack_notehead is not None else 0:
                                             -1 if release_notehead is not None else None]

            # only attach attack articulations to the main note
            if attack_notehead is not None:
                for articulation in self._get_attack_articulations():
                    NoteLike._attach_articulation_to_xml_note_or_chord(articulation, attack_notehead)
            # attach inner articulations to inner grace notes
            for articulation in self._get_inner_articulations():
                for inner_grace_note in inner_noteheads:
                    NoteLike._attach_articulation_to_xml_note_or_chord(articulation, inner_grace_note)
            # attach release articulations to the last grace note
            if release_notehead is not None:
                for articulation in self._get_release_articulations():
                    NoteLike._attach_articulation_to_xml_note_or_chord(articulation, release_notehead)
        else:
            # just a single notehead, so attach all articulations
            for articulation in self.properties.articulations:
                NoteLike._attach_articulation_to_xml_note_or_chord(articulation, xml_note_group[0])

    def _get_xml_tie_state(self):
        if self.properties.starts_tie() and self.properties.ends_tie():
            return "continue"
        elif self.properties.starts_tie():
            return "start"
        elif self.properties.ends_tie():
            return "stop"
        else:
            return None

    def source_id(self) -> Optional[int]:
        """
        ID representing the original PerformanceNote that this came from.
        Since PerformanceNotes are split up into tied segments, we need to keep track of which ones
        belonged together so that we can rejoin them with ties, glissandi, etc.
        (This is done via _join_same_source_abjad_note_group or _join_same_source_xml_note_group)
        """
        if "_source_id" in self.properties.temp:
            return self.properties.temp["_source_id"]
        else:
            return None

    def __repr__(self):
        return "NoteLike(pitch={}, written_length={}, properties={})".format(
            self.pitch, self.written_length, self.properties
        )
