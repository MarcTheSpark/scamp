def _make_envelope_segments_from_function(function, domain_start, domain_end, resolution_multiple=1,
                                          key_point_precision=100, key_point_iterations=5):
    from .envelope_segment import EnvelopeSegment
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
