from scamp import *
import random

session = Session()

piano = session.new_part("piano")
piano.set_max_pitch_bend(20)

random.seed(1)

session.start_transcribing()

while session.time() < 12:
    gliss = Envelope.from_levels_and_durations(
        [random.random() * 20 + 60, random.random() * 20 + 60, random.random() * 20 + 60, random.random() * 20 + 60],
        [random.random()+0.5, random.random()+0.5, random.random()+0.5]
    )

    if random.random() < 0.5:
        piano.play_note(gliss, 1.0, random.random()*2 + 0.5)
    else:
        piano.play_chord([gliss, gliss+4], 1.0, random.random()*2 + 0.5)
    if random.random() < 0.5:
        session.wait(random.random() * 2)

# # Thia line causes the turn-around points of the glissandi to be rendered differently
# engraving_settings.glissandi.control_point_policy = "grace"
performance = session.stop_transcribing()

performance.quantize(QuantizationScheme.from_time_signature("5/4"))
performance.save_to_json(resolve_relative_path("SavedFiles/quantized_glisses.json"))

session.wait(2)
print("playing quantized")
performance.play(clock=session)

performance.to_score().show()
