import time
from sortedcontainers import SortedListWithKey
from collections import namedtuple
import threading
from multiprocessing.pool import ThreadPool
import logging
from .parameter_curve import ParameterCurve, ParameterCurveSegment


def _sleep_precisely_until(stop_time):
    time_remaining = stop_time - time.time()
    if time_remaining <= 0:
        return
    elif time_remaining < 0.0005:
        # when there's not much left, just burn cpu cycles and hit it exactly
        while time.time() < stop_time:
            pass
    else:
        time.sleep(time_remaining / 2)
        _sleep_precisely_until(stop_time)


def sleep_precisely(secs):
    _sleep_precisely_until(time.time() + secs)


WakeUpCall = namedtuple("WakeUpCall", "t clock")


class Clock:

    def __init__(self, name=None, parent=None, initial_rate=1.0, pool_size=200, timing_policy="relative"):
        """
        Recursively nestable clock class. Clocks can fork child-clocks, which can in turn fork their own child-clock.
        Only the master clock calls sleep; child-clocks instead register WakeUpCalls with their parents, who
        register wake-up calls with their parents all the way up to the master clock.
        :param name (optional): can be useful for keeping track in confusing multi-threaded situations
        :param parent: the parent clock for this clock; a value of None indicates the master clock
        :param pool_size: the size of the process pool for unsynchronized forks, which are used for playing notes. Only
        has an effect if this is the master clock.
        :param timing_policy: either "relative" or "absolute". "relative" attempts to keeps each wait call as faithful
        as possible to what it should be. This can result in the clock getting behind real time, since if heavy
        processing causes us to get behind on one note we never catch up. "absolute" tries instead to stay faithful to
        the time since the clock began. If one wait is too long due to heavy processing, later delays will be shorter
        to try to catch up. This can result in inaccuracies in relative timing. In general, use "relative" unless you
        are trying to synchronize the output with an external process.
        """
        self.name = name
        self.parent = parent
        self._children = []

        # queue of WakeUpCalls for child clocks
        self._queue = SortedListWithKey(key=lambda x: x.t)
        # how long have I been around, in seconds since I was created
        self._tempo_curve = TempoCurve(initial_rate)

        # how long had my parent been around when I was created
        self.parent_offset = self.parent.beats() if self.parent is not None else 0
        # will use these if not master clock
        self._ready_and_waiting = False
        self._wait_event = threading.Event()

        if self.is_master():
            # The thread pool runs on the master clock
            self._pool = ThreadPool(processes=pool_size)
            # Used to keep track of if we're using all the threads in the pool
            # if so, we just start a thread and throw a warning to increase pool size
            self._pool_semaphore = threading.BoundedSemaphore(pool_size)
            threading.current_thread().__clock__ = self
        else:
            # All other clocks just use self.master._pool
            self._pool = None
            self._pool_semaphore = None

        self._last_sleep_time = self._start_time = time.time()
        # precise timing uses a while loop when we get close to the wake-up time
        # it burns more CPU to do this, but the timing is more accurate
        self.use_precise_timing = True
        self._log_processing_time = False

        assert timing_policy in ("relative", "absolute")
        self.timing_policy = timing_policy

    @property
    def master(self):
        return self if self.is_master() else self.parent.master

    def is_master(self):
        return self.parent is None

    def time(self):
        return self._tempo_curve.time()

    def beats(self):
        return self._tempo_curve.beats()

    def time_in_master(self):
        return self.master.time()

    @property
    def beat_length(self):
        return self._tempo_curve.beat_length

    @beat_length.setter
    def beat_length(self, b):
        self._tempo_curve.beat_length = b

    @property
    def rate(self):
        return self._tempo_curve.rate

    @rate.setter
    def rate(self, r):
        self._tempo_curve.rate = r

    @property
    def tempo(self):
        return self._tempo_curve.tempo

    @tempo.setter
    def tempo(self, t):
        self._tempo_curve.tempo = t

    def set_beat_length_target(self, beat_length_target, duration, curve_shape=0,
                               duration_units="beats", truncate=True):
        self._tempo_curve.set_beat_length_target(beat_length_target, duration, curve_shape, duration_units, truncate)

    def set_rate_target(self, rate_target, duration, curve_shape=0, duration_units="beats", truncate=True):
        self._tempo_curve.set_rate_target(rate_target, duration, curve_shape, duration_units, truncate)

    def set_tempo_target(self, tempo_target, duration, curve_shape=0, duration_units="beats", truncate=True):
        self._tempo_curve.set_tempo_target(tempo_target, duration, curve_shape, duration_units, truncate)

    def absolute_rate(self):
        absolute_rate = self.rate if self.parent is None else (self.rate * self.parent.rate)
        return absolute_rate

    def _run_in_pool(self, target, args, kwargs):
        if self.master._pool_semaphore.acquire(blocking=False):
            semaphore = self.master._pool_semaphore
            self.master._pool.apply_async(target, args=args, kwds=kwargs, callback=lambda _: semaphore.release())
        else:
            logging.warning("Ran out of threads in the master clock's ThreadPool; small thread creation delays may "
                            "result. You can increase the number of threads in the pool to avoid this.")
            threading.Thread(target=target, args=args, kwargs=kwargs, daemon=True).start()

    def fork(self, process_function, name="", initial_rate=1.0, extra_args=(), kwargs=None):
        kwargs = {} if kwargs is None else kwargs

        child = Clock(name, parent=self, initial_rate=initial_rate)
        self._children.append(child)

        def _process(*args, **kwds):
            try:
                threading.current_thread().__clock__ = child
                process_function(child, *args, **kwds)
                self._children.remove(child)
            except Exception as e:
                logging.exception(e)
        self._run_in_pool(_process, extra_args, kwargs)

        return child

    def fork_unsynchronized(self, process_function, args=(), kwargs=None):
        kwargs = {} if kwargs is None else kwargs

        def _process(*args, **kwargs):
            try:
                process_function(*args, **kwargs)
            except Exception as e:
                logging.exception(e)

        self._run_in_pool(_process, args, kwargs)

    def wait_in_parent(self, dt):
        if self._log_processing_time:
            logging.info("Clock {} processed for {} secs.".format(self.name if self.name is not None else "<unnamed>",
                                                                  time.time() - self._last_sleep_time))
        if dt == 0:
            return
        if self.is_master():
            # no parent, so this is the master thread that actually sleeps
            # we want to stop sleeping dt after we last finished sleeping, not including the processing that happened
            # after we finished sleeping. So we calculate the time to finish sleeping based on that
            stop_sleeping_time = self._start_time + self.time() + dt if self.timing_policy == "absolute" \
                else self._last_sleep_time + dt
            # in case processing took so long that we are already past the time we were supposed to stop sleeping,
            # we throw a warning that we're getting behind and don't try to sleep at all
            if stop_sleeping_time < time.time() - 0.01:
                # if we're more than 10 ms behind, throw a warning: this starts to get noticeable
                logging.warning("Clock is running noticeably behind real time; probably processing is too heavy.")
            else:
                if self.use_precise_timing:
                    _sleep_precisely_until(stop_sleeping_time)
                else:
                    time.sleep(stop_sleeping_time - time.time())
        else:
            self.parent._queue.add(WakeUpCall(self.parent.beats() + dt, self))
            self._ready_and_waiting = True
            self._wait_event.wait()
            self._wait_event.clear()
        self._last_sleep_time = time.time()

    def wait(self, beats):
        # wait for any and all children to schedule their next wake up call and call wait()
        while not all(child._ready_and_waiting for child in self._children):
            # note that sleeping a tiny amount is better than a straight while loop,
            # which slows down the other threads with its greediness
            time.sleep(0.000001)

        end_time = self.beats() + beats

        # while there are wakeup calls left to do amongst the children, and those wake up calls
        # would take place before we're done waiting here on the master clock
        while len(self._queue) > 0 and self._queue[0].t < end_time:
            # find the next wake up call
            next_wake_up_call = self._queue.pop(0)
            wake_up_beat = next_wake_up_call.t
            beats_till_wake = wake_up_beat - self.beats()
            self.wait_in_parent(self._tempo_curve.get_wait_time(beats_till_wake))
            self.advance_tempo_map_to_beat(wake_up_beat)
            next_wake_up_call.clock._ready_and_waiting = False
            next_wake_up_call.clock._wait_event.set()

            # wait for the child clock that we woke up to finish processing, or to finish altogether
            while next_wake_up_call.clock in self._children and not next_wake_up_call.clock._ready_and_waiting:
                # note that sleeping a tiny amount is better than a straight while loop,
                # which slows down the other threads with its greediness
                time.sleep(0.000001)

        # if we exit the while loop, that means that there is no one in the queue (meaning no children),
        # or the first wake up call is scheduled for after this wait is to end. So we can safely wait.
        self.wait_in_parent(self._tempo_curve.get_wait_time(end_time - self.beats()))
        self._tempo_curve.advance(end_time - self.beats())

        # when we're done waiting, some of the children may be behind, having not woken up yet
        # we advance them forward to the current time
        for child in self._children:
            if child.time() < self.beats():
                child._tempo_curve.advance_time(self.beats() - child.time())

    def advance_tempo_map_to_beat(self, beat):
        self._tempo_curve.advance(beat - self.beats())

    def sleep(self, beats):
        # alias to wait
        self.wait(beats)

    def wait_for_children_to_finish(self):
        # wait for any and all children to schedule their next wake up call and call wait()
        while not all(child._ready_and_waiting for child in self._children):
            # note that sleeping a tiny amount is better than a straight while loop,
            # which slows down the other threads with its greediness
            time.sleep(0.000001)

        # while there are wakeup calls left to do amongst the children, and those wake up calls
        # would take place before we're done waiting here on the master clock
        while len(self._queue) > 0:
            # find the next wake up call
            next_wake_up_call = self._queue.pop(0)
            beats_till_wake = next_wake_up_call.t - self.beats()
            parent_wait_time = self._tempo_curve.get_wait_time(beats_till_wake)
            self.wait_in_parent(parent_wait_time)
            self._tempo_curve.advance(beats_till_wake, parent_wait_time)

            next_wake_up_call.clock._ready_and_waiting = False
            next_wake_up_call.clock._wait_event.set()

            # wait for the child clock that we woke up to finish processing, or to finish altogether
            while next_wake_up_call.clock in self._children and not next_wake_up_call.clock._ready_and_waiting:
                # note that sleeping a tiny amount is better than a straight while loop,
                # which slows down the other threads with its greediness
                time.sleep(0.000001)

    def log_processing_time(self):
        if logging.getLogger().level > 20:
            logging.warning("Set default logger to level of 20 or less to see INFO logs about clock processing time."
                            " (i.e. call logging.getLogger().setLevel(20))")
        self._log_processing_time = True

    def stop_logging_processing_time(self):
        self._log_processing_time = False

    def __repr__(self):
        child_list = "" if len(self._children) == 0 else ", ".join(str(child) for child in self._children)
        return ("Clock('{}')".format(self.name) if self.name is not None else "Clock") + "[" + child_list + "]"


class TempoCurve(ParameterCurve):

    def __init__(self, starting_rate=1.0):
        # This is built on a parameter curve of beat length (units = s / beat, or really parent_beats / beat)
        super().__init__(1/starting_rate)
        self._t = 0.0
        self._beats = 0.0

    def time(self):
        return self._t

    def beats(self):
        return self._beats

    @property
    def beat_length(self):
        return self.value_at(self._beats)

    @beat_length.setter
    def beat_length(self, beat_length):
        self.remove_segments_after(self.beats())
        # brings us up-to-date by adding a constant segment in case we haven't had a segment for a while
        if self.length() < self.beats():
            # no explicit segments have been made for a while, insert a constant segment to bring us up to date
            self.append_segment(self.end_level(), self.beats() - self.length())
        self.append_segment(beat_length, 0)

    @property
    def rate(self):
        return 1/self.beat_length

    @rate.setter
    def rate(self, rate):
        self.beat_length = 1/rate

    def rate_at(self, beat):
        return 1/self.value_at(self._beats + beat)

    @property
    def tempo(self):
        return self.rate * 60

    @tempo.setter
    def tempo(self, tempo):
        self.rate = tempo / 60

    def set_beat_length_target(self, beat_length_target, duration, curve_shape=0,
                               duration_units="beats", truncate=True):
        assert duration_units in ("beats", "time")
        # truncate removes any segments that extend into the future
        if truncate:
            self.remove_segments_after(self.beats())

        # brings us up-to-date by adding a constant segment in case we haven't had a segment for a while
        if self.length() < self.beats():
            # no explicit segments have been made for a while, insert a constant segment to bring us up to date
            self.append_segment(self.end_level(), self.beats() - self.length())

        if duration_units == "beats":
            extension_into_future = self.length() - self.beats()
            assert duration > extension_into_future, "Target must extend beyond the last existing target."
            self.append_segment(beat_length_target, duration - extension_into_future, curve_shape)
        else:
            # units == "time", so we need to figure out how many beats are necessary
            time_extension_into_future = self.integrate_interval(self.beats(), self.length())
            assert duration > time_extension_into_future, "Target must extend beyond the last existing target."

            # normalized_time = how long the curve would take if it were one beat long
            normalized_time = ParameterCurveSegment(
                0, 1, self.value_at(self.length()), beat_length_target, curve_shape
            ).integrate_segment(0, 1)
            desired_curve_length = duration - time_extension_into_future
            self.append_segment(beat_length_target, desired_curve_length / normalized_time, curve_shape)

    def set_rate_target(self, rate_target, duration, curve_shape=0, duration_units="beats", truncate=True):
        self.set_beat_length_target(1 / rate_target, duration, curve_shape, duration_units, truncate)

    def set_tempo_target(self, tempo_target, duration, curve_shape=0, duration_units="beats", truncate=True):
        self.set_beat_length_target(60 / tempo_target, duration, curve_shape, duration_units, truncate)

    def get_wait_time(self, beats):
        return self.integrate_interval(self._beats, self._beats + beats)

    def advance(self, beats, wait_time=None):
        if wait_time is None:
            wait_time = self.get_wait_time(beats)
        self._beats += beats
        self._t += wait_time

    def advance_time(self, seconds):
        beat_to_get_to = self.get_upper_integration_bound(self._beats, seconds)
        self.advance(beat_to_get_to - self._beats)
