import logging
from copy import deepcopy


class ParameterCurve:

    def __init__(self, levels, durations, curvatures):
        if len(levels) == len(durations):
            # there really should be one more level than duration, but if there's the same
            # number, we assume that they intend the last level to stay where it is
            levels = list(levels) + [levels[-1]]
        if len(levels) != len(durations) + 1:
            raise ValueError("Inconsistent number of levels and durations given.")
        if len(curvatures) > len(levels) - 1:
            logging.warning("Too many curvature values given to ParameterCurve. Discarding extra.")
        if len(curvatures) < len(levels) - 1:
            logging.warning("Too few curvature values given to ParameterCurve. Assuming linear for remainder.")
            curvatures += [1] * (len(levels) - 1 - len(curvatures))
        for c in curvatures:
            assert (c > 0), "Curvature values cannot be negative!"

        self.levels = levels
        self.durations = durations
        self.curvatures = curvatures

    @classmethod
    def from_levels(cls, levels):
        # just given levels, so we linearly interpolate segments of equal length
        durations = [1.0 / (len(levels) - 1)] * (len(levels) - 1)
        curves = [1.0] * (len(levels) - 1)
        return cls(levels, durations, curves)

    @classmethod
    def from_levels_and_durations(cls, levels, durations):
        # given levels and durations, so we assume linear curvature for every segment
        return cls(levels, durations, [1.0] * (len(levels) - 1))

    @classmethod
    def from_list(cls, constructor_list):
        # converts from a list that may contain just levels, may have levels and durations, and may have everything
        # a input of [1, 0.5, 0.3] is interpreted as evenly spaced levels
        # an input of [[1, 0.5, 0.3], [0.2, 0.8]] is interpreted as levels and durations
        # an input of [[1, 0.5, 0.3], [0.2, 0.8], [2, 0.5]]is interpreted as levels, durations, and curvatures
        if hasattr(constructor_list[0], "__len__"):
            # we were given levels and durations, and possibly curvature values
            if len(constructor_list) == 2:
                # given levels and durations
                return ParameterCurve.from_levels_and_durations(constructor_list[0], constructor_list[1])
            elif len(constructor_list) >= 3:
                # given levels, durations, and curvature values
                return cls(constructor_list[0], constructor_list[1], constructor_list[2])
        else:
            # just given levels
            return ParameterCurve.from_levels(constructor_list)

    def normalize_to_duration(self, desired_duration, in_place=True):
        out = self if in_place else deepcopy(self)
        current_duration = sum(out.durations)
        if current_duration != desired_duration:
            ratio = desired_duration / current_duration
            for i, dur in enumerate(out.durations):
                out.durations[i] = dur * ratio
        return out

    def value_at(self, t):
        if t < 0:
            return self.levels[-1]
        for i, segment_length in enumerate(self.durations):
            if t > segment_length:
                t -= segment_length
            else:
                segment_progress = (t / segment_length) ** self.curvatures[i]
                return self.levels[i] * (1 - segment_progress) + self.levels[i+1] * segment_progress
        return self.levels[-1]

    def max_level(self):
        return max(self.levels)

    def to_json(self):
        duration_unnecessary = all(x == self.durations[0] for x in self.durations)
        curvature_unnecessary = all(x == 1 for x in self.curvatures)
        if duration_unnecessary and curvature_unnecessary:
            return self.levels
        elif curvature_unnecessary:
            return [self.levels, self.durations]
        else:
            return [self.levels, self.durations, self.curvatures]

    @staticmethod
    def from_json(json_list):
        return ParameterCurve.from_list(json_list)

    def __repr__(self):
        return "ParameterCurve({}, {}, {})".format(self.levels, self.durations, self.curvatures)
