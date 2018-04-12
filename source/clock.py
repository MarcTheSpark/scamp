import time
from sortedcontainers import SortedListWithKey
from collections import namedtuple
import threading
from multiprocessing.pool import ThreadPool
import logging
import math
from copy import deepcopy


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

    def __init__(self, name=None, parent=None, pool_size=200, timing_policy="relative"):
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
        self._tempo_map = TempoMap()

        # how long had my parent been around when I was created
        self.parent_offset = self.parent.time() if self.parent is not None else 0
        # will use these if not master clock
        self._ready_and_waiting = False
        self._wait_event = threading.Event()

        if self.is_master():
            # The thread pool runs on the master clock
            self._pool = ThreadPool(processes=pool_size)
            # Used to keep track of if we're using all the threads in the pool
            # if so, we just start a thread and throw a warning to increase pool size
            self._pool_semaphore = threading.BoundedSemaphore(pool_size)
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
        return self._tempo_map.time()

    def beats(self):
        return self._tempo_map.beats()

    @property
    def rate(self):
        return self._tempo_map.rate

    @rate.setter
    def rate(self, r):
        self._tempo_map.rate = r

    def absolute_rate(self):
        absolute_rate = self.rate if self.parent is None else (self.rate * self.parent.rate)
        return absolute_rate

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

    def _run_in_pool(self, target, args, kwargs):
        if self.master._pool_semaphore.acquire(blocking=False):
            semaphore = self.master._pool_semaphore
            self.master._pool.apply_async(target, args=args, kwds=kwargs, callback=lambda _: semaphore.release())
        else:
            logging.warning("Ran out of threads in the master clock's ThreadPool; small thread creation delays may "
                            "result. You can increase the number of threads in the pool to avoid this.")
            threading.Thread(target=target, args=args, kwargs=kwargs, daemon=True).start()

    def fork(self, process_function, name="", extra_args=(), kwargs=None):
        kwargs = {} if kwargs is None else kwargs

        child = Clock(name, parent=self)
        self._children.append(child)

        def _process(*args, **kwds):
            process_function(child, *args, **kwds)
            self._children.remove(child)

        self._run_in_pool(_process, extra_args, kwargs)

        return child

    def fork_unsynchronized(self, process_function, args=(), kwargs=None):
        kwargs = {} if kwargs is None else kwargs

        def _process(*args, **kwargs):
            process_function(*args, **kwargs)

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
            self.parent._queue.add(WakeUpCall(self.time_in_parent() + dt, self))
            self._ready_and_waiting = True
            self._wait_event.wait()
            self._wait_event.clear()
        self._last_sleep_time = time.time()

    def wait(self, beats):
        # wait for any and all children to schedule their next wake up call and call wait()
        while not all(child._ready_and_waiting for child in self._children):
            pass

        end_time = self.beats() + beats

        # while there are wakeup calls left to do amongst the children, and those wake up calls
        # would take place before we're done waiting here on the master clock
        while len(self._queue) > 0 and self._queue[0].t < end_time:
            # find the next wake up call
            next_wake_up_call = self._queue.pop(0)
            time_till_wake = next_wake_up_call.t - self.beats()
            self.wait_in_parent(self._tempo_map.get_wait_time(time_till_wake))
            self._tempo_map.advance(time_till_wake)

            next_wake_up_call.clock._ready_and_waiting = False
            next_wake_up_call.clock._wait_event.set()

            while next_wake_up_call.clock in self._children and not next_wake_up_call.clock._ready_and_waiting:
                # wait for the child clock that we woke up to finish processing, or to finish altogether
                pass

        # if we exit the while loop, that means that there is no one in the queue (meaning no children),
        # or the first wake up call is scheduled for after this wait is to end. So we can safely wait.

        self.wait_in_parent(self._tempo_map.get_wait_time(end_time - self.beats()))
        self._tempo_map.advance(end_time - self.beats())

    def sleep(self, beats):
        # alias to wait
        self.wait(beats)

    def wait_for_children_to_finish(self):
        # wait for any and all children to schedule their next wake up call and call wait()
        while not all(child._ready_and_waiting for child in self._children):
            pass

        # while there are wakeup calls left to do amongst the children, and those wake up calls
        # would take place before we're done waiting here on the master clock
        while len(self._queue) > 0:
            # find the next wake up call
            next_wake_up_call = self._queue.pop(0)
            time_till_wake = next_wake_up_call.t - self.beats()
            self.wait_in_parent(self._tempo_map.get_wait_time(time_till_wake))
            self._tempo_map.advance(time_till_wake)

            next_wake_up_call.clock._ready_and_waiting = False
            next_wake_up_call.clock._wait_event.set()

            while next_wake_up_call.clock in self._children and not next_wake_up_call.clock._ready_and_waiting:
                # wait for the child clock that we woke up to finish processing, or to finish altogether
                pass

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


class ParameterCurveSegment:

    def __init__(self, start_time, end_time, start_level, end_level, curve_shape):
        # note that start_level, end_level, and curvature are properties, since we want
        # to recalculate the constants that we use internally if they are changed.
        self.start_time = start_time
        self.end_time = end_time
        self._start_level = start_level
        self._end_level = end_level
        self._curve_shape = curve_shape
        # we avoid calculating the constants until necessary for the calculations so that this
        # class is lightweight and can freely be created and discarded by a ParameterCurve object
        self._curve_coefficient = self._A = self._B = None

    def _calculate_coefficients(self):
        # _curvature gets scaled internally to _curve_coefficient so that a "curvature" of 1 is
        # simple exponential interpolation. _A and _B are constants used in integration, and it's
        # more efficient to just calculate them once.
        self._curve_coefficient = self._curve_shape * math.log(self._end_level / self._start_level)
        if abs(self._curve_shape) < 0.000001:
            self._A = self._B = None
        else:
            self._A = (self._start_level - (self._end_level - self._start_level) /
                       (math.exp(self._curve_coefficient) - 1))
            self._B = (self._end_level - self._start_level) / \
                      (self._curve_coefficient * (math.exp(self._curve_coefficient) - 1))

    @property
    def start_level(self):
        return self._start_level

    @start_level.setter
    def start_level(self, start_level):
        self._start_level = start_level
        self._calculate_coefficients()

    @property
    def end_level(self):
        return self._end_level

    @end_level.setter
    def end_level(self, end_level):
        self._end_level = end_level
        self._calculate_coefficients()

    @property
    def curve_shape(self):
        return self._curve_shape

    @curve_shape.setter
    def curve_shape(self, curve_shape):
        self._curve_shape = curve_shape
        self._calculate_coefficients()

    def max_level(self):
        return max(self.start_level, self.end_level)

    @property
    def duration(self):
        return self.end_time - self.start_time

    def value_at(self, t):
        """
        Get interpolated value of the curve at time t
        The equation here is y(t) = y1 + (y2 - y1) / (e^S - 1) * (e^(S*t) - 1)
        (y1=starting rate, y2=final rate, t=progress along the curve 0 to 1, S=curvature coefficient)
        Essentially it's an appropriately scaled and stretched segment of e^x with x in the range [0, S]
        as S approaches zero, we get a linear segment, and S of ln(y2/y1) represents normal exponential interpolation
        large values of S correspond to last-minute change, and negative values of S represent early change
        """
        if self._A is None:
            self._calculate_coefficients()

        if t >= self.end_time:
            return self._end_level
        elif t <= self.start_time:
            return self._start_level
        else:
            norm_t = (t - self.start_time) / (self.end_time - self.start_time)
        if abs(self._curve_coefficient) < 0.000001:
            # S is or is essentially zero, so this segment is linear. That limiting case breaks
            # our standard formula, but is easy to simply interpolate
            return self._start_level + norm_t * (self._end_level - self._start_level)

        return self._start_level + (self._end_level - self._start_level) / \
            (math.exp(self._curve_coefficient) - 1) * (math.exp(self._curve_coefficient * norm_t) - 1)

    def _segment_antiderivative(self, normalized_t):
        # the antiderivative of the interpolation curve y(t) = y1 + (y2 - y1) / (e^S - 1) * (e^(S*t) - 1)
        return self._A * normalized_t + self._B * math.exp(self._curve_coefficient * normalized_t)

    def integrate_segment(self, t1, t2):
        """
        Integrate part of this segment.
        :param t1: start time
        :param t2: end time
        """
        assert self.start_time <= t1 <= self.end_time and self.start_time <= t2 <= self.end_time, \
            "Integration bounds must be within curve segment bounds."
        if self._A is None:
            self._calculate_coefficients()

        norm_t1 = (t1 - self.start_time) / (self.end_time - self.start_time)
        norm_t2 = (t2 - self.start_time) / (self.end_time - self.start_time)

        if abs(self._curve_coefficient) < 0.000001:
            # S is or is essentially zero, so this segment is linear. That limiting case breaks
            # our standard formula, but is easy to simple calculate based on average level
            start_level = (1 - norm_t1) * self.start_level + norm_t1 * self.end_level
            end_level = (1 - norm_t2) * self.start_level + norm_t2 * self.end_level
            return (t2 - t1) * (start_level + end_level) / 2

        segment_length = self.end_time - self.start_time

        return segment_length * (self._segment_antiderivative(norm_t2) - self._segment_antiderivative(norm_t1))

    def __contains__(self, t):
        # checks if the given time is contained within this parameter curve segment
        return self.start_time <= t <= self.end_time

    def __repr__(self):
        return "ParameterCurveSegment({}, {}, {}, {}, {})".format(self.start_time, self.end_time, self.start_level,
                                                                  self.end_level, self.curve_shape)


class ParameterCurve:

    def __init__(self, levels=(0, 0), durations=(0,), curve_shapes=None):
        """
        Implements a parameter curve using exponential curve segments.
        A curve shape of zero is linear, > 0 changes late, and < 0 changes early.
        A curve shape 1 represents standard exponential interpolation, i.e. fixed proportional growth
        :param levels: at least 1 level should be given (if only one level is given, it is automatically doubled so as
        to be the start and end level of the one segment of the curve)
        :param durations: there should be one fewer duration than level given
        :param curve_shapes: there should be one fewer than the number of levels. If None, all segments are linear
        """
        if not hasattr(levels, "__len__"):
            levels = (levels,)
        assert hasattr(levels, "__len__") and hasattr(durations, "__len__") \
            and (curve_shapes is None or hasattr(curve_shapes, "__len__"))
        assert len(levels) > 0, "At least one level is needed to construct a parameter curve."
        if len(levels) == 1:
            levels = levels + levels
        assert len(durations) == len(levels) - 1, "Inconsistent number of levels and durations given."
        if curve_shapes is None:
            curve_shapes = [0] * (len(levels) - 1)

        self._segments = self._construct_segments_list(levels, durations, curve_shapes)

    @staticmethod
    def _construct_segments_list(levels, durations, curve_shapes):
        if len(levels) == 0:
            return [ParameterCurveSegment(0, 0, levels[0], levels[0], 0)]
        segments = []
        t = 0
        for i in range(len(levels) - 1):
            segments.append(ParameterCurveSegment(t, t + durations[i],
                                                  levels[i], levels[i + 1], curve_shapes[i]))
            t += durations[i]
        return segments

    def length(self):
        if len(self._segments) == 0:
            return 0
        return self._segments[-1].end_time

    def append_segment(self, level, duration, curve_shape=0.0):
        if len(self._segments) == 1 and self._segments[0].duration() == 0:
            self._segments[0].end_level = ParameterCurveSegment(0, duration, self._segments[0].start_level,
                                                                level, curve_shape)
        else:
            self._segments.append(ParameterCurveSegment(self.length(), self.length() + duration,
                                                        self._segments[-1].end_level, level, curve_shape))

    def insert(self, t, level, curve_shape_in=0, curve_shape_out=0):
        # TODO: This
        assert t >= 0, "ParameterCurve is only defined for positive values"
        if len(self._segments) == 0:
            # empty curve, just put zero-length segment right at the beginning
            # honestly, it shouldn't ever because an empty curve is created with that zero-length segment anyway
            self.append_segment(level, 0, curve_shape_in)
        if t > self.length():
            self.append_segment(level, t - self.length(), curve_shape_in)
            return
        elif t == self.length:
            self._segments[-1].end_level = level
            self._segments[-1].curve_shape = curve_shape_in
            # replacing the very end of the curve. Should probably rewrite the last segment's final level and curve shape
            pass
        else:
            for segment in self._segments:
                if t == segment.start_time:
                    # we are right on the dot of an existing segment, so we replace it
                    pass
                elif segment.start_time < t < segment.end_time:
                    # we are inside an existing segment
                    pass

    def pop_segment(self):
        if len(self._segments) == 1:
            if self._segments[0].end_time != self._segments[0].start_time or \
                    self._segments[0].end_level != self._segments[0].start_level:
                self._segments[0].end_time = self._segments[0].start_time
                self._segments[0].end_level = self._segments[0].start_level
                return
            else:
                raise IndexError("pop from empty ParameterCurve")
        return self._segments.pop()

    def remove_segments_after(self, t):
        # TODO: This
        pass

    def integrate_interval(self, t1, t2):
        # TODO: This
        pass

    @classmethod
    def from_levels(cls, levels, length=1.0):
        """
        Construct a parameter curve from levels alone, normalized to the given length
        :param levels: the levels of the curve
        :param length: the total length of the curve, divided evenly amongst the levels
        :return: a ParameterCurve
        """
        assert len(levels) > 0, "At least one level is needed to construct a parameter curve."
        if len(levels) == 1:
            levels = list(levels) + levels[-1]
        # just given levels, so we linearly interpolate segments of equal length
        durations = [length / (len(levels) - 1)] * (len(levels) - 1)
        curves = [0.0] * (len(levels) - 1)
        return cls(levels, durations, curves)

    @classmethod
    def from_list(cls, constructor_list):
        # converts from a list that may contain just levels, may have levels and durations, and may have everything
        # a input of [1, 0.5, 0.3] is interpreted as evenly spaced levels with a total duration of 1
        # an input of [[1, 0.5, 0.3], 3.0] is interpreted as levels and durations with a total duration of e.g. 3.0
        # an input of [[1, 0.5, 0.3], [0.2, 0.8]] is interpreted as levels and durations
        # an input of [[1, 0.5, 0.3], [0.2, 0.8], [2, 0.5]] is interpreted as levels, durations, and curvatures
        if hasattr(constructor_list[0], "__len__"):
            # we were given levels and durations, and possibly curvature values
            if len(constructor_list) == 2:
                if hasattr(constructor_list[1], "__len__"):
                    # given levels and durations
                    return ParameterCurve(constructor_list[0], constructor_list[1])
                else:
                    # given levels and the total length
                    return ParameterCurve.from_levels(constructor_list[0], length=constructor_list[1])

            elif len(constructor_list) >= 3:
                # given levels, durations, and curvature values
                return cls(constructor_list[0], constructor_list[1], constructor_list[2])
        else:
            # just given levels
            return ParameterCurve.from_levels(constructor_list)

    def normalize_to_duration(self, desired_duration, in_place=True):
        out = self if in_place else deepcopy(self)
        if self.length() != desired_duration:
            ratio = desired_duration / self.length()
            for segment in out._segments:
                segment.start_time *= ratio
                segment.end_time *= ratio
        return out

    def value_at(self, t):
        if t <= 0:
            return self._segments[0].start_level
        for segment in self._segments:
            if t in segment:
                return segment.value_at(t)
        return self._segments[-1].end_level

    def max_value(self):
        return max(segment.max_level() for segment in self._segments)

    @property
    def levels(self):
        return [segment.start_level for segment in self._segments] + [self._segments[-1].end_level]

    @property
    def durations(self):
        return [segment.duration for segment in self._segments]

    @property
    def curve_shapes(self):
        return [segment.curve_shape for segment in self._segments]

    def to_json(self):
        levels = self.levels
        durations = self.durations
        curve_shapes = self.curve_shapes
        even_durations = all(x == durations[0] for x in durations)
        curvature_unnecessary = all(x == 0 for x in curve_shapes)
        if even_durations and curvature_unnecessary:
            if self.length() == 1:
                return levels
            else:
                return [levels, self.length()]
        elif curvature_unnecessary:
            return [levels, durations]
        else:
            return [levels, durations, curve_shapes]

    @staticmethod
    def from_json(json_list):
        return ParameterCurve.from_list(json_list)

    def __repr__(self):
        return "ParameterCurve({}, {}, {})".format(self.levels, self.durations, self.curve_shapes)


# class TempoMap:
#
#     def __init__(self):
#         self._t = 0.0
#         self._beats = 0.0
#         self._rate = 1.0
#         # either None or (target_rate, start_time, end_time, curve_power, curve_segment_start, curve_segment_end)
#         self._rate_target = None
#         self._timeline_history = []
#
#     def time(self):
#         return self._t
#
#     def beats(self):
#         return self._beats
#
#     @property
#     def rate(self):
#         return self._rate
#
#     @rate.setter
#     def rate(self, rate):
#         self._rate = rate
#
#     def set_rate_target(self, target, transition_time, curve=1):
#         pass
#
#     @property
#     def tempo(self):
#         return self._rate * 60
#
#     def set_tempo(self, tempo):
#         self._rate = tempo / 60
#
#     def get_wait_time(self, beats):
#         return beats / self._rate
#
#     def advance(self, beats):
#         self._beats += beats
#         self._t += self.get_wait_time(beats)
#
#     @staticmethod
#     def interpolate(T1, T2, t, S):
#         """
#         The equation here is T(t) = T1 + (T2 - T1) / (e^S - 1) * (e^(S*t) - 1)
#         (T1=starting rate, T2=final rate, t=progress along the curve 0 to 1, S=curvature coefficient)
#         essentially it's an appropriately scaled and stretched segment of e^x with x in the range [0, S]
#         as S approaches zero, we get a linear segment, while large values of S correspond to last-minute change
#         conveniently, negative values of S represent early change in a symmetrical way
#         a value of S of ln(T2/T1) gives us steady, proportional exponential growth, a smooth accelerando
#         """
#         if abs(S) < 0.000001:
#             # S is or is essentially zero, so this segment is linear. That limiting case breaks
#             # our standard formula, but is easy to simply interpolate
#             return T1 + t*(T2 - T1)
#         return T1 + (T2 - T1) / (math.exp(S) - 1) * (math.exp(S * t) - 1)

# start = time.time()
# print(time.time()-start)
# start = time.time()
# bob = ParameterCurveSegment(2, 10, 1, 6, 0)
# print(time.time()-start)
# start = time.time()
# pc = ParameterCurve.from_levels([2, 0.5, 1, 7])
# print(time.time()-start)
# start = time.time()
# pc = ParameterCurve.from_levels([2, 0.5, 1, 7])
# print(time.time()-start)
# start = time.time()
# pc.normalize_to_duration(6)
# print(time.time()-start)


start = time.time()
bob = ParameterCurve([6, 10, 3, 13], [2, 0.5, 2.5], [0, 1, 1])
print(bob)
bob.pop_segment()
print(bob)
bob.pop_segment()
print(bob)
bob.pop_segment()
print(bob)

print(ParameterCurve.from_json(bob.to_json()))

# TODO: MAYBE ParameterCurve should only have the parameter segments in it, not store the lists of levels, durations, etc.
# it would have to reconstruct them to store in a json, but that's okay, I think
# TODO: BUILD IT BASED ON BEAT_LENGTH, HAVE DEFAULT CURVATURE BE LINEAR CHANGE IN BEAT_LENGTH.
# INTERESTINGLY, THIS SEEMS TO BE THE SAME AS EXPONENTIAL INTERPOLATION OF TEMPO; I don't understand why...