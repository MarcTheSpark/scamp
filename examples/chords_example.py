from playcorder import *

pc = Playcorder("default")

piano = pc.add_midi_part("piano")

# this makes the whole chord diamond noteheads
piano.play_chord((60, 64, 69), 0.5, 2.0, "notehead: diamond")

# this gives separate noteheads for separate pitches
piano.play_chord((60, 64, 69), 0.5, 2.0, "noteheads: diamond / normal / cross")

# noteheads are assigned in the order of the pitch tuple given, not in order from low to high
# so here, middle C has a normal notehead, E has a diamond, and A has a cross
piano.play_chord((64, 60, 69), 0.5, 2.0, "noteheads: diamond / normal / cross")

# Here an error is thrown, because the wrong number of noteheads is given for the chord
piano.play_chord((64, 60, 69), 0.5, 2.0, "noteheads: diamond / normal")
