from scamp import *

TOTAL_LENGTH = 180

# golden ratio durations
gr, one_minus_gr = TOTAL_LENGTH * 0.618, TOTAL_LENGTH * (1 - 0.618)

cello_continue_probability = Envelope.from_levels_and_durations([0.4, 1.0, 0], [gr, one_minus_gr])
cello_staccato_probability = Envelope.from_levels([0, 1], length=TOTAL_LENGTH)
pianoteq_gesture_length = Envelope.from_levels([0, 0, 10, 0], length=TOTAL_LENGTH)
pianoteq_gesture_rit_factor = Envelope.from_levels_and_durations([0.25, 0.8, 0.1], [gr, one_minus_gr])
pianoteq_filler_probability = Envelope.from_levels_and_durations([0.3, 0.97, 0.3], [gr, one_minus_gr])
crackliness = Envelope.from_levels_and_durations([0.6, 1.0, 0], [gr, one_minus_gr])
sc_gesture_length = Envelope.from_levels_and_durations([5, 2, 5], [gr, one_minus_gr])
sc_register = Envelope.from_levels_and_durations([72, 72, 60, 60, 48, 48, 36, 36 ],
                                                 [TOTAL_LENGTH * 0.7, 0, TOTAL_LENGTH * 0.1, 0, TOTAL_LENGTH * 0.1, 0, TOTAL_LENGTH * 0.1])


if __name__ == "__main__":
    cello_continue_probability.show_plot("Cello continue probability")
    cello_staccato_probability.show_plot("Cello staccato probability")
    pianoteq_gesture_length.show_plot("Pianoteq gesture length")
    pianoteq_gesture_rit_factor.show_plot("Pianoteq rit factor")
    pianoteq_filler_probability.show_plot("Pianoteq filler probability")
    crackliness.show_plot("SC instrument crackliness")
    sc_gesture_length.show_plot("SC instrument gesture length")
    sc_register.show_plot("SC instrument register")
