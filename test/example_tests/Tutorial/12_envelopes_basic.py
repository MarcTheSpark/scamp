"""
SCAMP Example: Envelopes (basic)

Create and plot two simple envelopes, one with evenly-spaced linear segments, and one with uneven, curved segments.
"""

from scamp import Envelope

e1 = Envelope.from_levels(
    [60, 72, 66, 70]
)

e2 = Envelope.from_levels_and_durations(
    [60, 72, 66, 70], [2, 1, 1],
    curve_shapes=[2, -2, -2]
)


def test_results():
    return [e1.json_dumps(), e2.json_dumps()]
