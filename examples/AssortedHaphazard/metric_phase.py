from scamp import *

s = Session(tempo=120)

piano = s.new_part("piano")

def metro():
    while True:
        piano.play_note(90, 1.0, 1, "staccato")
        piano.play_note(85, 1.0, 1, "staccato")
        piano.play_note(85, 1.0, 1, "staccato")

def chromatic_accel():
    set_rate_target(2, Moment.after_beats(8), align_to=Moment.after_time(6))
    for p in range(48, 80):
        piano.play_note(p, 1, 0.25)
    print(current_clock().beat(), current_clock().time())
    for _ in range(12):
        piano.play_note(80, 1, 0.5)
        piano.play_note(75, 1, 0.5)
    set_rate_target(1, Moment.after_beats(8), align_to=Moment.after_time(6))
    for p in range(80, 48, -1):
        piano.play_note(p, 1, 0.25)
    for _ in range(6):
        piano.play_note(48, 1, 0.5)
        piano.play_note(43, 1, 0.5)
    set_rate_targets([3, 0.5, 2, 1], [Moment.after_beats(8), Moment.after_beats(15), Moment.after_beats(18), Moment.after_beats(21)], align_to=MetricPhaseTarget(0, 3))
    print(current_clock().beat())
    for _ in range(7):
        for i in range(12):
            piano.play_note(60 + i, 1, 0.25)
    print(current_clock().beat())
    for _ in range(10):
        piano.play_note(72, 1, 0.5)

fork(chromatic_accel)
metro()
wait_for_children_to_finish()