from playcorder import *
from playcorder.score import Score

pc = Playcorder("default")

piano = pc.add_midi_part("piany")
piano.set_max_pitch_bend(20)

pc.master_clock.tempo = 120

pc.start_recording()

#TODO: Why does this fail with not

import random

random.seed(0)

from playcorder.settings import engraving_settings

engraving_settings.glissandi.control_point_policy = "grace"
engraving_settings.glissandi.consider_non_extrema_control_points = False
engraving_settings.glissandi.include_end_grace_note = True

for _ in range(20):
    boops = random.randint(2, 7)
    pitches = [round(65 + 10 * random.random()) for _ in range(boops + 1)]
    length = boops * 0.25
    piano.play_note(pitches, 1.0, length)


recording = pc.stop_recording()
quantized_recording = recording.quantized()
quantized_recording.save_to_json("splittle.json")
import abjad

abjad.show(Score.from_quantized_performance(quantized_recording).to_abjad())