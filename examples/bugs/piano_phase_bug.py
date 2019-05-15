from scamp import *

session = Session()

piano1 = session.new_part("Piano")
piano2 = session.new_part("Piano 2")

pitches = [64, 66, 71, 73, 74, 66, 64, 73, 71, 66, 74, 73]


def piano_part(which_piano):
    while True:
        for pitch in pitches:
            which_piano.play_note(pitch, 1.0, 0.25)


# TODO: solve the bug that the clock has already called "wait" at tempo = 60 before its new tempo is set, and so waits too long. I think this is the same as the "midwait" bug
clock1 = session.fork(piano_part, extra_args=(piano1, ))
clock1.tempo = 100
clock2 = session.fork(piano_part, extra_args=(piano2, ))
clock2.tempo = 98

session.start_recording(clock=clock1)
session.wait(10)

performance = session.stop_recording()
print(performance)
performance.to_score(QuantizationScheme.from_time_signature("3/4", 16)).show()
