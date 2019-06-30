"""
SCAMP Example: Pitch Spelling

Demonstrates the ability to define note pitch spelling using the optional properties argument to "play_note". This can
be done by explicitly setting it, or by defining the key in which it resides.
"""

from scamp import *

s = Session()
piano = s.new_part("piano")

s.start_transcribing()

# play and spell a note with a flat no matter what
piano.play_note(63, 1.0, 1.0, "b")

# play and spell a note with a sharp no matter what
piano.play_note(63, 1.0, 1.0, "#")

# define some notes and durations
pitches = [65, 63, 61, 60]
durations = [1/3] * 3 + [1]

# play them and spell them in F minor
for pitch, dur in zip(pitches, durations):
    piano.play_note(pitch, 1.0, dur, "key: F minor")

# play them and spell them in B major
for pitch, dur in zip(pitches, durations):
    piano.play_note(pitch, 1.0, dur, "key: B major")

s.stop_transcribing().to_score().show()
