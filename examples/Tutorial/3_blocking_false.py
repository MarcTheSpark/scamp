"""
SCAMP Example: Blocking False

Demonstrating the ability to have non-blocking calls to play_note. This plays two notes that each last
for two beats, but overlapping by one beat.
"""

# import the scamp namespace
from scamp import *
# construct a session object
s = Session()
# add a new violin part to the session
violin = s.new_part("Violin")

# start playing a 2-beat C, but return immediately
violin.play_note(60, 1, 2, blocking=False)
# wait for only one beat
wait(1)
# start playing a 2-beat E, blocking this time
violin.play_note(64, 1, 2)
