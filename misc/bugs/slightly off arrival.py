"""
When this is recorded on the trumpet part, why is it that it dips below the final tempo?

Or is this even a bug?
"""

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
s.start_transcribing(clock=trumpet_clock)

while s.beats() < 12:
    trombone.play_note(60, 1, 1)

performance = s.stop_transcribing()
trumpet_clock.extract_absolute_tempo_envelope().show_plot()
performance.to_score("3/4").show_xml()