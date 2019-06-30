from scamp import *

session = Session()

piano1 = session.new_part("Piano")
piano2 = session.new_part("Piano")

pitches = [64, 66, 71, 73, 74, 66, 64, 73, 71, 66, 74, 73]


def piano_part(which_piano):
    while True:
        for pitch in pitches:
            which_piano.play_note(pitch, 1.0, 0.25)


clock1 = session.fork(piano_part, extra_args=(piano1, ), initial_tempo=100)
clock2 = session.fork(piano_part, extra_args=(piano2, ), initial_tempo=98)

session.start_transcribing(clock=clock1)
session.wait(30)

performance = session.stop_transcribing()
performance.to_score(QuantizationScheme.from_time_signature("3/4", 16)).show()
