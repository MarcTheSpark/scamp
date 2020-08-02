from scamp import *
from random import random

s = Session()

maxinst = s.new_osc_part("maxinst", 9000)

while True:
    for p in range(65, 80):
        maxinst.play_note(p, [0.2, 1.0], 1.0, "param_overdrive:[0, 0.8, 0]")
        if random() < 0.5:
            wait(random())
        