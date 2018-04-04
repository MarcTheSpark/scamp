import time
from sortedcontainers import SortedListWithKey
from collections import namedtuple
import threading

WakeUpCall = namedtuple("WakeUpCall", "t clock")


class Clock:

    def __init__(self, name=None, parent=None):
        """
        Recursively nestable clock class. Clocks can fork child-clocks, which can in turn fork their own child-clock.
        Only the master clock calls sleep; child-clocks instead register WakeUpCalls with their parents, who
        register wake-up calls with their parents all the way up to the master clock.
        :param name (optional): can be useful for keeping track in confusing multi-threaded situations
        :param parent: the parent clock for this clock; a value of None indicates the master clock
        """
        self.name = name
        self.parent = parent
        self._children = []

        # queue of WakeUpCalls for child clocks
        self._queue = SortedListWithKey(key=lambda x: x.t)
        # how long have I been around, in seconds since I was created
        self._t = 0

        # how long had my parent been around when I was created
        self.parent_offset = self.parent.time() if self.parent is not None else 0
        # will use these if not master clock
        self._ready_and_waiting = False
        self._wait_event = threading.Event()

    @property
    def master(self):
        return self if self.is_master() else self.parent.master()

    def is_master(self):
        return self.parent is None

    def time(self):
        return self._t

    @property
    def master_offset(self):
        if self.parent is None:
            return 0
        else:
            return self.parent_offset + self.parent.master_offset

    def time_in_parent(self):
        return self.time() + self.parent_offset

    def time_in_master(self):
        return self.time() + self.master_offset

    def fork(self, process_function, name=""):
        child = Clock(name, parent=self)
        self._children.append(child)

        def _process():
            process_function(child)
            self._children.remove(child)

        threading.Thread(target=_process, daemon=True).start()
        return child

    def wait_in_parent(self, dt):
        if self.is_master():
            # no parent, so this is the master thread that actually sleeps
            time.sleep(dt)
        else:
            self.parent._queue.add(WakeUpCall(self.time_in_parent() + dt, self))
            self._ready_and_waiting = True
            self._wait_event.wait()
            self._wait_event.clear()
            self._t += dt

    def wait_absolute(self, dt):
        # wait for any and all children to schedule their next wake up call and call wait()
        while not all(child._ready_and_waiting for child in self._children):
            pass

        end_time = self.time() + dt

        # while there are wakeup calls left to do amongst the children, and those wake up calls
        # would take place before we're done waiting here on the master clock
        while len(self._queue) > 0 and self._queue[0].t < end_time:
            # find the next wake up call
            next_wake_up_call = self._queue.pop(0)
            time_till_wake = next_wake_up_call.t - self._t
            self.wait_in_parent(time_till_wake)
            self._t += time_till_wake

            next_wake_up_call.clock._ready_and_waiting = False
            next_wake_up_call.clock._wait_event.set()

            while next_wake_up_call.clock in self._children and not next_wake_up_call.clock._ready_and_waiting:
                # wait for the child clock that we woke up to finish processing, or to finish altogether
                pass

        # if we exit the while loop, that means that there is no one in the queue (meaning no children),
        # or the first wake up call is scheduled for after this wait is to end. So we can safely wait.

        self.wait_in_parent(end_time - self._t)
        self._t = end_time

    def wait_for_children_to_finish(self):
        # wait for any and all children to schedule their next wake up call and call wait()
        while not all(child._ready_and_waiting for child in self._children):
            pass

        # while there are wakeup calls left to do amongst the children, and those wake up calls
        # would take place before we're done waiting here on the master clock
        while len(self._queue) > 0:
            # find the next wake up call
            next_wake_up_call = self._queue.pop(0)
            time_till_wake = next_wake_up_call.t - self._t
            self.wait_in_parent(time_till_wake)
            self._t += time_till_wake

            next_wake_up_call.clock._ready_and_waiting = False
            next_wake_up_call.clock._wait_event.set()

            while next_wake_up_call.clock in self._children and not next_wake_up_call.clock._ready_and_waiting:
                # wait for the child clock that we woke up to finish processing, or to finish altogether
                pass

    def __repr__(self):
        child_list = "" if len(self._children) == 0 else ", ".join(str(child) for child in self._children)
        return ("Clock('{}')".format(self.name) if self.name is not None else "Clock") + "[" + child_list + "]"


# # DEMO OF A MULTI-GENERATIONAL CLOCK FAMILY :-)
#
# master = Clock("master")
#
#
# def infinite_grandchild_process(clock):
#     while True:
#         clock.wait_absolute(0.5)
#         print("Grandkid! I've been around for {}s, and my grandpa for {}s".format(
#             clock.time(), clock.time_in_master())
#         )
#
#
# def finite_grandchild_process(clock):
#     for i in range(5):
#         print("HI", i+1)
#         clock.wait_absolute(0.2)
#
#
# def child_process(clock):
#     print("Hello - I'm a child!")
#     clock.wait_absolute(0.75)
#     clock.fork(finite_grandchild_process, "finite grandkid")
#     clock.wait_for_children_to_finish()
#     print("Just kidding around with you!")
#     clock.fork(infinite_grandchild_process, "infinite grandkid")
#     clock.wait_absolute(2.0)
#     print("Okay, child out!")
#
#
# print("I am the master")
# master.wait_absolute(1.0)
# master.fork(child_process, "child")
# master.wait_for_children_to_finish()
