from scamp import *
from random import random, seed

session = Session()
drum = session.add_midi_part("metronome", (0, 116))
piano = session.add_midi_part("piano")

recording = True

seed(4)


def piano_part():
    while recording:
        if random() < 0.5:
            piano.play_note(50 + random()*20, 0.5, random() * 1.5)
        else:
            piano.play_chord([50 + random()*20, 50 + random()*20], 0.5, random() * 1.5)


session.fork(piano_part)

print("Making Recording...", end="")
session.start_recording()
for _ in range(8):
    drum.play_note(80, 1, 1)

recording = False
performance = session.stop_recording()
quantized_performance = performance.quantized(
    QuantizationScheme([MeasureQuantizationScheme.from_time_signature("4/4", max_divisor=5, max_indigestibility=3)])
)

print("Done")

while True:
    print("Replaying recording with quantization")
    session.wait(1)
    quantized_performance.play(clock=session)

    print("Replaying recording without quantization")
    session.wait(1)
    performance.play(clock=session)
