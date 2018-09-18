from playcorder import *
from playcorder.quantization import QuantizationScheme
import random

pc = Playcorder("default")

piano = pc.add_midi_part("piano")
piano.set_max_pitch_bend(20)

random.seed(0)

pc.start_recording()

while pc.time() < 12:
    gliss = Envelope.from_levels_and_durations(
        [random.random() * 20 + 60, random.random() * 20 + 60, random.random() * 20 + 60, random.random() * 20 + 60],
        [random.random(), random.random(), random.random()]
    )
    if random.random() < 0.5:
        piano.play_note(gliss, 1.0, random.random()*2 + 0.2)
    else:
        piano.play_chord([gliss, gliss+4], 1.0, random.random()*2 + 0.2)
    if random.random() < 0.5:
        pc.wait(random.random()*2)


performance = pc.stop_recording()

performance.quantize(QuantizationScheme.from_time_signature("5/4"))
performance.save_to_json("quantized_glisses.json")

pc.wait(2)
print("playing quantized")
performance.play(clock=pc.master_clock)
