from scamp import *

session = Session("default")

piano1 = session.add_midi_part("Piano 1", (0, 0))
piano2 = session.add_midi_part("Piano 2", (0, 0))

pitches = [64, 66, 71, 73, 74, 66, 64, 73, 71, 66, 74, 73]


def piano1_part():
    while True:
        for pitch in pitches:
            piano1.play_note(pitch, 1.0, 0.25)


def piano2_part():
    while True:
        for pitch in pitches:
            piano2.play_note(pitch, 1.0, 0.25)


clock1 = session.fork(piano1_part)
clock1.tempo = 100
clock2 = session.fork(piano2_part)
clock2.tempo = 98

session.start_recording(clock=clock1)
session.fast_forward_in_beats(30)
session.wait(30)

performance = session.stop_recording()
print("quantizing...")
quantized_performance = performance.quantize(QuantizationScheme.from_time_signature("3/4", 16))
print("converting to score...")
score = performance.to_score()
print(score)

print("show")
# score.print_music_xml()
print(score.to_music_xml())
# score.show_xml()
