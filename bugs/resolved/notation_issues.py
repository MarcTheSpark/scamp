"""
Bugs:
- Duplicate metronome marks at the start
- The looping tempo curve didn't materialize until *after* the loop point, so on beat 4 we got the old rate value
from the end of the loop.
"""

from scamp import *

s = Session()

flute = s.new_part("flute")

s.start_transcribing()

# looping tempo shapes now live on apply_tempo_envelope rather than set_tempo_targets(..., loop=True)
tempo_env = TempoEnvelope.from_levels_and_durations(
    (160, 160, 100, 100, 130, 130, 70, 70), (1, 0, 1, 0, 1, 0, 1))
apply_tempo_envelope(tempo_env, loop=True)

# s.fast_forward()
while get_beat() < 8:
    flute.play_note(int(70 + 10 * get_rate()), 0.8, 0.25, "staccato")

s.stop_transcribing().to_score().show()

