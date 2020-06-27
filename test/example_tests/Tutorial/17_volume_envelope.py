"""
SCAMP Example: Volume Envelope

Plots an envelope representing a forte-piano-crescendo dynamic, and then uses it to affect the dynamics of a note's
playback. This example shows that an Envelope can be passed to the volume argument of "play_note", just like it can
to the pitch argument. (The list short-hand also works, by the way.)
"""

from scamp import *

s = Session()
viola = s.new_part("viola")
s.fast_forward_in_beats(float("inf"))

fp_cresc = Envelope.from_levels_and_durations(
    [0.8, 0.3, 1],
    [0.07, 0.93],
    curve_shapes=[2, 4]
)

# play a note with the dynamic curve
viola.play_note(48, fp_cresc, 4)


def test_results():
    return [True]
