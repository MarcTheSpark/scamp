import time
from sortedcontainers import SortedListWithKey
from collections import namedtuple
import threading


WakeUpCall = namedtuple("WakeUpCall", "t clock")


class MasterClock:

    def __init__(self):
        self.t = 0
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
        while not all(child.ready_and_waiting for child in self.children):
            pass

        end_time = self.t + dt

        # while there are wakeup calls left to do amongst the children, and those wake up calls
        # would take place before we're done waiting here on the master clock
        while len(self.queue) > 0 and self.queue[0].t < end_time:
            # find the next wake up call
            next_wake_up_call = self.queue.pop(0)
            time_till_wake = next_wake_up_call.t - self.t
            time.sleep(time_till_wake)
            self.t += time_till_wake

            next_wake_up_call.clock.ready_and_waiting = False
            next_wake_up_call.clock.wait_event.set()
            while not next_wake_up_call.clock.ready_and_waiting:
                pass

        time.sleep(end_time - self.t)
        self.t = end_time


class Clock:

    def __init__(self, master_clock):
        self.t = 0
        self.master = master_clock
        self.ready_and_waiting = False
        self.wait_event = threading.Event()

    def wait(self, dt):
        self.master.queue.add(WakeUpCall(self.master.t + dt, self))
        self.ready_and_waiting = True
        self.wait_event.wait()
        self.wait_event.clear()
        self.t += dt


# # Simple Clock Demo
#
# mc = MasterClock()
#
#
# def process2(clock):
#     while True:
#         print("C2 time = ", clock.t, "MC time = ", clock.master.t)
#         clock.wait(1.0)
#
#
# def process3(clock):
#     while True:
#         print("C3 time = ", clock.t, "MC time = ", clock.master.t)
#         clock.wait(2./3)
#
#
# mc.fork(process2)
# mc.fork(process3)
#
#
# while True:
#     print("MC time = ", mc.t)
#     mc.wait(2.0)
