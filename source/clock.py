import time
from sortedcontainers import SortedListWithKey
from collections import namedtuple
import threading


WakeUpCall = namedtuple("WakeUpCall", "t clock")


class MasterClock:

    def __init__(self):
        self._t = 0
        self.queue = SortedListWithKey(key=lambda x: x.t)
        self.children = []

    def fork(self, process_function):
        child = Clock(self)
        self.children.append(child)

        def _process():
            process_function(child)
            self.children.remove(child)

        threading.Thread(target=_process, daemon=True).start()

    def wait(self, dt):
        # wait for all children to scheduled their next wake up time and call wait()
        while not all(child._ready_and_waiting for child in self.children):
            pass

        end_time = self._t + dt

        # while there are wakeup calls left to do amongst the children, and those wake up calls
        # would take place before we're done waiting here on the master clock
        while len(self.queue) > 0 and self.queue[0].t < end_time:
            # find the next wake up call
            next_wake_up_call = self.queue.pop(0)
            time_till_wake = next_wake_up_call.t - self._t
            time.sleep(time_till_wake)
            self._t += time_till_wake

            next_wake_up_call.clock._ready_and_waiting = False
            next_wake_up_call.clock._wait_event.set()
            while not next_wake_up_call.clock._ready_and_waiting:
                pass

        time.sleep(end_time - self._t)
        self._t = end_time

    def time(self):
        return self._t


class Clock:

    def __init__(self, master_clock):
        self._t = 0
        self.master = master_clock
        self._ready_and_waiting = False
        self._wait_event = threading.Event()

    def wait(self, dt):
        self.master.queue.add(WakeUpCall(self.master.time() + dt, self))
        self._ready_and_waiting = True
        self._wait_event.wait()
        self._wait_event.clear()
        self._t += dt

    def time(self):
        return self._t

# # Simple Clock Demo
#
# mc = MasterClock()
#
#
# def process2(clock):
#     while True:
#         print("C2 time = ", clock.time(), "MC time = ", clock.master.time())
#         clock.wait(1.0)
#
#
# def process3(clock):
#     while True:
#         print("C3 time = ", clock.time(), "MC time = ", clock.master.time())
#         clock.wait(2./3)
#
#
# mc.fork(process2)
# mc.fork(process3)
#
#
# while True:
#     print("MC time = ", mc.time())
#     mc.wait(2.0)
