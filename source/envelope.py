import math
from copy import deepcopy
import numbers


# --------------------------------------------------- Utilities ----------------------------------------------------


def _get_extrema_and_inflection_points(function, domain_start, domain_end, resolution=100, iterations=5,
                                       include_endpoints=True, return_on_first_point=False):
    assert resolution >= 10 or iterations == 1, "Resolution should be at least 10 if iteration is being used"
    key_points = []
    value = None
    first_difference = None
    second_difference = None
    step = (domain_end - domain_start) / resolution
    for x in range(0, resolution):
        t = domain_start + x * step
        this_value = function(t)

        if value is not None:
            # some rounding is necessary to avoid floating point inaccuracies from creating false sign changes
            this_difference = round(this_value - value, 10)
            if first_difference is not None:
                # check if first difference changes sign in the first derivative
                if this_difference * first_difference < 0:
                    # there's been a change of sign, so it's a local min or max. split here
                    new_point = _get_extrema_and_inflection_points(
                        function, t - 2 * step, t + 2 * step, max(10, int(resolution / 2)), iterations - 1,
                        include_endpoints=False, return_on_first_point=True
                    ) if iterations > 1 else t

                    if return_on_first_point:
                        return new_point
                    else:
                        key_points.append(new_point)

                this_second_difference = round(this_difference - first_difference, 10)

                if second_difference is not None:
                    # check if second difference changes sign
                    if this_second_difference * second_difference < 0:
                        # there's been a change of sign, so it's an inflection point. split here
                        if t not in key_points:
                            new_point = _get_extrema_and_inflection_points(
                                function, t - 2 * step, t + 2 * step, max(10, int(resolution / 2)), iterations - 1,
                                include_endpoints=False, return_on_first_point=True
                            ) if iterations > 1 else t

                            if return_on_first_point:
                                return new_point
                            else:
                                key_points.append(new_point)
                second_difference = this_second_difference
            first_difference = this_difference
        value = this_value

    if return_on_first_point:
        # something has gone a little wrong, because we did an extra iteration to find the key point more exactly,
        # but we didn't get any closer. So just return the average.
        return (domain_start + domain_end) / 2

    if include_endpoints:
        return [domain_start] + key_points + [domain_end]
    else:
        return key_points


def _make_envelope_segments_from_function(function, domain_start, domain_end, resolution_multiple=1,
                                          key_point_precision=100, key_point_iterations=5):
    assert isinstance(resolution_multiple, int) and resolution_multiple > 0
    key_points = _get_extrema_and_inflection_points(function, domain_start, domain_end,
                                                    key_point_precision, key_point_iterations)
    if resolution_multiple > 1:
        key_points = [l + k * (r - l) / resolution_multiple
                      for l, r in zip(key_points[:-1], key_points[1:])
                      for k in range(resolution_multiple)] + [key_points[-1]]

    segments = []
    i = 0
    while i < len(key_points) - 1:
        segment_start = key_points[i]
        segment_end = key_points[i + 1]
        halfway_point = (segment_start + segment_end) / 2
        segment_start_value = function(segment_start)
        segment_end_value = function(segment_end)
        segment_halfway_value = function(halfway_point)

        # we're trying to split at the min / max locations to get monotonic segments
        # in case we get a segment that is neither strictly monotonic not constant,
        # we can just split it straight down the middle
        is_strictly_monotonic = min(segment_start_value, segment_end_value) < segment_halfway_value < \
                                max(segment_start_value, segment_end_value)
        is_constant = segment_start_value == segment_halfway_value == segment_end_value
        if not (is_strictly_monotonic or is_constant):
            # if we are splitting it, add a key point halfway and try again without incrementing
            key_points.insert(i + 1, halfway_point)
            continue

        segments.append(EnvelopeSegment.from_endpoints_and_halfway_level(
            segment_start, segment_end,
            segment_start_value, segment_end_value, segment_halfway_value
        ))
        i += 1

    return segments


# --------------------------------------------- Main Envelope Class ------------------------------------------------


class Envelope:

    def __init__(self, segments=None):
        """
        Implements an envelope using exponential curve segments. Initialization happens outside
        of the constructor for smoother subclassing; this way all of the class methods work correctly
        on derived classes like TempoEnvelope.
        """
        if segments is None:
            self.segments = None
            self.initialize()
        else:
            self.segments = segments

    def initialize(self, levels=(0, 0), durations=(0,), curve_shapes=None, offset=0):
        """
        A curve shape of zero is linear, > 0 changes late, and < 0 changes early. Strings containing "exp" will also be
        evaluated, with "exp" standing for the shape that will produce constant proportional change per unit time.

        :param levels: at least 1 level should be given (if only one level is given, it is automatically doubled so as
        to be the start and end level of the one segment of the curve)
        :param durations: there should be one fewer duration than level given
        :param curve_shapes: there should be one fewer than the number of levels. If None, all segments are linear
        :param offset: starts Envelope from somewhere other than zero
        """
        if not hasattr(levels, "__len__"):
            levels = (levels,)
        assert hasattr(levels, "__len__") and hasattr(durations, "__len__") \
               and (curve_shapes is None or hasattr(curve_shapes, "__len__"))
        assert len(levels) > 0, "At least one level is needed to construct an envelope."
        if len(levels) == 1:
            levels = levels + levels
        assert len(durations) == len(levels) - 1, "Inconsistent number of levels and durations given."
        if curve_shapes is None:
            curve_shapes = [0] * (len(levels) - 1)

        self.segments = Envelope._construct_segments_list(levels, durations, curve_shapes, offset)
        return self

    @staticmethod
    def _construct_segments_list(levels, durations, curve_shapes, offset=0):
        segments = []
        t = offset
        for i in range(len(levels) - 1):
            segments.append(EnvelopeSegment(t, t + durations[i], levels[i], levels[i + 1], curve_shapes[i]))
            t += durations[i]
        return segments

    # ---------------------------- Class methods --------------------------------

    @classmethod
    def from_levels_and_durations(cls, levels=(0, 0), durations=(0,), curve_shapes=None, offset=0):
        """
        Construct an envelope from levels, durations, and optionally curve shapes
        :param levels: the levels of the curve
        :param durations: the durations of the curve
        :param curve_shapes: the curve shape values (optional)
        :param offset: starts curve from somewhere other than zero
        :return: an Envelope constructed accordingly
        """
        return cls().initialize(levels, durations, curve_shapes, offset)

    @classmethod
    def from_levels(cls, levels, length=1.0, offset=0):
        """
        Construct an envelope from levels alone, normalized to the given length
        :param levels: the levels of the curve
        :param length: the total length of the curve, divided evenly amongst the levels
        :param offset: starts curve from somewhere other than zero
        :return: an Envelope constructed accordingly
        """
        assert len(levels) > 0, "At least one level is needed to construct an envelope."
        if len(levels) == 1:
            levels = list(levels) * 2
        # just given levels, so we linearly interpolate segments of equal length
        durations = [length / (len(levels) - 1)] * (len(levels) - 1)
        curves = [0.0] * (len(levels) - 1)
        return cls.from_levels_and_durations(levels, durations, curves, offset)

    @classmethod
    def from_list(cls, constructor_list):
        """
        Construct an envelope from a list that can take a number of formats
        :param constructor_list: either a flat list that just contains levels, or a list of lists either of the form
         [levels_list, total_duration], [levels_list, durations_list] or [levels_list, durations_list, curve_shape_list]
         for example:
         - an input of [1, 0.5, 0.3] is interpreted as evenly spaced levels with a total duration of 1
         - an input of [[1, 0.5, 0.3], 3.0] is interpreted as levels and durations with a total duration of e.g. 3.0
         - an input of [[1, 0.5, 0.3], [0.2, 0.8]] is interpreted as levels and durations
         - an input of [[1, 0.5, 0.3], [0.2, 0.8], [2, 0.5]] is interpreted as levels, durations, and curvatures
        :return: an Envelope constructed accordingly
        """
        assert hasattr(constructor_list, "__len__")
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

    @classmethod
    def from_points(cls, *points):
        """
        Construct an envelope from points, each of which is of the form (time, value) or (time, value, curve_shape)
        :param points: list of points
        :return an Envelope constructed accordingly
        """
        assert all(len(point) >= 2 for point in points)
        points = tuple(sorted(points, key=lambda point: point[0]))
        if all(len(point) == 2 for point in points):
            curve_shapes = None
        else:
            curve_shapes = tuple(points[i][2] if len(points[i]) > 2 else 0 for i in range(len(points)))
        return cls.from_levels_and_durations(tuple(point[1] for point in points),
                                             tuple(points[i + 1][0] - points[i][0] for i in range(len(points) - 1)),
                                             curve_shapes=curve_shapes, offset=points[0][0])

    @classmethod
    def release(cls, duration, start_level=1, curve_shape=None):
        """
        Construct an simple decaying envelope
        :param duration: total decay length
        :param start_level: level decayed from
        :param curve_shape: shape of the curve
        :return: an Envelope constructed accordingly
        """
        curve_shapes = (curve_shape,) if curve_shape is not None else None
        return cls.from_levels_and_durations((start_level, 0), (duration,), curve_shapes=curve_shapes)

    @classmethod
    def ar(cls, attack_length, release_length, peak_level=1, attack_shape=None, release_shape=None):
        """
        Construct an attack/release envelope
        :param attack_length: rise time
        :param release_length: release time
        :param peak_level: level reached after attack and before release
        :param attack_shape: sets curve shape for attack portion of the curve
        :param release_shape: sets curve shape for release portion of the curve
        :return: an Envelope constructed accordingly
       """
        curve_shapes = None if attack_shape is release_shape is None else \
            (0 if attack_shape is None else attack_shape, 0 if release_shape is None else release_shape)
        return cls.from_levels_and_durations((0, peak_level, 0), (attack_length, release_length),
                                             curve_shapes=curve_shapes)

    @classmethod
    def asr(cls, attack_length, sustain_level, sustain_length, release_length, attack_shape=None, release_shape=None):
        """
        Construct an attack/sustain/release envelope
        :param attack_length: rise time
        :param sustain_level: sustain level reached after attack and before release
        :param sustain_length: length of sustain portion of curve
        :param release_length: release time
        :param attack_shape: sets curve shape for attack portion of the curve
        :param release_shape: sets curve shape for release portion of the curve
        :return: an Envelope constructed accordingly
       """
        curve_shapes = None if attack_shape is release_shape is None else \
            (0 if attack_shape is None else attack_shape, 0, 0 if release_shape is None else release_shape)
        return cls.from_levels_and_durations((0, sustain_level, sustain_level, 0),
                                             (attack_length, sustain_length, release_length),
                                             curve_shapes=curve_shapes)

    @classmethod
    def adsr(cls, attack_length, attack_level, decay_length, sustain_level, sustain_length, release_length,
             attack_shape=None, decay_shape=None, release_shape=None):
        """
        Construct a standard attack/decay/sustain/release envelope
        :param attack_length: rise time
        :param attack_level: level reached after attack before decay
        :param decay_length: length of decay portion of the curve
        :param sustain_level: sustain level reached after decay and before release
        :param sustain_length: length of sustain portion of curve
        :param release_length: release time
        :param attack_shape: sets curve shape for attack portion of the curve
        :param decay_shape: sets curve shape for decay portion of the curve
        :param release_shape: sets curve shape for release portion of the curve
        :return: an Envelope constructed accordingly
       """
        curve_shapes = None if attack_shape is decay_shape is release_shape is None else \
            (0 if attack_shape is None else attack_shape, 0 if decay_shape is None else decay_shape,
             0, 0 if release_shape is None else release_shape)
        return cls.from_levels_and_durations((0, attack_level, sustain_level, sustain_level, 0),
                                             (attack_length, decay_length, sustain_length, release_length),
                                             curve_shapes=curve_shapes)

    @classmethod
    def from_function(cls, function, domain_start=0, domain_end=1, resolution_multiple=2,
                      key_point_precision=100, key_point_iterations=5):
        """
        Approximation of arbitrary function as an envelope of exponential segments.
        By default, the function is split at local extrema and inflection points found through a pretty
        unsophisticated numerical process. The precision of this numerical process is set through the
        key_point_precision and key_point_iterations arguments. If resolution_multiple is set greater than 1
        then extra key points are added in between those key points to improve curve fit.
        :return: an Envelope
        """
        return cls(_make_envelope_segments_from_function(function, domain_start, domain_end, resolution_multiple,
                                                         key_point_precision, key_point_iterations))

    # ---------------------------- Various Properties --------------------------------

    def length(self):
        if len(self.segments) == 0:
            return 0
        return self.segments[-1].end_time - self.segments[0].start_time

    def start_time(self):
        return self.offset

    def end_time(self):
        return self.segments[-1].end_time

    def start_level(self):
        return self.segments[0].start_level

    def end_level(self):
        return self.segments[-1].end_level

    def max_level(self, t_range=None):
        if t_range is None:
            # checking over the entire range, so that's easy
            return max(segment.max_level() for segment in self.segments)
        else:
            # checking over the range (t1, t2), so look at the values at those endpoints and any anchor points between
            assert hasattr(t_range, "__len__") and len(t_range) == 2 and t_range[0] < t_range[1]
            t1, t2 = t_range
            points_to_check = [self.value_at(t1), self.value_at(t2)]
            for segment in self.segments:
                if t1 <= segment.start_time <= t2:
                    points_to_check.append(segment.start_level)
                if t1 <= segment.end_time <= t2:
                    points_to_check.append(segment.end_level)
            return max(points_to_check)

    def average_level(self):
        return self.integrate_interval(self.start_time(), self.start_time() + self.length()) / self.length()

    def max_absolute_slope(self):
        return max(segment.max_absolute_slope() for segment in self.segments)

    @property
    def levels(self):
        return tuple(segment.start_level for segment in self.segments) + (self.end_level(),)

    @property
    def durations(self):
        return tuple(segment.duration for segment in self.segments)

    @property
    def times(self):
        return tuple(segment.start_time for segment in self.segments) + (self.end_time(),)

    @property
    def curve_shapes(self):
        return tuple(segment.curve_shape for segment in self.segments)

    @property
    def offset(self):
        return self.segments[0].start_time

    # ----------------------- Insertion of new control points --------------------------

    def insert(self, t, level, curve_shape_in=0, curve_shape_out=0):
        """
        Insert a curve point at time t, and set the shape of the curve into and out of it
        """
        if t < self.start_time():
            self.prepend_segment(level, self.start_time() - t, curve_shape_out)
        if t > self.end_time():
            # adding a point after the curve
            self.append_segment(level, t - self.end_time(), curve_shape_in)
            return
        else:
            for i, segment in enumerate(self.segments):
                if segment.start_time < t < segment.end_time:
                    # we are inside an existing segment, so we break it in two
                    # save the old segment end time and level, since these will be the end of the second half
                    end_time = segment.end_time
                    end_level = segment.end_level
                    # change the first half to end at t and have the given shape
                    segment.end_time = t
                    segment.curve_shape = curve_shape_in
                    segment.end_level = level
                    new_segment = EnvelopeSegment(t, end_time, level, end_level, curve_shape_out)
                    self.segments.insert(i + 1, new_segment)
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
        Insert another curve point at the given time, without changing the shape of the curve
        """
        if t < self.start_time():
            # we set tolerance to -1 here to ensure that the initial segement doesn't simply get extended
            # we actually want an extra control point, redundant or not
            self.prepend_segment(self.start_level(), self.start_time() - t, tolerance=-1)
            return
        if t > self.end_time():
            # tolerance set to -1 for same reason as above
            self.append_segment(self.end_level(), t - self.end_time(), tolerance=-1)
            return
        if t == self.start_time() or t == self.end_time():
            return
        for i, segment in enumerate(self.segments):
            if t == segment.start_time:
                return
            if t in segment:
                # this is the case that matters; t is within one of the segments
                part1, part2 = segment.split_at(t)
                self.segments.insert(i + 1, part2)

    # ----------------------- Appending / removing segments --------------------------

    def append_segment(self, level, duration, curve_shape=0.0, tolerance=0):
        """
        Append a segment to the end of the curve ending at level and lasting for duration.
        If we're adding a linear segment to a linear segment, then we extend the last linear segment
        instead of adding a new one if the level is within tolerance of where the last one was headed
        :return:
        """
        if self.segments[-1].duration == 0:
            # the previous segment has no length. Are we also adding a segment with no length?
            if duration == 0:
                # If so, replace the end level of the existing zero-length segment
                self.segments[-1].end_level = level
            else:
                # okay, we're adding a segment with length
                # did the previous segment actually change the level?
                if self.segments[-1].end_level != self.segments[-1].start_level:
                    # If so we keep it and add a new one
                    self.segments.append(EnvelopeSegment(self.end_time(), self.end_time() + duration,
                                                         self.end_level(), level, curve_shape))
                else:
                    # if not, just modify the previous segment into what we want
                    self.segments[-1].end_level = level
                    self.segments[-1].end_time = self.end_time() + duration
                    self.segments[-1].curve_shape = curve_shape
        elif self.segments[-1].curve_shape == 0 and curve_shape == 0 and \
                abs(self.segments[-1].value_at(self.end_time() + duration,
                                               clip_at_boundary=False) - level) <= tolerance:
            # we're adding a point that would be a perfect continuation of the previous linear segment
            # (could do this for non-linear, but it's probably not worth the effort)
            self.segments[-1].end_time = self.length() + duration
            self.segments[-1].end_level = level
        else:
            self.segments.append(EnvelopeSegment(self.end_time(), self.end_time() + duration,
                                                 self.end_level(), level, curve_shape))

    def prepend_segment(self, level, duration, curve_shape=0.0, tolerance=0):
        """
        Prepend a segment to the beginning of the curve, starting at level and lasting for duration.
        If we're adding a linear segment to a linear segment, then we extend the last linear segment
        instead of adding a new one if the level is within tolerance of where the last one was headed
        :return:
        """
        if self.segments[0].duration == 0:
            # the first segment has no length. Are we also prepending a segment with no length?
            if duration == 0:
                # If so, replace the start level of the existing zero-length segment
                self.segments[0].start_level = level
            else:
                # okay, we're adding a segment with length
                # does the first segment actually change the level?
                if self.segments[-1].end_level != self.segments[-1].start_level:
                    # If so we keep it and add a new one before it
                    self.segments.insert(0, EnvelopeSegment(self.start_time() - duration, self.start_time(),
                                                            level, self.start_level(), curve_shape))
                else:
                    # if not, just modify the previous segment into what we want
                    self.segments[0].start_level = level
                    self.segments[0].start_time = self.start_time() - duration
                    self.segments[0].curve_shape = curve_shape
        elif self.segments[0].curve_shape == 0 and curve_shape == 0 and \
                abs(self.segments[0].value_at(self.start_time() - duration,
                                              clip_at_boundary=False) - level) <= tolerance:
            # we're adding a point that would be a perfect extrapolation of the initial linear segment
            # (could do this for non-linear, but it's probably not worth the effort)
            self.segments[0].start_time = self.start_time() - duration
            self.segments[0].start_level = level
        else:
            self.segments.insert(0, EnvelopeSegment(self.start_time() - duration, self.start_time(),
                                                    level, self.start_level(), curve_shape))

    def pop_segment(self):
        if len(self.segments) == 1:
            if self.segments[0].end_time != self.segments[0].start_time or \
                    self.segments[0].end_level != self.segments[0].start_level:
                self.segments[0].end_time = self.segments[0].start_time
                self.segments[0].end_level = self.segments[0].start_level
                return
            else:
                raise IndexError("Cannot pop from empty Envelope")
        return self.segments.pop()

    def pop_segment_from_start(self):
        if len(self.segments) == 1:
            if self.segments[0].end_time != self.segments[0].start_time or \
                    self.segments[0].end_level != self.segments[0].start_level:
                self.segments[0].start_time = self.segments[0].end_time
                self.segments[0].start_level = self.segments[0].end_level
                return
            else:
                raise IndexError("Cannot pop from empty Envelope")
        return self.segments.pop(0)

    def remove_segments_after(self, t):
        if t < self.start_time():
            while True:
                try:
                    self.pop_segment()
                except IndexError:
                    break
        for segment in self.segments:
            if t == segment.start_time:
                while self.end_time() > t:
                    self.pop_segment()
                return
            elif segment.start_time < t < segment.end_time:
                self.insert_interpolated(t)
                while self.end_time() > t:
                    self.pop_segment()
                return

    def remove_segments_before(self, t):
        if t > self.end_time():
            while True:
                try:
                    self.pop_segment_from_start()
                except IndexError:
                    break
        for segment in reversed(self.segments):
            if t == segment.end_time:
                while self.start_time() < t:
                    self.pop_segment_from_start()
                return
            elif segment.start_time < t < segment.end_time:
                self.insert_interpolated(t)
                while self.start_time() < t:
                    self.pop_segment_from_start()
                return

    # ------------------------ Interpolation, Integration --------------------------

    def value_at(self, t, from_left=False):
        """
        The most important method for an Envelope: what's it's value at a given time
        :param t: the time
        :param from_left: if true, get the limit as we approach t from the left. In the case of a zero-length segment,
        which suddenly changes the value, this tells us what the value was right before the jump.
        :return: the value of this Envelope at t
        """
        if t < self.start_time():
            return self.start_level()
        for segment in self.segments:
            if t in segment or from_left and t == segment.end_time:
                return segment.value_at(t)
        return self.end_level()

    def integrate_interval(self, t1, t2):
        if t1 == t2:
            return 0
        if t2 < t1:
            return -self.integrate_interval(t2, t1)
        if t1 < self.start_time():
            return (self.start_time() - t1) * self.segments[0].start_level + \
                   self.integrate_interval(self.start_time(), t2)
        if t2 > self.end_time():
            return (t2 - self.end_time()) * self.end_level() + self.integrate_interval(t1, self.end_time())
        # now that the edge conditions are covered, we just add up the segment integrals
        integral = 0

        # if there are a lot of segments, we bisect the list repeatedly until we get close t
        start_index = 0
        while True:
            new_start_index = start_index + (len(self.segments) - start_index) // 2
            if self.segments[new_start_index].end_time < t1 and len(self.segments) - new_start_index > 3:
                start_index = new_start_index
            else:
                break

        for segment in self.segments[start_index:]:
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

    # -------------------------------- Utilities --------------------------------

    def normalize_to_duration(self, desired_duration, in_place=True):
        out = self if in_place else deepcopy(self)
        if self.length() != desired_duration:
            ratio = desired_duration / self.length()
            for segment in out.segments:
                segment.start_time = (segment.start_time - self.start_time()) * ratio + self.start_time()
                segment.end_time = (segment.end_time - self.start_time()) * ratio + self.start_time()
        return out

    def local_extrema(self, include_saddle_points=False):
        """
        Returns a list of the times where the curve changes direction.
        """
        local_extrema = []
        last_direction = 0
        for segment in self.segments:
            if segment.end_level > segment.start_level:
                direction = 1
            elif segment.end_level < segment.start_level:
                direction = -1
            else:
                # if this segment was static, then keep the direction we had going in
                direction = last_direction
                if include_saddle_points and segment.start_time not in local_extrema:
                    local_extrema.append(segment.start_time)
            if last_direction * direction < 0 and segment.start_time not in local_extrema:
                # we changed sign, since
                local_extrema.append(segment.start_time)
            last_direction = direction
        return local_extrema

    def split_at(self, t, change_original=False):
        """
        Splits the Envelope at one or several points and returns a tuple of the pieces
        :param t: either the time t or a tuple/list of times t at which to split the curve
        :param change_original: if true, the original Envelope gets turned into the first of the returned tuple
        :return: tuple of Envelopes representing the pieces this has been split into
        """
        to_split = self if change_original else Envelope([x.clone() for x in self.segments])

        # if t is a tuple or list, we split at all of those times and return len(t) + 1 segments
        # This is implemented recursively. If len(t) is 1, t is replaced by t[0]
        # If len(t) > 1, then we sort and set aside t[1:] as remaining splits to do on the second half
        # and set t to t[0]. Note that we subtract t[0] from each of t[1:] to shift it to start from 0
        remaining_splits = None
        if hasattr(t, "__len__"):
            # ignore all split points that are outside this Envelope's range
            t = [x for x in t if to_split.start_time() <= x <= to_split.end_time()]
            if len(t) == 0:
                # if no usable points are left we're done (note we always return a tuple for consistency)
                return to_split,

            if len(t) > 1:
                t = list(t)
                t.sort()
                remaining_splits = [x - t[0] for x in t[1:]]
            t = t[0]

        # cover the case of trying to split outside of the Envelope's range
        # (note we always return a tuple for consistency)
        if not to_split.start_time() < t < to_split.end_time():
            return to_split,

        # Okay, now we go ahead with a single split at time t
        to_split.insert_interpolated(t)
        for i, segment in enumerate(to_split.segments):
            if segment.start_time == t:
                second_half = Envelope(to_split.segments[i:])
                to_split.segments = to_split.segments[:i]
                for second_half_segment in second_half.segments:
                    second_half_segment.start_time -= t
                    second_half_segment.end_time -= t
                break

        if remaining_splits is None:
            return to_split, second_half
        else:
            return to_split, second_half.split_at(remaining_splits, change_original=True)

    def to_json(self):
        json_dict = {'levels': self.levels}

        if all(x == self.durations[0] for x in self.durations):
            json_dict['length'] = self.length()
        else:
            json_dict['durations'] = self.durations

        if any(x != 0 for x in self.curve_shapes):
            json_dict['curve_shapes'] = self.curve_shapes

        if self.offset != 0:
            json_dict['offset'] = self.offset

        return json_dict

    @classmethod
    def from_json(cls, json_dict):
        curve_shapes = None if 'curve_shapes' not in json_dict else json_dict['curve_shapes']
        offset = 0 if 'offset' not in json_dict else json_dict['offset']
        if 'length' in json_dict:
            return cls.from_levels(json_dict['levels'], json_dict['length'], offset)
        else:
            return cls.from_levels_and_durations(json_dict['levels'], json_dict['durations'],
                                                 curve_shapes, offset)

    def save_to_json(self, file_path):
        with open(file_path, "w") as file:
            json.dump(self.to_json(), file, sort_keys=True, indent=4)

    @classmethod
    def load_from_json(cls, file_path):
        with open(file_path, "r") as file:
            return cls.from_json(json.load(file))

    def is_shifted_version_of(self, other):
        assert isinstance(other, Envelope)
        return all(x.is_shifted_version_of(y) for x, y in zip(self.segments, other.segments))

    def shift_vertical(self, amount):
        assert isinstance(amount, numbers.Number)
        for segment in self.segments:
            segment.shift_vertical(amount)
        return self

    def scale_vertical(self, amount):
        assert isinstance(amount, numbers.Number)
        for segment in self.segments:
            segment.scale_vertical(amount)
        return self

    def shift_horizontal(self, amount):
        assert isinstance(amount, numbers.Number)
        for segment in self.segments:
            segment.shift_horizontal(amount)
        return self

    def scale_horizontal(self, amount):
        assert isinstance(amount, numbers.Number)
        for segment in self.segments:
            segment.scale_horizontal(amount)
        return self

    def get_graphable_point_pairs(self, resolution=25):
        x_values = []
        y_values = []
        for i, segment in enumerate(self.segments):
            # only include the endpoint on the very last segment, since otherwise there would be repeats
            segment_x_values, segment_y_values = segment.get_graphable_point_pairs(
                resolution=resolution, endpoint=(i == len(self.segments) - 1)
            )
            x_values.extend(segment_x_values)
            y_values.extend(segment_y_values)
        return x_values, y_values

    def show_plot(self, title=None, resolution=25, show_segment_divisions=True):
        import matplotlib.pyplot as plt
        fig, ax = plt.subplots()
        ax.plot(*self.get_graphable_point_pairs(resolution))
        if show_segment_divisions:
            ax.plot(self.times, self.levels, 'o')
        ax.set_title('Graph of Envelope' if title is None else title)
        plt.show()

    @staticmethod
    def _apply_binary_operation_to_pair(envelope1, envelope2, binary_function):
        envelope1 = deepcopy(envelope1)
        envelope2 = deepcopy(envelope2)
        for t in set(envelope1.times + envelope2.times):
            envelope1.insert_interpolated(t)
            envelope2.insert_interpolated(t)
        result_segments = []
        for s1, s2 in zip(envelope1.segments, envelope2.segments):
            this_segment_result = binary_function(s1, s2)
            # when we add or multiply two EnvelopeSegments, we might get an EnvelopeSegment if it's simple
            # or we might get an Envelope if the result is best represented by multiple segments
            if isinstance(this_segment_result, Envelope):
                # if it's an envelope, append all of it's segments
                result_segments.extend(this_segment_result.segments)
            else:
                # otherwise, it should just be a segment
                assert isinstance(this_segment_result, EnvelopeSegment)
                result_segments.append(this_segment_result)
        return Envelope(result_segments)

    def _reciprocal(self):
        assert all(x > 0 for x in self.levels) or all(x < 0 for x in self.levels), \
            "Cannot divide by Envelope that crosses zero"
        return Envelope([segment._reciprocal() for segment in self.segments])

    def __add__(self, other):
        if isinstance(other, numbers.Number):
            return Envelope([segment + other for segment in self.segments])
        elif isinstance(other, Envelope):
            return Envelope._apply_binary_operation_to_pair(self, other, lambda a, b: a + b)
        else:
            raise ValueError("Envelope can only be added to a constant or another envelope")

    def __radd__(self, other):
        return self.__add__(other)

    def __neg__(self):
        return Envelope([-segment for segment in self.segments])

    def __sub__(self, other):
        return self.__add__(-other)

    def __rsub__(self, other):
        return self.__radd__(-other)

    def __mul__(self, other):
        if isinstance(other, numbers.Number):
            return Envelope([segment * other for segment in self.segments])
        elif isinstance(other, Envelope):
            return Envelope._apply_binary_operation_to_pair(self, other, lambda a, b: a * b)
        else:
            raise ValueError("Envelope can only be multiplied by a constant or another envelope")

    def __rmul__(self, other):
        return self.__mul__(other)

    def __truediv__(self, other):
        return self * (1 / other)

    def __rtruediv__(self, other):
        return self._reciprocal() * other

    def __repr__(self):
        return "Envelope({}, {}, {}, {})".format(self.levels, self.durations, self.curve_shapes, self.offset)


# ------------------------------------------ Envelope Segment Class ------------------------------------------------


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
        import matplotlib.pyplot as plt
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
