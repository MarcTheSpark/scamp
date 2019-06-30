"""
SCAMP Example: Envelope Shorthand

Plays two glissandi by passing lists instead of envelopes to the pitch argument of play_note.
"""

from scamp import *

s = Session()
viola = s.new_part("viola")

s.start_transcribing()

# a list of values results in evenly spaced glissando
viola.play_note([60, 70, 55], 1.0, 4)

# a list of lists can give values, durations, and (optionally) curve shapes
# this results in segment durations of 2 and 1 and curve shapes of -2 and 0
viola.play_note([[60, 70, 55], [2, 1], [-2, 0]], 1.0, 4)

s.stop_transcribing().to_score().show()
