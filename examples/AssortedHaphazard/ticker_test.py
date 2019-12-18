from clockblocks import Clock
import threading
import time

bob = Clock("master")


def wakethread():
    time.sleep(1.5)
    ticker_clock.tempo = 10


def ticker(clock):
    while True:
        print(clock.beat())
        clock.wait(0.1)


ticker_clock = bob.fork(ticker)
threading.Thread(target=wakethread).start()
bob.wait(1)
bob.wait(4)

print("done")
