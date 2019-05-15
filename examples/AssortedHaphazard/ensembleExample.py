from scamp import Ensemble


def construct_ensemble():
    global piano, flute, strings, ensemble
    ensemble = Ensemble()

    ensemble.print_default_soundfont_presets()

    piano = ensemble.new_part("piano")
    flute = ensemble.new_part("flute")
    strings = ensemble.new_part("strings", (0, 40))


def play_some_stuff():
    while True:
        piano.play_note(65, 0.5, 1.0)
        flute.play_note(70, 0.5, 0.25)
        strings.play_note([75, 73], 0.5, 1.0, blocking=True)


construct_ensemble()

# # ------- Use this line to save the Ensemble so that it can be reloaded -------
# ensemble.save_to_json("SavedFiles/savedEnsemble.json")

# # ------- Use this line to reloaded the Ensemble from the saved file -------
# ensemble = Ensemble.load_from_json("SavedFiles/savedEnsemble.json")
# piano, flute, strings = ensemble.instruments

play_some_stuff()
