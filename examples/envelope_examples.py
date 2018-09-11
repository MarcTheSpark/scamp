from playcorder.envelope import Envelope

# Ways of constructing Envelopes

envelope_from_levels = Envelope.from_levels((1.0, 0.2, 0.6, 0), length=3)
envelope_from_levels.show_plot()

envelope_from_levels_and_durations = Envelope.from_levels_and_durations((1.0, 0.2, 0.6, 0), (2.0, 1.0, 3.0))
envelope_from_levels_and_durations.show_plot()

envelope_from_levels_and_durations_with_curve_shapes = Envelope.from_levels_and_durations(
    (1.0, 0.2, 0.6, 0), (2.0, 1.0, 3.0), curve_shapes=(2, 2, -3)
)
envelope_from_levels_and_durations_with_curve_shapes.show_plot()

envelope_from_points = Envelope.from_points((-1, 5), (1, 6), (5, -2))
envelope_from_points.show_plot()

envelope_from_points_with_curve_shapes = Envelope.from_points((-1, 5, -3), (1, 6, 2), (5, -2))
envelope_from_points_with_curve_shapes.show_plot()

envelope_from_list1 = Envelope.from_list([3, 6, 2, 0])  # just levels
envelope_from_list1.show_plot()

envelope_from_list2 = Envelope.from_list([[3, 6, 2, 0], 7])  # levels and total duration
envelope_from_list2.show_plot()

envelope_from_list3 = Envelope.from_list([[3, 6, 2, 0], [2, 0.5, 5]])  # levels and segment durations
envelope_from_list3.show_plot()

envelope_from_list4 = Envelope.from_list([[3, 6, 2, 0], [2, 0.5, 5], [3, 0, -3]])  # levels, durations and curve shapes
envelope_from_list4.show_plot()

release_envelope = Envelope.release(3, curve_shape=-2)
release_envelope.show_plot()

attack_release_envelope = Envelope.ar(0.1, 2, release_shape=-3)
attack_release_envelope.show_plot()

attack_sustain_release_envelope = Envelope.asr(1, 0.8, 4, 2, attack_shape=-4)
attack_sustain_release_envelope.show_plot()

adsr_envelope = Envelope.adsr(0.2, 1.0, 0.3, 0.7, 3.0, 1.0, decay_shape=-2, release_shape=3)
adsr_envelope.show_plot()

# Arithmetic with Envelopes:
# Approximates as best as possible the result of function addition / multiplication / division
# Since the resulting functions are often not piecewise exponential, we break the result apart at local min / max
# and points of inflection and try to fit exponentials to each of the resulting segments

a = Envelope.adsr(0.2, 1.0, 0.3, 0.7, 3.0, 1.0, decay_shape=-2, release_shape=3)
a.show_plot()
b = Envelope.adsr(0.2, 1.0, 0.3, 0.7, 3.0, 1.0, decay_shape=-2, release_shape=3).shift_horizontal(3) + 1
b.show_plot()
((a + b) * (a - b)).show_plot()
(a / b).show_plot()
