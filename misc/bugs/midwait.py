from clockblocks import *


master = Clock("MASTER")


def c():
    print("child start")
    wait(2)
    print("child end")


child = master.fork(c)
master.wait(1)
child.tempo = 10
master.wait_for_children_to_finish()