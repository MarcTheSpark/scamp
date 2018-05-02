from playcorder.ensemble import Ensemble

ensemble = Ensemble("default", "pulseaudio")


piano = ensemble.add_midi_part("piano", (0, 0))

while True:
    piano.play_note(65, 0.5, 1.0, blocking=True)