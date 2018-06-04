from playcorder import Playcorder
from playcorder.quantization import QuantizationScheme, MeasureQuantizationScheme
from random import random, seed

pc = Playcorder("default")
drum = pc.add_midi_part("metronome", (0, 116))
piano = pc.add_midi_part("piano", (0, 0))

recording = True

seed(4)


def piano_part():
    while recording:
        if random() < 0.5:
            piano.play_note(50 + random()*20, 0.5, random() * 1.5)
        else:
            piano.play_chord([50 + random()*20, 50 + random()*20], 0.5, random() * 1.5)


pc.fork(piano_part)

print("Making Recording...", end="")
pc.start_recording()
for _ in range(8):
    drum.play_note(80, 1, 1)

recording = False
performance = pc.stop_recording()
quantized_performance = performance.quantized(
    QuantizationScheme([MeasureQuantizationScheme.from_time_signature("4/4", max_divisor=5, max_indigestibility=3)])
)

quantized_performance.save_to_json("score_test.json")
print("Done")

while True:
    print("Replaying recording with quantization")
    pc.wait(1)
    quantized_performance.play(clock=pc.master_clock)

    print("Replaying recording without quantization")
    pc.wait(1)
    performance.play(clock=pc.master_clock)
