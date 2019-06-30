"""
SCAMP Example: Multi Tempo

The trombone part plays quarter notes at the overall tempo of the session, which gradually accelerates from
the default starting tempo of 60 BPM to 100 BPM. Meanwhile, the trumpet part plays eighth notes and runs in a
child process that initially runs at the same speed as its parent (it inherits the parent's acceleration), but
then slows down to half speed within the accelerating parent process.

TODO: maybe make a multi-tempo example that doesn't have nested tempi first.
"""
from scamp import *
s = Session()

trumpet = s.new_part("trumpet")
trombone = s.new_part("trombone")


# When a function is forked, it is run on
# a child clock of the process forking it.
# This child clock can be passed as the
# first argument and then manipulated.
def trumpet_part(clock: Clock):
    # play eighth notes for three beats
    while s.beats() < 3:
        trumpet.play_note(67, 1, 0.5)

    # tell the clock for this child process
    # to slow down to 1/2 speed over six
    # beats in the parent process
    clock.set_rate_target(0.5, 6, duration_units="time")
    # keep playing eighth notes until 12
    # beats pass in the parent session

    while s.beats() < 12:
        trumpet.play_note(67, 1, 0.5)


# Have the session as a whole speed up to
# 100 BPM over the first nine beats
s.set_tempo_target(100, 9)
# Fork the trumpet part as a child process
# It will be influenced both by its own
# tempo and that of the session
s.fork(trumpet_part)
s.start_transcribing()
# Play quarter notes for 12 beats
while s.beats() < 12:
    trombone.play_note(60, 1, 1)

# Stop recording and show the result
performance = s.stop_transcribing()
performance.to_score("3/4").show_xml()
