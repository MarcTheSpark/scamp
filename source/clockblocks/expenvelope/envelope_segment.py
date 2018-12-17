from .utilities import _make_envelope_segments_from_function
import numbers
import math


class EnvelopeSegment:

    def __init__(self, start_time, end_time, start_level, end_level, curve_shape):
        """
        A segment of an envelope, with the ability to perform interpolation and integration
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
        # class is lightweight and can freely be created and discarded by an Envelope object

        self._A = self._B = None

    @classmethod
    def from_endpoints_and_halfway_level(cls, start_time, end_time, start_level, end_level, halfway_level):
        if start_level == halfway_level == end_level:
            return cls(start_time, end_time, start_level, end_level, 0)
        assert min(start_level, end_level) < halfway_level < max(start_level, end_level), \
            "Halfway level must be strictly between start and end levels, or equal to both."
        # class method that allows us to give a guide point half way through instead of giving
        # the curve_shape directly. This lets us try to match a curve that's not perfectly the right type.
        if end_level == start_level:
            # if the end_level equals the start_level, then the best we can do is a straight line
            return cls(start_time, end_time, start_level, end_level, 0)
        halfway_level_normalized = (halfway_level - start_level) / (end_level - start_level)
        curve_shape = 2 * math.log(1 / halfway_level_normalized - 1)
        return cls(start_time, end_time, start_level, end_level, curve_shape)

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
        Split this segment into two EnvelopeSegment's without altering the curve shape and return them.
        This segment is altered in the process.
        :param t: where to split it (t is absolute time)
        :return: a tuple of this segment modified to be only the first part, and a new segment for the second part
        """
        assert self.start_time < t < self.end_time
        middle_level = self.value_at(t)
        # since the curve shape represents how much of the curve e^x we go through, you simply split proportionally
        curve_shape_1 = (t - self.start_time) / (self.end_time - self.start_time) * self.curve_shape
        curve_shape_2 = self.curve_shape - curve_shape_1
        new_segment = EnvelopeSegment(t, self.end_time, middle_level, self.end_level, curve_shape_2)

        self.end_time = t
        self._end_level = middle_level
        self._curve_shape = curve_shape_1
        self._calculate_coefficients()
        return self, new_segment

    def clone(self):
        return EnvelopeSegment(self.start_time, self.end_time, self.start_level, self.end_level, self.curve_shape)

    def shift_vertical(self, amount):
        assert isinstance(amount, numbers.Number)
        self._start_level += amount
        self._end_level += amount
        self._calculate_coefficients()
        return self

    def scale_vertical(self, amount):
        assert isinstance(amount, numbers.Number)
        self._start_level *= amount
        self._end_level *= amount
        self._calculate_coefficients()
        return self

    def shift_horizontal(self, amount):
        assert isinstance(amount, numbers.Number)
        self.start_time += amount
        self.end_time += amount
        return self

    def scale_horizontal(self, amount):
        assert isinstance(amount, numbers.Number)
        self.start_time *= amount
        self.end_time *= amount
        return self

    def is_shifted_version_of(self, other, tolerance=1e-10):
        assert isinstance(other, EnvelopeSegment)
        return abs(self.start_time - other.start_time) < tolerance and \
               abs(self.end_time - other.end_time) < tolerance and \
               ((self._start_level - other._start_level) - (self._end_level - other._end_level)) < tolerance and \
               (self._curve_shape - other._curve_shape) < tolerance

    def get_graphable_point_pairs(self, resolution=25, endpoint=True):
        x_values = [self.start_time + x / resolution * self.duration
                    for x in range(resolution + 1 if endpoint else resolution)]
        y_values = [self.value_at(x) for x in x_values]
        return x_values, y_values

    def show_plot(self, title=None, resolution=25):
        try:
            import matplotlib.pyplot as plt
        except ImportError:
            raise ImportError("Could not find matplotlib, which is needed for plotting.")
        fig, ax = plt.subplots()
        ax.plot(*self.get_graphable_point_pairs(resolution))
        ax.set_title('Graph of Envelope Segment' if title is None else title)
        plt.show()

    def _reciprocal(self):
        assert self.start_level * self.end_level > 0, "Cannot divide by EnvelopeSegment that crosses zero"
        return self.from_endpoints_and_halfway_level(self.start_time, self.end_time,
                                                     1 / self.start_level, 1 / self.end_level,
                                                     1 / self.value_at((self.start_time + self.end_time) / 2))

    def __neg__(self):
        return EnvelopeSegment(self.start_time, self.end_time,
                               -self.start_level, -self.end_level, self.curve_shape)

    def __add__(self, other):
        from .envelope import Envelope
        if isinstance(other, numbers.Number):
            out = self.clone()
            out.shift_vertical(other)
            return out
        elif isinstance(other, EnvelopeSegment):
            if self.start_time == other.start_time and self.end_time == other.end_time:
                segments = _make_envelope_segments_from_function(lambda t: self.value_at(t) + other.value_at(t),
                                                                 self.start_time, self.end_time)
                if len(segments) == 1:
                    return segments[0]
                else:
                    return Envelope(segments)
            else:
                raise ValueError("EnvelopeSegments can only be added if they have the same time range.")
        else:
            raise TypeError("Can only add EnvelopeSegment to a constant or another EnvelopeSegment")

    def __radd__(self, other):
        return self.__add__(other)

    def __sub__(self, other):
        return self.__add__(-other)

    def __rsub__(self, other):
        return self.__radd__(-other)

    def __mul__(self, other):
        from .envelope import Envelope
        if isinstance(other, numbers.Number):
            out = self.clone()
            out.scale_vertical(other)
            return out
        elif isinstance(other, EnvelopeSegment):
            if self.start_time == other.start_time and self.end_time == other.end_time:
                segments = _make_envelope_segments_from_function(lambda t: self.value_at(t) * other.value_at(t),
                                                                 self.start_time, self.end_time)
                if len(segments) == 1:
                    return segments[0]
                else:
                    return Envelope(segments)
            else:
                raise ValueError("EnvelopeSegments can only be added if they have the same time range.")
        else:
            raise TypeError("Can only multiply EnvelopeSegment with a constant or another EnvelopeSegment")

    def __rmul__(self, other):
        return self.__mul__(other)

    def __truediv__(self, other):
        return self * (1 / other)

    def __rtruediv__(self, other):
        return self._reciprocal() * other

    def __contains__(self, t):
        # checks if the given time is contained within this envelope segment
        # maybe this is silly, but it seemed a little convenient
        return self.start_time <= t < self.end_time

    def __repr__(self):
        return "EnvelopeSegment({}, {}, {}, {}, {})".format(self.start_time, self.end_time, self.start_level,
                                                            self.end_level, self.curve_shape)
