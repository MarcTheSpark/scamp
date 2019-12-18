from clockblocks import *


master = Clock("MASTER")
grandchild = None


def c():
    global grandchild
    print("child start")
    grandchild = fork(gc, name="GRANDCHILD")
    wait(8)
    print("child end", master.time())


def gc(clock):
    while True:
        print(clock.beat(), master.beat())
        wait(2)


child = master.fork(c, name="CHILD")


def test():
    global grandchild
    time.sleep(1.5)
    master.rouse_and_hold()
    grandchild.rouse_and_hold()
    grandchild.tempo = 10
    print(master._wait_keeper.being_held, grandchild._wait_keeper.being_held)
    grandchild.release_from_suspension()
    time.sleep(0.001)
    print(master._wait_keeper.being_held, grandchild._wait_keeper.being_held)
    master.release_from_suspension()
    time.sleep(0.001)
    print(master._wait_keeper.being_held, grandchild._wait_keeper.being_held)

# wait(1.5)
# master.rouse_and_hold()
# grandchild.rouse_and_hold()
# grandchild.tempo = 10
# grandchild.release_from_suspension()
# master.release_from_suspension()
threading.Thread(target=test).start()

# master.wait_forever()
master.wait_for_children_to_finish()
