"""
Various and sundry utility functions used by SCAMP.
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

import os
import sys
import math
import itertools
import functools
from typing import Iterator, Type, Callable, List, Sequence, Tuple, Union, TypeVar
from expenvelope.json_serializer import SavesToJSON, SavesToJSONMeta


# -------------------------------------------- Utility Classes ----------------------------------------------

class NoteProperty:
    """
    Parent class for class for classes like :class:`~scamp.spelling.SpellingPolicy`, :class:`~scamp.text.StaffText` and
    :class:`~scamp.playback_adjustments.NotePlaybackAdjustment`, which can be passed to the properties argument of
    :func:`~scamp.instruments.ScampInstrument.play_note`.
    """
    pass

# ------------------------------------------- General Utilities ---------------------------------------------


def iterate_all_subclasses(type_name: Type) -> Iterator[Type]:
    """
    Iterates all generations of subclasses of a type
    """
    for subclass in type_name.__subclasses__():
        yield subclass
        for x in iterate_all_subclasses(subclass):
            yield x


def resolve_path(path: str) -> str:
    """
    Resolves the given path based on a variety of prefixes.

    :param path: A path, possibly prefixed by "/", "~/", or "%PKG/". A prefix of "/" will be interpreted as an absolute
        path, a prefix of "~/" will be interpreted as relative to the user's home directory, a prefix of "%PKG/"
        will be interpreted as relative to the package source directory, and an unprefixed path will be interpreted as
        relative to the current working directory.
    :return: the resolved path
    """
    if path.startswith("%PKG/"):
        # Relative to the package source directory
        return resolve_package_path(path[5:])
    elif path.startswith("/"):
        # Absolute soundfont path
        return path
    elif path.startswith("~/"):
        # Relative to user home directory
        return os.path.expanduser(path)
    else:
        # Unprefixed paths are relative to the working directory
        return os.path.join(os.getcwd(), path)


def resolve_package_path(path: str) -> str:
    if getattr(sys, 'frozen', False):
        # Python is running from a binary executable made by PyInstaller (the bootloader adds 'frozen' to sys)
        package_dir = os.path.dirname(sys.executable)
    else:
        # Otherwise, inspect the stack to find the module that made this call (or the root module if desired)
        package_dir = os.path.dirname(__file__)

    return os.path.join(package_dir, path)


def memoize(obj: Callable) -> Callable:
    """
    Decorator used for memoization (see https://en.wikipedia.org/wiki/Memoization)

    :param obj: the function to be wrapped in a memoizer
    :return: the wrapped, memoized function
    """
    cache = obj.cache = {}

    @functools.wraps(obj)
    def memoizer(*args, **kwargs):
        key = str(args) + str(kwargs)
        if key not in cache:
            cache[key] = obj(*args, **kwargs)
        return cache[key]

    return memoizer

# -------------------------------------------- Numerical Utilities -----------------------------------------------


def is_x_pow_of_y(x, y) -> bool:
    """
    Checks if x is an integer (including negative) power of y
    """
    a = math.log(x, y)
    if a == int(a):
        return True
    else:
        return False


def floor_x_to_pow_of_y(x, y):
    """
    Returns the integer power of y that is closest below x.
    """
    a = math.log(x, y)
    return y ** math.floor(a)


def ceil_x_to_pow_of_y(x, y):
    """
    Returns the integer power of y that is closest above x.
    """
    a = math.log(x, y)
    return y ** math.ceil(a)


def round_x_to_pow_of_y(x, y):
    """
    Returns the integer power of y that is closest to x (above or below).
    """
    a = math.log(x, y)
    return y ** (int(round(a)) if isinstance(y, int) else round(a))


def floor_to_multiple(x, factor):
    """
    Returns the multiple of factor that is closest below x.
    """
    return math.floor(x / factor) * factor


def ceil_to_multiple(x, factor):
    """
    Returns the multiple of factor that is closest above x.
    """
    return math.ceil(x / factor) * factor


def round_to_multiple(x, factor):
    """
    Returns the multiple of factor that is closest to x (above or below).
    """
    return round(x / factor) * factor


def is_multiple(x, y) -> bool:
    """
    Checks if x is a multiple of y.
    """
    return round_to_multiple(x, y) == x


def prime_factor(n: int) -> List[int]:
    """
    Returns a list of the prime factors of n.
    """
    i = 2
    primes = []
    while i * i <= n:
        while n % i == 0:
            n //= i
            primes.append(i)
        i += 1

    if n != 1:
        primes.append(n)

    return primes


def is_prime(a: int) -> bool:
    """
    Checks if a is a prime number.
    """
    return not (a < 2 or any(a % x == 0 for x in range(2, int(a ** 0.5) + 1)))

# ---------------------------------------------- List Utilities --------------------------------------------------


def make_flat_list(l: Sequence, indivisible: Union[Type, Tuple[Type]] = None) -> List:
    """
    Flattens a list, including ones containing multiple levels of nesting. Certain types can be excluded from expansion.

    :param l: a list or similar iterable
    :param indivisible: a type or tuple of types that should not be expanded out. E.g. a custom named tuple
    :return: a flattened version of the list
    """
    # indivisible_type is a type that we don't want to divide,
    new_list = list(l)

    i = 0
    while i < len(new_list):
        if hasattr(new_list[i], "__len__") and not isinstance(new_list[i], str) and \
                (indivisible is None or not isinstance(new_list[i], indivisible)):
            # if this list item can be expanded and it's not an indivisible type
            # then expand it and don't increment i
            new_list = new_list[:i] + list(new_list[i]) + new_list[i+1:]
        else:
            # otherwise increment i
            i += 1
    return new_list


def rotate(l: List, n: int) -> List:
    """
    Rotates a list such that it starts at the nth index and loops back to end at the (n-1)st

    :param l: the input list
    :param n: the new start index
    :return: the rotated list
    """
    return l[n:] + l[:n]


def sum_nested_list(l: List):
    """
    Sums up all of the values within a nested list.
    For instance :code:`sum_nested_list([6, [4, 2], [[-7]]])` will return 5

    :param l: the input list
    :return: sum of the l's nested values
    """
    if not hasattr(l, "__len__"):
        return l
    else:
        return sum(sum_nested_list(x) for x in l)


# ---------------------------------------------- String Utilities --------------------------------------------------


def get_average_square_correlation(test_string: str, template_string: str) -> float:
    """
    A test of the similarity of two strings via a (squared) cross-correlation of their characters.
    (Scaled down to compensate for the influence of string lengths.)

    :param test_string: string we are testing
    :param template_string: template string we are testing against
    """
    square_correlation_sum = 0
    test_length, template_length = len(test_string), len(template_string)
    for offset in range(-test_length + 1, template_length):
        test_string_segment = test_string[max(0, -offset): template_length - offset]
        template_string_segment = template_string[max(0, offset): max(0, offset) + len(test_string_segment)]
        correlation_score = sum(a == b for a, b in zip(test_string_segment, template_string_segment))
        square_correlation_sum += correlation_score ** 2
    return square_correlation_sum / (test_length + template_length)


# ------------------------------------ Indigestibility (a la Clarence Barlow) ------------------------------------
# All of these are needed for the indispensability stuff below


def indigestibility(n: int) -> float:
    """
    Returns the indigestibility of a number per the theories of Clarence Barlow.
    (See "On Musiquantics", http://clarlow.org/wp-content/uploads/2016/10/On-MusiquanticsA4.pdf)
    """
    assert isinstance(n, int) and n > 0
    if is_prime(n):
        return 2 * float((n-1)**2) / n
    else:
        total = 0
        for factor in prime_factor(n):
            total += indigestibility(factor)
        return total

# ------------------------------------- Indispensability (a la Clarence Barlow) -------------------------------------
# Indispensability is a way of assigning importance weightings to the pulses in a meter.
# I use this to improve the readability of the notation outputted. Read the code below at your own risk.


def _first_order_backward_beat_priorities(length):
    if hasattr(length, "__getitem__"):
        # a list or tuple or suchlike means we're dealing with additive meter
        # first reverse the group lengths, since we are doing everything backwards
        # lets take the example of length = (3, 5, 2)
        group_lengths = length[::-1]
        # now group_lengths = (2, 5, 3), since we calculate backwards

        # then construct beat groups according to their (backwards) position in the bar
        beat_groups = []
        beat = 0
        for group in group_lengths:
            beat_group = []
            for i in range(group):
                beat_group.append(beat)
                beat += 1
            beat_groups.append(beat_group)
        # in our example, this results in beat_groups = [[0, 1], [2, 3, 4, 5, 6], [7, 8, 9]]

        # OK, now we move the beats to a list in order from most indispensable to least
        order_of_indispensability = []

        # first take the first of each group (these are the beats)
        for beat_group in beat_groups:
            order_of_indispensability.append(beat_group.pop(0))
        # example: order_of_indispensibility = [0, 2, 7]

        # then gradually pick all the beats
        # beat groups that are the longest get whittled away first, until they
        # are no longer than any of the others. Always we go in order (backwards through the bar)
        # example: 3, 4, 5 get added next (remember, it's backwards, so we're adding the pulses
        #   leading up to the beat following the 5 group) once there are equally many pulses left
        #   in each beat, we add from each group in order (i.e. backwards order).
        largest_beat_group_length = max([len(x) for x in beat_groups])
        while largest_beat_group_length > 0:
            for beat_group in beat_groups:
                if len(beat_group) == largest_beat_group_length:
                    order_of_indispensability.append(beat_group.pop(0))
            largest_beat_group_length = max([len(x) for x in beat_groups])

        return order_of_indispensability
    else:
        return range(length)


def _get_backward_beat_priorities(*args):
    strata_backward_beat_priorities = []
    for meter_stratum in args:
        strata_backward_beat_priorities.append(_first_order_backward_beat_priorities(meter_stratum))
    # we reverse the strata here, because the position in the lowest level stratum matters the most
    strata_backward_beat_priorities.reverse()

    strata_lengths = [len(x) for x in strata_backward_beat_priorities]

    strata_multipliers = [1]
    last_multiplier = 1
    for l in strata_lengths[:-1]:
        last_multiplier *= l
        strata_multipliers.append(last_multiplier)

    overall_beat_priorities = []
    for combination in itertools.product(*strata_backward_beat_priorities):
        overall_beat_priorities.append(sum(p*q for p, q in zip(combination, strata_multipliers)))

    return overall_beat_priorities


def _get_indispensability_array(rhythmic_strata, normalize=False):
    backward_beat_priorities = _get_backward_beat_priorities(*rhythmic_strata)
    length = len(backward_beat_priorities)
    backward_indispensability_array = [length-1-backward_beat_priorities.index(i) for i in range(length)]
    indispensability_array = rotate(backward_indispensability_array, 1)
    indispensability_array.reverse()
    if normalize:
        max_val = max(indispensability_array)
        return [float(x)/max_val for x in indispensability_array]
    else:
        return indispensability_array


def _decompose_to_twos_and_threes(n):
    assert isinstance(n, int)
    out = []
    if n % 2 == 1:
        n -= 3
        out.append(3)

    while n > 0:
        n -= 2
        out.append(2)

    out.reverse()
    return out


def _standardize_strata(rhythmic_strata):
    strata = []
    for stratum in rhythmic_strata:
        assert isinstance(stratum, int) and stratum > 0
        if stratum > 2:
            strata.append(_decompose_to_twos_and_threes(stratum))
        else:
            strata.append(stratum)
    return strata


int_or_float = TypeVar("int_or_float", int, float)


def get_standard_indispensability_array(rhythmic_strata: Sequence, normalize: bool = False) -> List[int_or_float]:
    """
    Returns a list of the indispensabilities of different pulses in a meter defined by the rhythmic_strata.
    (See Barlow's "On Musiquantics", http://clarlow.org/wp-content/uploads/2016/10/On-MusiquanticsA4.pdf)

    :param rhythmic_strata: a tuple representing the rhythmic groupings from large scale to small scale. For instance,
        the sixteenth-note pulses in a measure of 9/8 would be represented by (3, 3, 2), since there are three beats of
        three eighth notes, each of which has two sixteenth notes.
    :param normalize: if True, scale all indispensabilities to the range 0 to 1
    :return: a list of integer indispensabilities, or float if normalize is set to true
    """
    return _get_indispensability_array(_standardize_strata(rhythmic_strata), normalize)
