"""
SCAMP Example: OSC to SuperCollider

Plays back notes by sending OSC messages to the corresponding SuperCollider process.
Start SuperCollider and run the code blocks in osc_to_supercollider.scd before running this script.
"""

from scamp import *
import random

s = Session()

# on the other end, an OSC receiver is
# setup to play notes that take vibrato
# and OSC messages as well as the usual
vib = s.new_osc_part("vibrato", 57120)

s.start_recording()

# any property entries starting or ending
# with "param" will be treated as extra
# playback parameters
while s.beats() < 20:
    # glissando between three random values
    pitch_env = [random.randint(60, 82) for _ in range(3)]
    volume_env = random.choice([
        # percussive envelope
        Envelope.ar(0.1, 1.2),
        # fp crescendo envelope
        Envelope.from_levels_and_durations([1, 0.2, 1], [0.1, 1],
                                           curve_shapes=[-2, 3])
    ])
    vib_width_env = [random.uniform(0, 5) for _ in range(2)]
    vib_freq_env = [random.uniform(3, 13) for _ in range(2)]
    vib.play_note(
        pitch_env, volume_env, random.uniform(0.3, 3),
        {"vibWidth_param": vib_width_env,
         "vibFreq_param": vib_freq_env},
        blocking=False
    )
    wait(random.uniform(0.5, 3))

performance = s.stop_recording()
engraving_settings.max_voices_per_part = 1
performance.to_score().show()
