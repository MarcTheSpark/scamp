from scamp import *

s = Session()

trumpet = s.new_part("trumpet")
trombone = s.new_part("trombone")


def trumpet_part(clock: Clock):
    while s.beats() < 3:
        trumpet.play_note(67, 1, 0.5)
    clock.set_rate_target(0.5, 6, duration_units="time")
    while s.beats() < 12:
        trumpet.play_note(67, 1, 0.5)


s.set_tempo_target(100, 9)
trumpet_clock = s.fork(trumpet_part)
trombone_based_performance = s.start_recording()
trumpet_based_performance = s.start_recording(clock=trumpet_clock)

while s.beats() < 12:
    trombone.play_note(60, 1, 1)

s.stop_recording(trombone_based_performance)
s.stop_recording(trumpet_based_performance)

trombone_based_performance.to_score("3/4", title="Trombone Clock").show_xml()
trumpet_based_performance.to_score("3/4", title="Trumpet Clock").show_xml()