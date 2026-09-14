"""
SCAMP Example: Random Walk Fragments

Forks overlapping random-walk melodies into a single instrument, then renders the same performance
at several max_voices_per_staff settings to compare how the fragments get distributed across voices
and staves.
"""

from scamp import *
import random

random.seed(4)
s = Session()
s.tempo = 120
s.fast_forward()

piano = s.new_part("piano")


def voice_name_iter():
    i = 0
    while True:
        yield f'frag_{i}'
        i += 1


voice_namer = voice_name_iter()


def random_walk_fragment():
    # a melody that steps by a random interval each note, occasionally resting instead of playing
    pitch = random.randint(60, 80)
    fragment_length = random.uniform(2, 6)
    elapsed = 0
    voice_name = next(voice_namer)
    while elapsed < fragment_length:
        duration = random.choice([0.25, 0.5, 1.0, 1.5])
        if random.random() < 0.25:
            wait(duration)
        else:
            piano.play_note(pitch, 1.0, duration, {"voice": voice_name})
        pitch += random.choice([-3, -1, -2, 2, 4, 5])
        elapsed += duration


s.start_transcribing()
while s.beat < 60:
    fork(random_walk_fragment)
    wait(random.uniform(0.5, 8))
performance = s.stop_transcribing()

# render the same performance a few different ways
for max_voices in (1, 2, 4):
    engraving_settings.max_voices_per_staff = max_voices
    performance.to_score(title=f"max_voices_per_staff = {max_voices}").show()
