"""
SCAMP Example: Tempo Change

Same as Hello World example, but at half-tempo.
"""

# import the scamp namespace
from scamp import *
# construct a session object
s = Session()
# change to half of default tempo
s.tempo = 30

# add a new violin part to the session
violin = s.new_part("Violin")
# looping through the MIDI pitches
# of a C major arpeggio...
for pitch in [60, 64, 67, 72]:
    # play each pitch sequentially
    # with volume of 1 (full volume)
    # and duration of half a beat
    violin.play_note(pitch, 1, 0.5)