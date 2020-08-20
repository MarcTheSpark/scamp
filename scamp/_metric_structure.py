"""
Contains the MetricStructure class, which provides a highly flexible representation of a metric hierarchy. This can
used to describe how low-level pulses/subdivisions come together to form beats, meters, hypermeters, etc., and
allows us to get an indispensability array for such a structure, or to get an array of beat depths, representing how
many layers of subdivision a particular time point occurs at. The indispensability array
is my own reimplementation and extension of Clarence Barlow's concept of indispensibility such that it works for
additive meters (even nested additive meters).
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

from itertools import chain, count
from copy import deepcopy
import operator
import functools
from typing import Union, Sequence, List, TypeVar


INT_OR_FLOAT = TypeVar("IntOrFloat", int, float)


def _rotate_list(l, n):
    return l[n:] + l[:n]


def _decompose_to_twos_and_threes(n):
    """
    Split an integer into a list of 2's and possible one 3 that add up to it

    :param n: the int
    :return: a list of 2's and possible one three
    """
    if not isinstance(n, int) and n >= 2:
        raise ValueError("n must be an integer greater than or equal to 2.")
    out = []
    if n % 2 == 1:
        n -= 3
        out.append(3)

    while n > 0:
        n -= 2
        out.append(2)

    out.reverse()
    return out


def _depth(seq):
    """
    Find the maximum _depth of any element in a nested sequence. Slightly adapted from pillmuncher's answer here:
    https://stackoverflow.com/questions/6039103/counting-depth-or-the-deepest-level-a-nested-list-goes-to

    :param seq: a nested Sequence (list, tuple, etc)
    :return: int representing maximum _depth
    """
    if not isinstance(seq, Sequence):
        return 0
    seq = iter(seq)
    try:
        for level in count():
            seq = chain([next(seq)], seq)
            seq = chain.from_iterable(s for s in seq if isinstance(s, Sequence))
    except StopIteration:
        return level


def _normalize_depth(input_list, in_place=True):
    """
    Modifies a list, wrapping parts of it in new lists, so that every element is at uniform _depth.

    :param input_list: a list
    :param in_place: if False, the original list remains unchanged
    :return: a modified version of that list with each element at uniform _depth
    """
    if not in_place:
        input_list = deepcopy(input_list)

    max_depth = max(_depth(element) for element in input_list)
    for i in range(len(input_list)):
        while _depth(input_list[i]) < max_depth:
            input_list[i] = [input_list[i]]
    for element in input_list:
        if isinstance(element, list):
            _normalize_depth(element)
    return input_list


class MeterArithmeticGroup:

    """
    This class exists as an aid to parsing arithmetic expressions into MetricStructures.
    Simply defining __add__ and __mul__ for MetricStructure wasn't flexible enough, since it was important to
    differentiate between, say, a "4 + 2 + 3" meter and a "(4 + 2) + 3" meter. The former establishes a flat
    hierarchy with three groups, whereas the latter establishes a nested hierarchy with two groups, the first of
    which is split into two smaller groups.

    :param elements: a list of MeterArithmeticGroups or integers representing simple beat groups
    :param operation: either "+", "*", or None, in the case of just a number
    """

    def __init__(self, elements: Sequence[Union['MeterArithmeticGroup', int]], operation: Union[str, None]):
        if operation is None:
            if not (len(elements) == 1 and isinstance(elements[0], int)):
                raise ValueError("\"operation\" can only be None if a single integer element is given.")
        elif operation not in ("+", "*"):
            raise ValueError("\"operation\" must be one of: (\"+\", \"*\", None).")
        self.elements = elements
        self.operation = operation

    @classmethod
    def parse(cls, input_string: str) -> 'MeterArithmeticGroup':
        """
        Parses an input string containing an arithmetic expression into a (probably nested) MeterArithmeticGroup. For
        instance an input string of "(3+2)+3*2" will be parsed as::

            MeterArithmeticGroup(
                [MeterArithmeticGroup([MeterArithmeticGroup([3], "None"), MeterArithmeticGroup([2], "None")], "+"),
                MeterArithmeticGroup([MeterArithmeticGroup([3], "None"), MeterArithmeticGroup([2], "None")], "*")],
                "+"
            )

        :param input_string: input string consisting of integers, plus signs, multiplication signs, and parentheses
        :return: a MeterArithmeticGroup
        """
        input_string = input_string.replace(" ", "")
        if len(input_string) == 0:
            raise ValueError("Cannot parse empty input string.")
        if not all(x in "0123456789+*()" for x in input_string):
            raise ValueError("Meter arithmetic expression can only contain integers, "
                             "plus signs, multiplication signs, and parentheses")
        if not (input_string[0] in "(0123456789" and input_string[-1] in ")0123456789"):
            raise ValueError("Bad input string: leading or trailing operator.")
        if any(x in input_string for x in ("++", "+*", "*+", "**")):
            raise ValueError("Cannot parse input string: multiple adjacent operators found.")
        if any(c in input_string for c in ("(", ")", "*", "+")):
            paren_level = 0
            chunks = []
            current_chunk = ""
            for char in input_string:
                if paren_level == 0 and char in ("+", "*"):
                    if len(current_chunk) > 0:
                        chunks.append(current_chunk)
                    current_chunk = ""
                    chunks.append(char)
                    continue
                if char == "(":
                    paren_level += 1
                    if paren_level == 1:
                        # don't include the outer level of parentheses
                        continue
                elif char == ")":
                    paren_level -= 1
                    if paren_level < 0:
                        raise ValueError("Encountered unmatched closes-parenthesis.")
                    if paren_level == 0:
                        chunks.append(current_chunk)
                        current_chunk = ""
                    if paren_level == 0:
                        # don't include the outer level of parentheses
                        continue
                current_chunk += char
            if len(current_chunk) > 0:
                chunks.append(current_chunk)

            if paren_level > 0:
                raise ValueError("Encountered unmatched open-parenthesis.")

            merged_multiplies = []
            i = 0
            while i < len(chunks):
                if i + 1 < len(chunks) and chunks[i + 1] == "*":
                    multiplied_elements = chunks[i:i + 3:2]
                    i += 3
                    while i < len(chunks) and chunks[i] == "*":
                        multiplied_elements.append(chunks[i + 1])
                        i += 2
                    merged_multiplies.append(
                        MeterArithmeticGroup([MeterArithmeticGroup.parse(x) for x in multiplied_elements], "*"))
                else:
                    merged_multiplies.append(chunks[i])
                    i += 1
            return MeterArithmeticGroup(
                [x if isinstance(x, MeterArithmeticGroup)
                 else MeterArithmeticGroup.parse(x) for x in merged_multiplies if x != "+"], "+"
            )
        else:
            return MeterArithmeticGroup([int(input_string)], None)

    def to_metric_structure(self, break_up_large_numbers: bool = False) -> 'MetricStructure':
        """
        Renders this arithmetic group as a :class:`MetricStructure`.

        :param break_up_large_numbers: see :class:`MetricStructure`
        """
        if self.operation is None:
            return MetricStructure(self.elements[0], break_up_large_numbers=break_up_large_numbers)
        elif self.operation == "+":
            return MetricStructure(*[x.to_metric_structure(break_up_large_numbers) for x in self.elements],
                                   break_up_large_numbers=break_up_large_numbers)
        else:
            return functools.reduce(operator.mul, (x.to_metric_structure(break_up_large_numbers) for x in self.elements))

    def __repr__(self):
        return "MeterArithmeticGroup({}, \"{}\")".format(self.elements, self.operation)


def flatten_beat_groups(beat_groups: List[List], upbeats_before_group_length: bool = True) -> List:
    """
    Returns a flattened version of beat_groups, unraveling the outer layer according to rules of indispensability.
    Repeated application of this function to nested beat groups leads to a 1-d ordered list of beat priorities

    :param beat_groups: list of nested beat group
    :param upbeats_before_group_length: This is best explained with an example. Consider a 5 = 2 + 3 beat pattern.
        The Barlow approach to indispensability would give indispensabilities [4, 0, 3, 1, 2]. The idea would be
        downbeat first, then start of the group of 3, then upbeat to downbeat, and then the fourth eighth note because
        it's the upbeat to that upbeat, and because he would say the eighth note right after the downbeat should be the
        most dispensable. However, another way of looking at it would be to say that once we get to [4, _, 3, _, 2],
        the next most indispensable beat should be the second eighth note, since it is the pickup to the second most
        indispensable beat! This would yield indispensabilities [4, 1, 3, 0, 2], which also makes sense. I've chosen
        to make this latter approach the default; I think it generally sounds more correct.
    :return: a (perhaps still nested) list of beat groups with the outer layer unraveled so that it's a layer less deep
    """
    beat_groups = deepcopy(beat_groups)
    out = []
    # first big beats
    for sub_group in beat_groups:
        out.append(sub_group.pop(0))

    if upbeats_before_group_length:
        # then the pickups to those beats
        for sub_group in beat_groups:
            if len(sub_group) > 0:
                out.append(sub_group.pop(0))

    # then by the longest chain, and secondarily by order (big beat indispensability)
    while True:
        max_subgroup_length = max(len(sub_group) for sub_group in beat_groups)
        if max_subgroup_length == 0:
            break
        else:
            for sub_group in beat_groups:
                if len(sub_group) == max_subgroup_length:
                    out.append(sub_group.pop(0))
                    break
    return out


def _return_first_from_nested_list(l):
    """
    Returns the first (unraveled) element of a nested list / tuple

    :param l: the nested list / tuple
    """
    if hasattr(l, "__len__") and not isinstance(l, str):
        return _return_first_from_nested_list(l[0])
    else:
        return l


class MetricStructure:

    """
    A highly flexible representation of a metric hierarchy, capable of describing both additive, multiplicative, and
    hybrid additive/multiplicative meters. Each MetricStructure describes a single layer of a metric grouping, and
    more complex hierarchies can be created by nesting metric structures inside of one another. For instance, a
    2 + 3 + 2 additive meter is simply constructed with ``MetricStructure(2, 3, 2)``. If we want each of the eight
    pulses in this meter to be subdivided in three, we could accomplish this by nesting metric strucures like this:
    ``MetricStructure(MetricStructure(3, 3), MetricStructure(3, 3, 3), MetricStructure(3, 3))``. Of course, this is
    quite a cumbersome expression, so it is usually much easier and more intuitive to use the :func:`from_string` class
    method: ``MetricStructure.from_string("(2+3+2)*3")``.

    Note that instances of MetricStructure do not contain any information as to the speed of fastest subdivision; they
    simply describe how subdivisions come together to form beats, how beats come together to form meters, etc. A
    MetricStructure can be asked to calculate an array of indispensibility values (following the theories of Clarence
    Barlow), or an array of beat depths, showing how nested each pulse is within the underlying meter (i.e. the degree
    to which it is on or off the beat, and at what layer of structure).

    :param groups: list of additively combined groups. If all integers, then this is like a simple additive meter
        without considering subdivisions. For instance, (2, 4, 3) is like the time signature (2+4+3)/8. However,
        any component of this structure can instead be itself a MetricStructure, allowing for nesting. Nested
        structures can also be created by having one of the groups be a tuple, or tuple of tuples, etc.
    :param break_up_large_numbers: if True, groups with number greater than 3 are broken up into a sum of 2's
        followed by one 3 if odd. This is the Barlow approach.
    """

    def __init__(self, *groups: Sequence[Union[int, Sequence, 'MetricStructure']],
                 break_up_large_numbers: bool = False):
        if not all(isinstance(x, (int, list, tuple, MetricStructure)) for x in groups):
            raise ValueError("Groups must either be integers, list/tuples or MetricStructures themselves")

        self.groups = [MetricStructure(*x) if isinstance(x, (tuple, list)) else x for x in groups]

        if break_up_large_numbers:
            self._break_up_large_numbers()

        self._remove_redundant_nesting()

    @classmethod
    def from_string(cls, input_string: str, break_up_large_numbers: bool = False) -> 'MetricStructure':
        """
        Creates a MetricStructure from an appropriately formatted input string. This is the simplest way of creating
        complex nested structures. For example, "3 * 2 + 5 + (2 + 3)" renders to
        `MetricStructure(MetricStructure(2, 2, 2), 5, MetricStructure(2, 3))`.

        :param input_string: input string consisting of integers, plus signs, multiplication signs, and parentheses
        :param break_up_large_numbers: see :class:`MetricStructure`
        """
        return MeterArithmeticGroup.parse(input_string).to_metric_structure(break_up_large_numbers)

    def _break_up_large_numbers(self):
        for i, group in enumerate(self.groups):
            if isinstance(group, int):
                if group > 3:
                    self.groups[i] = MetricStructure(*_decompose_to_twos_and_threes(group))
            else:
                self.groups[i]._break_up_large_numbers()
        return self

    def _remove_redundant_nesting(self):
        """
        Since MetricStructure(MetricStructure(*)) = MetricStructure(*), this method removes those unnecessary nestings.
        """
        if len(self.groups) == 1 and isinstance(self.groups[0], MetricStructure):
            self.groups = self.groups[0].groups
            self._remove_redundant_nesting()
        else:
            for i, group in enumerate(self.groups):
                if isinstance(group, MetricStructure):
                    group._remove_redundant_nesting()
                    if len(group.groups) == 1 and isinstance(group.groups[0], int):
                        self.groups[i] = group.groups[0]
        return self

    @staticmethod
    def _count_nested_list(l):
        return sum(MetricStructure._count_nested_list(x) if hasattr(x, "__len__") else 1 for x in l)

    @staticmethod
    def _increment_nested_list(l, increment):
        for i, element in enumerate(l):
            if isinstance(element, list):
                MetricStructure._increment_nested_list(element, increment)
            else:
                l[i] += increment
        return l

    def _get_nested_beat_groups(self):
        beat_groups = []
        beat = 0
        for group in reversed(self.groups):
            beat_group = list(range(group)) if isinstance(group, int) else group._get_nested_beat_groups()
            MetricStructure._increment_nested_list(beat_group, beat)
            beat += MetricStructure._count_nested_list(beat_group)
            beat_groups.append(beat_group)
        return beat_groups

    def _get_backward_beat_priorities(self, upbeats_before_group_length=True):
        # If some branches of the beat priorities tree don't go as far as others, we should embed
        # them further so that every beat is at the same _depth within the tree
        nested_beat_groups = _normalize_depth(self._get_nested_beat_groups())

        while _depth(nested_beat_groups) > 1:
            nested_beat_groups = flatten_beat_groups(nested_beat_groups, upbeats_before_group_length)

        return nested_beat_groups

    def get_beat_depths(self) -> List[int]:
        """
        Returns a list of integers representing how nested each beat/subdivision is within the metric structure.
        For example, `MetricStructure(MetricStructure(2, 2, 2), 5, MetricStructure(2, 3))` will give us beat depths
        `[0, 3, 2, 3, 2, 3, 1, 3, 3, 3, 3, 1, 3, 2, 3, 3]`. Notice that the first beat has depth zero, and the start
        of each of the three main groups --- (2, 2, 2), 5, and (3, 2) --- has depth 1.
        """
        # If some branches of the beat priorities tree don't go as far as others, we should embed
        # them further so that every beat is at the same _depth within the tree
        nested_beat_groups = _normalize_depth(self._get_nested_beat_groups())
        if len(nested_beat_groups) == 1 and hasattr(nested_beat_groups[0], "__len__"):
            # when it's just a single layer, for some reason it's getting wrapped twice, leading to erroneous values
            nested_beat_groups = nested_beat_groups[0]
        beat_depths = [0] + [None] * (MetricStructure._count_nested_list(nested_beat_groups) - 1)
        current_depth = 1

        while _depth(nested_beat_groups) > 1:
            for group in nested_beat_groups:
                backward_beat_num = _return_first_from_nested_list(group)
                if beat_depths[-backward_beat_num] is None:
                    beat_depths[-backward_beat_num] = current_depth

            current_depth += 1

            nested_beat_groups = flatten_beat_groups(nested_beat_groups, True)

        for group in nested_beat_groups:
            backward_beat_num = _return_first_from_nested_list(group)
            if beat_depths[-backward_beat_num] is None:
                beat_depths[-backward_beat_num] = current_depth

        return beat_depths

    def get_indispensability_array(self, upbeats_before_group_length: bool = True,
                                   normalize: bool = False) -> List[INT_OR_FLOAT]:
        """
        Resolve the nested structure to a single one-dimensional indispensability array. See Barlow's
        "On Musiquantics" (http://clarlow.org/wp-content/uploads/2016/10/On-MusiquanticsA4.pdf) for more detail.

        :param upbeats_before_group_length: see description in :func:`flatten_beat_groups` above. Affects the result
            when there are groups of uneven length at some level of metric structure. To achieve the standard
            Barlowian result, set this to False. I think it works better as True, though.
        :param normalize: if True, indispensabilities range from 0 to 1. If false, they count up from 0.
        :return: an indispensability array
        """
        backward_beat_priorities = list(self._get_backward_beat_priorities(upbeats_before_group_length))
        length = len(backward_beat_priorities)
        backward_indispensability_array = [length - 1 - backward_beat_priorities.index(i) for i in range(length)]
        indispensability_array = _rotate_list(backward_indispensability_array, 1)
        indispensability_array.reverse()
        if normalize:
            max_val = max(indispensability_array)
            return [float(x) / max_val for x in indispensability_array]
        else:
            return indispensability_array

    def num_pulses(self) -> int:
        """The total number of pulses (smallest subdivisions) in this MetricStructure"""
        return sum(x.num_pulses() if isinstance(x, MetricStructure) else x for x in self.groups)

    def extend(self, other_metric_structure: 'MetricStructure', in_place: bool = True) -> 'MetricStructure':
        """
        Extends this MetricStructure by appending all of the groups of other_metric_structure. For example:
        `MetricStructure(3, 3).extend(MetricStructure(2, 2))` results in `MetricStructure(3, 3, 2, 2)`.

        :param other_metric_structure: another MetricStructure
        :param in_place: if True, alters this object; if false returns an extended copy.
        """
        if in_place:
            self.groups.extend(other_metric_structure.groups)
            return self._remove_redundant_nesting()
        else:
            return MetricStructure(*self.groups, *other_metric_structure.groups)

    def append(self, other_metric_structure: 'MetricStructure', in_place: bool = True) -> 'MetricStructure':
        """
        Adds a new group to this MetricStructure consisting of other_metric_structure. For example,
        `MetricStructure(3, 3).append(MetricStructure(2, 2))` results in `MetricStructure(3, 3, MetricStructure(2, 2))`.

        :param other_metric_structure: another MetricStructure
        :param in_place: if True, alters this object; if false returns an extended copy.
        """
        if in_place:
            self.groups.append(other_metric_structure)
            return self._remove_redundant_nesting()
        else:
            return MetricStructure(*self.groups, other_metric_structure)

    def join(self, other_metric_structure) -> 'MetricStructure':
        """
        Creates a new MetricStructure with two groups: this MetricStructure and other_metric_structure. For example,
        `MetricStructure(3, 3).join(MetricStructure(2, 2))` results in
        `MetricStructure(MetricStructure(3, 3), MetricStructure(2, 2))`.

        :param other_metric_structure: another MetricStructure
        """
        return MetricStructure(self, other_metric_structure)

    def __add__(self, other):
        return self.join(other)

    def __mul__(self, other):
        if isinstance(other, int):
            return self * MetricStructure(other)
        else:
            return MetricStructure(*(group * other for group in self.groups))

    def __rmul__(self, other):
        if other == 1:
            return self
        return MetricStructure(*([self] * other))

    def __radd__(self, other):
        if other == 0:
            # This allows the "sum" command in __mul__ above to work
            return self
        elif isinstance(other, int):
            return MetricStructure(other) + self
        else:
            return other + self

    def __repr__(self):
        return "MetricStructure({})".format(", ".join(str(x) for x in self.groups))
