"""
Bug: the inner fork, playing a long clarinet note outlasted the outer fork, and was leading to a hung note. Fixed
so that now the inner fork gets cut off with a warning.
"""

from scamp import *

s = Session()

clarinet = s.new_part("clarinet")


def outer_fork():
    # a forked note with blocking=False
    clarinet.play_note(67, [0.5, 1, 0], 3, blocking=False)

    # and a forked function playing some notes
    def inner_fork():
        for _ in range(8):
            clarinet.play_note(60, 0.7, 0.5)

    fork(inner_fork)
    # wait_for_children_to_finish()  # works with this
    wait(0.5)  # doesn't behave properly with this


fork(outer_fork)

wait_for_children_to_finish()
