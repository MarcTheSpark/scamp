import math


def _least_common_multiple(*args):
    # utility for getting the least_common_multiple of a list of numbers
    if len(args) == 0:
        return 1
    elif len(args) == 1:
        return args[0]
    elif len(args) == 2:
        return args[0] * args[1] // math.gcd(args[0], args[1])
    else:
        return _least_common_multiple(args[0], _least_common_multiple(*args[1:]))


def _is_power_of_two(x):
    # utility for checking if x is a power of two
    log2_x = math.log2(x)
    return log2_x == int(log2_x)


def _escape_split(s, delimiter):
    # Borrowed from https://stackoverflow.com/questions/18092354/python-split-string-without-splitting-escaped-character
    i, res, buf = 0, [], ''
    while True:
        j, e = s.find(delimiter, i), 0
        if j < 0:  # end reached
            return res + [buf + s[i:]]  # add remainder
        while j - e and s[j - e - 1] == '\\':
            e += 1  # number of escapes
        d = e // 2  # number of double escapes
        if e != d * 2:  # odd number of escapes
            buf += s[i:j - d - 1] + s[j]  # add the escaped char
            i = j + 1  # and skip it
            continue  # add more to buf
        res.append(buf + s[i:j - d])
        i, buf = j + len(delimiter), ''  # start after delim
