import math
from copy import deepcopy
from playcorder.utilities import SavesToJSON
import numbers


class ParameterCurve(SavesToJSON):

    def __init__(self, segments=None):
        """
        Implements a parameter curve using exponential curve segments. Initialization happens outside
        of the constructor for smoother subclassing; this way all of the class methods work correctly
        on derived classes like TempoCurve.
        """
        if segments is None:
            self._segments = None
            self.initialize()
        else:
            self._segments = segments

    def initialize(self, levels=(0, 0), durations=(0,), curve_shapes=None):
        """
        A curve shape of zero is linear, > 0 changes late, and < 0 changes early. Strings containing "exp" will also be
        evaluated, with "exp" standing for the shape that will produce constant proportional change per unit time.

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

        self._segments = ParameterCurve._construct_segments_list(levels, durations, curve_shapes)
        return self

    @staticmethod
    def _construct_segments_list(levels, durations, curve_shapes):
        if len(levels) == 0:
            return [ParameterCurveSegment(0, 0, levels[0], levels[0], 0)]
        segments = []
        t = 0
        for i in range(len(levels) - 1):
            segments.append(ParameterCurveSegment(t, t + durations[i], levels[i], levels[i + 1], curve_shapes[i]))
            t += durations[i]
        return segments

    # ---------------------------- Various Properties --------------------------------

    def length(self):
        if len(self._segments) == 0:
            return 0
        return self._segments[-1].end_time

    def start_level(self):
        return self._segments[0].start_level

    def end_level(self):
        return self._segments[-1].end_level

    def max_level(self, t_range=None):
        if t_range is None:
            # checking over the entire range, so that's easy
            return max(segment.max_level() for segment in self._segments)
        else:
            # checking over the range (t1, t2), so look at the values at those endpoints and any anchor points between
            assert hasattr(t_range, "__len__") and len(t_range) == 2 and t_range[0] < t_range[1]
            t1, t2 = t_range
            points_to_check = [self.value_at(t1), self.value_at(t2)]
            for segment in self._segments:
                if t1 <= segment.start_time <= t2:
                    points_to_check.append(segment.start_level)
                if t1 <= segment.end_time <= t2:
                    points_to_check.append(segment.end_level)
            return max(points_to_check)

    def average_level(self):
        return self.integrate_interval(0, self.length()) / self.length()

    def max_absolute_slope(self):
        return max(segment.max_absolute_slope() for segment in self._segments)

    @property
    def levels(self):
        return tuple([segment.start_level for segment in self._segments] + [self.end_level()])

    @property
    def durations(self):
        return tuple([segment.duration for segment in self._segments])

    @property
    def curve_shapes(self):
        return tuple([segment.curve_shape for segment in self._segments])

    # ----------------------- Insertion of new control points --------------------------

    def insert(self, t, level, curve_shape_in=0, curve_shape_out=0):
        """
        Insert a curve point at time t, and set the shape of the curve into and out of it
        """
        assert t >= 0, "ParameterCurve is only defined for positive values"
        if t > self.length():
            # adding a point after the curve
            self.append_segment(level, t - self.length(), curve_shape_in)
            return
        else:
            for i, segment in enumerate(self._segments):
                if segment.start_time < t < segment.end_time:
                    # we are inside an existing segment, so we break it in two
                    # save the old segment end time and level, since these will be the end of the second half
                    end_time = segment.end_time
                    end_level = segment.end_level
                    # change the first half to end at t and have the given shape
                    segment.end_time = t
                    segment.curve_shape = curve_shape_in
                    segment.end_level = level
                    new_segment = ParameterCurveSegment(t, end_time, level, end_level, curve_shape_out)
                    self._segments.insert(i+1, new_segment)
                    break
                else:
                    if t == segment.start_time:
                        # we are right on the dot of an existing segment, so we replace it
                        segment.start_level = level
                        segment.curve_shape = curve_shape_out
                    if t == segment.end_time:
                        segment.end_level = level
                        segment.curve_shape = curve_shape_in

    def insert_interpolated(self, t):
        """
        insert another curve point at the given time, without changing the shape of the curve
        """
        assert t >= 0, "ParameterCurve is only defined for positive values."
        assert t <= self.length(), "Cannot interpolate after end of curve."
        if t == self.length():
            return
        for i, segment in enumerate(self._segments):
            if t == segment.start_time:
                return
            if t in segment:
                # this is the case that matters; t is within one of the segments
                part1, part2 = segment.split_at(t)
                self._segments.insert(i+1, part2)

    # ----------------------- Appending / removing segments --------------------------

    def append_segment(self, level, duration, curve_shape=0.0, tolerance=0):
        """
        Append a segment to the end of the curve ending at level and lasting for duration.
        If we're adding a linear segment to a linear segment, then we extend the last linear segment
        instead of adding a new one if the level is within tolerance of where the last one was headed
        :return:
        """
        if self._segments[-1].duration == 0:
            # the previous segment has no length. Are we also adding a segment with no length?
            if duration == 0:
                # If so, replace the end level of the existing zero-length segment
                self._segments[-1].end_level = level
            else:
                # okay, we're adding a segment with length
                # did the previous segment actually change the level?
                if self._segments[-1].end_level != self._segments[-1].start_level:
                    # If so we keep it and add a new one
                    self._segments.append(ParameterCurveSegment(self.length(), self.length() + duration,
                                                                self.end_level(), level, curve_shape))
                else:
                    # if not, just modify the previous segment into what we want
                    self._segments[-1].end_level = level
                    self._segments[-1].end_time = self.length() + duration
                    self._segments[-1].curve_shape = curve_shape
        elif self._segments[-1].curve_shape == 0 and curve_shape == 0 and \
                abs(self._segments[-1].value_at(self.length() + duration, clip_at_boundary=False) - level) <= tolerance:
            # we're adding a point that would be a perfect continuation of the previous linear segment
            # (could do this for non-linear, but it's probably not worth the effort)
            self._segments[-1].end_time = self.length() + duration
            self._segments[-1].end_level = level
        else:
            self._segments.append(ParameterCurveSegment(self.length(), self.length() + duration,
                                                        self.end_level(), level, curve_shape))

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
        if t < 0:
            while True:
                try:
                    self.pop_segment()
                except IndexError:
                    break
        for i in range(len(self._segments)):
            this_segment = self._segments[i]
            if t == this_segment.start_time:
                while self.length() > t:
                    self.pop_segment()
                return
            elif this_segment.start_time < t < this_segment.end_time:
                self.insert_interpolated(t)
                while self.length() > t:
                    self.pop_segment()
                return

    # ------------------------ Interpolation, Integration --------------------------

    def value_at(self, t):
        if t < 0:
            return self.start_level()
        for segment in reversed(self._segments):
            # we start at the end in case of zero_length segments; it's best that they return their end level
            if t in segment:
                return segment.value_at(t)
        return self.end_level()

    def integrate_interval(self, t1, t2):
        if t1 == t2:
            return 0
        if t2 < t1:
            return -self.integrate_interval(t2, t1)
        if t1 < 0:
            return -t1 * self._segments[0].start_level + self.integrate_interval(0, t2)
        if t2 > self.length():
            return (t2 - self.length()) * self.end_level() + self.integrate_interval(t1, self.length())
        # now that the edge conditions are covered, we just add up the segment integrals
        integral = 0

        # if there are a lot of segments, we bisect the list repeatedly until we get close t
        start_index = 0
        while True:
            new_start_index = start_index + (len(self._segments) - start_index) // 2
            if self._segments[new_start_index].end_time < t1 and len(self._segments) - new_start_index > 3:
                start_index = new_start_index
            else:
                break

        for segment in self._segments[start_index:]:
            if t1 < segment.start_time:
                if t2 > segment.start_time:
                    if t2 <= segment.end_time:
                        # this segment contains the end of our integration interval, so we're done after this
                        integral += segment.integrate_segment(segment.start_time, t2)
                        break
                    else:
                        # this segment is fully within out integration interval, so add its full area
                        integral += segment.integrate_segment(segment.start_time, segment.end_time)
            elif t1 in segment:
                # since we know that t2 > t1, there's two possibilities
                if t2 in segment:
                    # this segment contains our whole integration interval
                    integral += segment.integrate_segment(t1, t2)
                    break
                else:
                    # this is the first segment in our integration interval
                    integral += segment.integrate_segment(t1, segment.end_time)
        return integral

    def get_upper_integration_bound(self, t1, desired_area, max_error=0.001):
        if desired_area < max_error:
            return t1
        t1_level = self.value_at(t1)
        t2_guess = desired_area / t1_level + t1
        area = self.integrate_interval(t1, t2_guess)
        if area <= desired_area:
            if desired_area - area < max_error:
                # we hit it almost perfectly and didn't go over
                return t2_guess
            else:
                # we undershot, so start from where we left off.
                # Eventually we will get close enough that we're below the max_error
                return self.get_upper_integration_bound(t2_guess, desired_area - area, max_error=max_error)
        else:
            # we overshot, so back up to a point that we know must be below the upper integration bound
            conservative_guess = t1_level / self.max_level((t1, t2_guess)) * (t2_guess - t1) + t1
            return self.get_upper_integration_bound(
                conservative_guess, desired_area - self.integrate_interval(t1, conservative_guess), max_error=max_error
            )

    # -------------------------- Utilities, classmethods ----------------------------

    def normalize_to_duration(self, desired_duration, in_place=True):
        out = self if in_place else deepcopy(self)
        if self.length() != desired_duration:
            ratio = desired_duration / self.length()
            for segment in out._segments:
                segment.start_time *= ratio
                segment.end_time *= ratio
        return out

    def inflection_points(self):
        """
        Returns a list of the times where the curve changes direction.
        """
        inflection_points = []
        last_direction = 0
        for segment in self._segments:
            if segment.end_level > segment.start_level:
                direction = 1
            elif segment.end_level < segment.start_level:
                direction = -1
            else:
                # if this segment was static, then keep the direction we had going in
                direction = last_direction
            if last_direction * direction < 0:
                # we changed sign, since
                inflection_points.append(segment.start_time)
            last_direction = direction
        return inflection_points

    @classmethod
    def from_levels_and_durations(cls, levels=(0, 0), durations=(0,), curve_shapes=None):
        return cls().initialize(levels, durations, curve_shapes)

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
            levels = list(levels) * 2
        # just given levels, so we linearly interpolate segments of equal length
        durations = [length / (len(levels) - 1)] * (len(levels) - 1)
        curves = [0.0] * (len(levels) - 1)
        return cls.from_levels_and_durations(levels, durations, curves)

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
                    return cls.from_levels_and_durations(constructor_list[0], constructor_list[1])
                else:
                    # given levels and the total length
                    return cls.from_levels(constructor_list[0], length=constructor_list[1])

            elif len(constructor_list) >= 3:
                # given levels, durations, and curvature values
                return cls.from_levels_and_durations(constructor_list[0], constructor_list[1], constructor_list[2])
        else:
            # just given levels
            return cls.from_levels(constructor_list)

    def split_at(self, t, change_original=False):
        """
        Splits the ParameterCurve at one or several points and returns a tuple of the pieces
        :param t: either the time t or a tuple/list of times t at which to split the curve
        :param change_original: if true, the original ParameterCurve gets turned into the first of the returned tuple
        :return: tuple of ParameterCurves representing the pieces this has been split into
        """
        to_split = self if change_original else ParameterCurve([x.clone() for x in self._segments])

        # if t is a tuple or list, we split at all of those times and return len(t) + 1 segments
        # This is implemented recursively. If len(t) is 1, t is replaced by t[0]
        # If len(t) > 1, then we sort and set aside t[1:] as remaining splits to do on the second half
        # and set t to t[0]. Note that we subtract t[0] from each of t[1:] to shift it to start from 0
        remaining_splits = None
        if hasattr(t, "__len__"):
            # ignore all split points that are outside this ParameterCurve's range
            t = [x for x in t if 0 <= x <= to_split.length()]
            if len(t) == 0:
                # if no usable points are left we're done (note we always return a tuple for consistency)
                return to_split,

            if len(t) > 1:
                t = list(t)
                t.sort()
                remaining_splits = [x - t[0] for x in t[1:]]
            t = t[0]

        # cover the case of trying to split outside of the ParameterCurve's range
        # (note we always return a tuple for consistency)
        if not 0 < t < to_split.length():
            return to_split,

        # Okay, now we go ahead with a single split at time t
        to_split.insert_interpolated(t)
        for i, segment in enumerate(to_split._segments):
            if segment.start_time == t:
                second_half = ParameterCurve(to_split._segments[i:])
                to_split._segments = to_split._segments[:i]
                for second_half_segment in second_half._segments:
                    second_half_segment.start_time -= t
                    second_half_segment.end_time -= t
                break

        if remaining_splits is None:
            return to_split, second_half
        else:
            return to_split, second_half.split_at(remaining_splits, change_original=True)

    def _to_json(self):
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

    @classmethod
    def _from_json(cls, json_list):
        return cls.from_list(json_list)

    def is_shifted_version_of(self, other):
        assert isinstance(other, ParameterCurve)
        return all(x.is_shifted_version_of(y) for x, y in zip(self._segments, other._segments))

    def shift_vertical(self, amount):
        for segment in self._segments:
            segment.shift_vertical(amount)

    def __add__(self, other):
        return ParameterCurve([segment + other for segment in self._segments])

    def __radd__(self, other):
        return self.__add__(other)

    def __sub__(self, other):
        return self.__add__(-other)

    def __rsub__(self, other):
        return self.__radd__(-other)

    def __mul__(self, other):
        return ParameterCurve([segment * other for segment in self._segments])

    def __rmul__(self, other):
        return self.__mul__(other)

    def __truediv__(self, other):
        return self.__mul__(1/other)

    def __repr__(self):
        return "ParameterCurve({}, {}, {})".format(self.levels, self.durations, self.curve_shapes)


class ParameterCurveSegment:

    def __init__(self, start_time, end_time, start_level, end_level, curve_shape):
        """
        A segment of a parameter curve, with the ability to perform interpolation and integration
        :param curve_shape: 0 is linear, > 0 changes late, < 0 changes early, also, string expressions involving "exp"
        can be given where "exp" stands for the shape that will produce constant proportional change per unit time.
        """
        # note that start_level, end_level, and curvature are properties, since we want
        # to recalculate the constants that we use internally if they are changed.
        self.start_time = start_time
        self.end_time = end_time
        self._start_level = start_level
        self._end_level = end_level
        if isinstance(curve_shape, str):
            assert end_level / start_level > 0, \
                "Exponential interpolation is impossible between {} and {}".format(start_level, end_level)
            exp_shape = math.log(end_level / start_level)
            # noinspection PyBroadException
            try:
                self._curve_shape = eval(curve_shape, {"exp": exp_shape})
            except Exception:
                raise ValueError("Expression for curve shape not understood")
        else:
            self._curve_shape = curve_shape
        # we avoid calculating the constants until necessary for the calculations so that this
        # class is lightweight and can freely be created and discarded by a ParameterCurve object

        self._A = self._B = None

    def _calculate_coefficients(self):
        # A and _B are constants used in integration, and it's more efficient to just calculate them once.
        if abs(self._curve_shape) < 0.000001:
            # the curve shape is essentially zero, so set the constants to none as a flag to use linear interpolation
            self._A = self._B = None
            return
        else:
            self._A = (self._start_level - (self._end_level - self._start_level) / (math.exp(self._curve_shape) - 1))
            self._B = (self._end_level - self._start_level) / (self._curve_shape * (math.exp(self._curve_shape) - 1))

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

    @property
    def duration(self):
        return self.end_time - self.start_time

    def max_level(self):
        return max(self.start_level, self.end_level)

    def average_level(self):
        return self.integrate_segment(self.start_time, self.end_time) / self.duration

    def max_absolute_slope(self):
        """
        Get the max absolute value of the slope of this segment over the interval.
        Since the slope of e^x is e^x, the max slope of e^x in the interval of [0, S] is e^S. If S is negative, the
        curve has exactly the same slopes, but in reverse (still need to think about why), so that's why the max slope
        term ends up being e^abs(S). We then have to scale that by the average slope over our interval divided by
        the average slope of e^x over [0, S] to get the true, scaled average slope. Hence the other scaling terms.
        """
        if self.duration == 0:
            # a duration of zero means we have an immediate change of value. Since this function is used primarily
            # to figure out the temporal resolution needed for smoothness, that doesn't matter; it's supposed to be
            # a discontinuity. So we just return zero as a throwaway.
            return 0
        if abs(self._curve_shape) < 0.000001:
            # it's essentially linear, so just return the average slope
            return abs(self._end_level - self._start_level) / self.duration
        return math.exp(abs(self._curve_shape)) * abs(self._end_level - self._start_level) / self.duration * \
            abs(self._curve_shape) / (math.exp(abs(self._curve_shape)) - 1)

    def value_at(self, t, clip_at_boundary=True):
        """
        Get interpolated value of the curve at time t
        The equation here is y(t) = y1 + (y2 - y1) / (e^S - 1) * (e^(S*t) - 1)
        (y1=starting rate, y2=final rate, t=progress along the curve 0 to 1, S=curve_shape)
        Essentially it's an appropriately scaled and stretched segment of e^x with x in the range [0, S]
        as S approaches zero, we get a linear segment, and S of ln(y2/y1) represents normal exponential interpolation
        large values of S correspond to last-minute change, and negative values of S represent early change
        """
        if self._A is None:
            self._calculate_coefficients()

        if clip_at_boundary and t >= self.end_time:
            return self._end_level
        elif clip_at_boundary and t <= self.start_time:
            return self._start_level
        else:
            norm_t = (t - self.start_time) / (self.end_time - self.start_time)
        if abs(self._curve_shape) < 0.000001:
            # S is or is essentially zero, so this segment is linear. That limiting case breaks
            # our standard formula, but is easy to simply interpolate
            return self._start_level + norm_t * (self._end_level - self._start_level)

        return self._start_level + (self._end_level - self._start_level) / \
            (math.exp(self._curve_shape) - 1) * (math.exp(self._curve_shape * norm_t) - 1)

    def _segment_antiderivative(self, normalized_t):
        # the antiderivative of the interpolation curve y(t) = y1 + (y2 - y1) / (e^S - 1) * (e^(S*t) - 1)
        return self._A * normalized_t + self._B * math.exp(self._curve_shape * normalized_t)

    def integrate_segment(self, t1, t2):
        """
        Integrate part of this segment.
        :param t1: start time (relative to the time zero, not to the start time of this segment)
        :param t2: end time (ditto)
        """
        assert self.start_time <= t1 <= self.end_time and self.start_time <= t2 <= self.end_time, \
            "Integration bounds must be within curve segment bounds."
        if t1 == t2:
            return 0
        if self._A is None:
            self._calculate_coefficients()

        norm_t1 = (t1 - self.start_time) / (self.end_time - self.start_time)
        norm_t2 = (t2 - self.start_time) / (self.end_time - self.start_time)

        if abs(self._curve_shape) < 0.000001:
            # S is or is essentially zero, so this segment is linear. That limiting case breaks
            # our standard formula, but is easy to simple calculate based on average level
            start_level = (1 - norm_t1) * self.start_level + norm_t1 * self.end_level
            end_level = (1 - norm_t2) * self.start_level + norm_t2 * self.end_level
            return (t2 - t1) * (start_level + end_level) / 2

        segment_length = self.end_time - self.start_time

        return segment_length * (self._segment_antiderivative(norm_t2) - self._segment_antiderivative(norm_t1))

    def split_at(self, t):
        """
        Split this segment into two ParameterCurveSegment's without altering the curve shape and return them.
        This segment is altered in the process.
        :param t: where to split it (t is absolute time)
        :return: a tuple of this segment modified to be only the first part, and a new segment for the second part
        """
        assert self.start_time < t < self.end_time
        middle_level = self.value_at(t)
        # since the curve shape represents how much of the curve e^x we go through, you simply split proportionally
        curve_shape_1 = (t - self.start_time) / (self.end_time - self.start_time) * self.curve_shape
        curve_shape_2 = self.curve_shape - curve_shape_1
        new_segment = ParameterCurveSegment(t, self.end_time, middle_level, self.end_level, curve_shape_2)

        self.end_time = t
        self._end_level = middle_level
        self._curve_shape = curve_shape_1
        self._calculate_coefficients()
        return self, new_segment

    def clone(self):
        return ParameterCurveSegment(self.start_time, self.end_time, self.start_level, self.end_level, self.curve_shape)

    def shift_vertical(self, amount):
        assert isinstance(amount, numbers.Number)
        self._start_level += amount
        self._end_level += amount
        self._calculate_coefficients()

    def scale_vertical(self, amount):
        assert isinstance(amount, numbers.Number)
        self._start_level *= amount
        self._end_level *= amount
        self._calculate_coefficients()

    def is_shifted_version_of(self, other):
        assert isinstance(other, ParameterCurveSegment)
        return self.start_time == other.start_time and self.end_time == other.end_time and \
               self._start_level - other._start_level == self._end_level - other._end_level and \
               self._curve_shape == other._curve_shape

    def __add__(self, other):
        if not isinstance(other, numbers.Number):
            raise TypeError("Can only add numerical constants to ParameterCurve or ParameterCurveSegment")
        out = self.clone()
        out.shift_vertical(other)
        return out

    def __radd__(self, other):
        return self.__add__(other)

    def __sub__(self, other):
        return self.__add__(-other)

    def __rsub__(self, other):
        return self.__radd__(-other)

    def __mul__(self, other):
        if not isinstance(other, numbers.Number):
            raise TypeError("Can only add numerical constants to ParameterCurve or ParameterCurveSegment")
        out = self.clone()
        out.scale_vertical(other)
        return out

    def __rmul__(self, other):
        return self.__mul__(other)

    def __truediv__(self, other):
        return self.__mul__(1/other)

    def __contains__(self, t):
        # checks if the given time is contained within this parameter curve segment
        # maybe this is silly, but it seemed a little convenient
        return self.start_time <= t < self.end_time

    def __repr__(self):
        return "ParameterCurveSegment({}, {}, {}, {}, {})".format(self.start_time, self.end_time, self.start_level,
                                                                  self.end_level, self.curve_shape)