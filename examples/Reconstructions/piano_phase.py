from scamp import *

session = Session()

piano1 = session.add_midi_part("Piano 1", (0, 0))
piano2 = session.add_midi_part("Piano 2", (0, 0))

pitches = [64, 66, 71, 73, 74, 66, 64, 73, 71, 66, 74, 73]


def piano_part(which_piano):
    while True:
        for pitch in pitches:
            which_piano.play_note(pitch, 1.0, 0.25)


clock1 = session.fork(piano_part, extra_args=(piano1, ))
clock1.tempo = 100
clock2 = session.fork(piano_part, extra_args=(piano2, ))
clock2.tempo = 98

session.start_recording(clock=clock1)
session.wait(30)

performance = session.stop_recording()
performance.to_score(QuantizationScheme.from_time_signature("3/4", 16)).show()
