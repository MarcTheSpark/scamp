import os
import sys
import inspect
import math
import itertools

__author__ = 'mpevans'


# determines if application is a script file or frozen exe
def get_relative_file_path(file_name, from_root_process=False):
    if getattr(sys, 'frozen', False):
        application_path = os.path.join(os.path.dirname(sys.executable), "..")
    else:
        frm = inspect.stack()[1] if not from_root_process else inspect.stack()[-1]
        mod = inspect.getmodule(frm[0])
        application_path = os.path.dirname(mod.__file__)

    return os.path.join(application_path, file_name)


# Numerical Stuff

def is_x_pow_of_y(x, y):
    a = math.log(x, y)
    if a == int(a):
        return True
    else:
        return False


def floor_x_to_pow_of_y(x, y):
    a = math.log(x, y)
    return y ** math.floor(a)


def ceil_x_to_pow_of_y(x, y):
    a = math.log(x, y)
    return y ** math.ceil(a)


def round_x_to_pow_of_y(x, y):
    a = math.log(x, y)
    return y ** (int(round(a)) if isinstance(y, int) else round(a))


def round_to_multiple(x, factor):
    return round(x/factor)*factor


def is_multiple(x, y):
    return round_to_multiple(x, y) == x


def prime_factor(n):
    assert isinstance(n, int)
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

# --------------------- list stuff ---------------------------


def make_flat_list(l, indivisible_type=None):
    # indivisible_type is a type that we don't want to divide,
    new_list = list(l)
    i = 0
    while i < len(new_list):
        if hasattr(new_list[i], "__len__"):
            if indivisible_type is None or not isinstance(new_list[i], indivisible_type):
                new_list = new_list[:i] + new_list[i] + new_list[i+1:]
        else:
            i += 1
    return new_list


def rotate(l, n):
    return l[n:] + l[:n]

# ---------------------------------------- Indigestibility ------------------------------------------


def is_prime(a):
    return not (a < 2 or any(a % x == 0 for x in range(2, int(a ** 0.5) + 1)))


def indigestibility(n):
    assert isinstance(n, int) and n > 0
    if is_prime(n):
        return 2 * float((n-1)**2) / n
    else:
        total = 0
        for factor in prime_factor(n):
            total += indigestibility(factor)
        return total

# ---------------------------------------------- Indispensability -----------------------------------------------


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


def get_indispensability_array(rhythmic_strata, normalize=False):
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


def decompose_to_twos_and_threes(n):
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


def standardize_strata(rhythmic_strata):
    strata = []
    for stratum in rhythmic_strata:
        assert isinstance(stratum, int) and stratum > 0
        if stratum > 2:
            strata.append(decompose_to_twos_and_threes(stratum))
        else:
            strata.append(stratum)
    return strata


def get_standard_indispensability_array(rhythmic_strata, normalize=False):
    return get_indispensability_array(standardize_strata(rhythmic_strata), normalize)