from scamp import *
import random
s = Session()

maxinst = s.new_osc_part("maxinst", 9000)

while True:
    maxinst.play_note(
        [random.uniform(60, 80), random.uniform(60, 80)],
        [0.2, 1.0],
        5.0,
        "param_overdrive:[0, 0.8, 0]",
        blocking=False
    )
    wait(random.uniform(0, 5))
        