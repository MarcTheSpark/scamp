from expenvelope import Envelope
import math

# Ways of constructing Envelopes

envelope_from_levels = Envelope.from_levels((1.0, 0.2, 0.6, 0), length=3)
envelope_from_levels.show_plot("Envelope from levels alone")

envelope_from_levels_and_durations = Envelope.from_levels_and_durations((1.0, 0.2, 0.6, 0), (2.0, 1.0, 3.0))
envelope_from_levels_and_durations.show_plot("Envelope from levels and durations")

envelope_from_levels_and_durations_with_curve_shapes = Envelope.from_levels_and_durations(
    (1.0, 0.2, 0.6, 0), (2.0, 1.0, 3.0), curve_shapes=(2, 2, -3)
)
envelope_from_levels_and_durations_with_curve_shapes.show_plot("Envelope with curve shapes")

envelope_from_points = Envelope.from_points((-1, 5), (1, 6), (5, -2))
envelope_from_points.show_plot("Envelope from points")

envelope_from_points_with_curve_shapes = Envelope.from_points((-1, 5, -3), (1, 6, 2), (5, -2))
envelope_from_points_with_curve_shapes.show_plot("Envelope from points with curve shapes")

envelope_from_list1 = Envelope.from_list([3, 6, 2, 0])  # just levels
envelope_from_list1.show_plot("Envelope from list (just levels)")

envelope_from_list2 = Envelope.from_list([[3, 6, 2, 0], 7])  # levels and total duration
envelope_from_list2.show_plot("Envelope from list (levels and total duration)")

envelope_from_list3 = Envelope.from_list([[3, 6, 2, 0], [2, 0.5, 5]])  # levels and segment durations
envelope_from_list3.show_plot("Envelope from list (levels and durations)")

envelope_from_list4 = Envelope.from_list([[3, 6, 2, 0], [2, 0.5, 5], [3, 0, -3]])  # levels, durations and curve shapes
envelope_from_list4.show_plot("Envelope from list (levels, durations and curve shapes)")

envelope_from_function = Envelope.from_function(lambda x: math.sin(x), -2, 7)
envelope_from_function.show_plot("Envelope from function (sine)")

release_envelope = Envelope.release(3, curve_shape=-2)
release_envelope.show_plot("Release envelope")

attack_release_envelope = Envelope.ar(0.1, 2, release_shape=-3)
attack_release_envelope.show_plot("Attack / release envelope")

attack_sustain_release_envelope = Envelope.asr(1, 0.8, 4, 2, attack_shape=-4)
attack_sustain_release_envelope.show_plot("ASR envelope")

adsr_envelope = Envelope.adsr(0.2, 1.0, 0.3, 0.7, 3.0, 1.0, decay_shape=-2, release_shape=3)
adsr_envelope.show_plot("ADSR envelope")

# Arithmetic with Envelopes:
# Approximates as best as possible the result of function addition / multiplication / division
# Since the resulting functions are often not piecewise exponential, we break the result apart at local min / max
# and points of inflection and try to fit exponentials to each of the resulting segments

a = Envelope.adsr(0.2, 1.0, 0.3, 0.7, 3.0, 1.0, decay_shape=-2, release_shape=3)
b = Envelope.adsr(0.2, 1.0, 0.3, 0.7, 3.0, 1.0, decay_shape=-2, release_shape=3).shift_horizontal(3) + 1
((a + b) * (a - b)).show_plot("Math on envelopes #1")
(a / b).show_plot("Math on envelopes #2")
