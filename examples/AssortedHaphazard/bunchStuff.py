from scamp import *
import random

s = Session()

# OSC to an external SuperCollider synth
sine_waves = s.new_osc_part("vibrato", 57120)
# basic soundfont-based rendering
piano = s.new_part("piano")
s.start_transcribing()  # start transcribing the music


def piano_part():
    while True:
        # play random notes 0.25 seconds long between middle C and A440 (microtonal)
        piano.play_note(random.uniform(60, 69), 1.0, 0.25, "staccato")


# start the piano as a parallel process
s.fork(piano_part)

while s.time() < 20:  # for twenty seconds...
    # play random sine-wave glissandi via the SuperCollider synth with varying vibrato
    sine_waves.play_note(
        [random.uniform(70, 96), random.uniform(70, 96)],  # pitch is a glissando between two values
        1.0, random.uniform(1, 4),  # volume is 1, duration is 1-4 seconds
        {"param_vibratoFreq": random.uniform(1, 20),
         "param_vibratoWidth": random.uniform(0.5, 3)}
    )

s.stop_transcribing().to_score(time_signature="3/4").show()
