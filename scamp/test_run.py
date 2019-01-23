from . import Session


def play():
    session = Session()

    piano = session.add_midi_part()

    session.set_rate_target(4, 10)

    for n in reversed(range(1, 40)):
        piano.play_note(60 + n * (-1) ** n, 1, 0.25)

    piano.play_note(60, 1.0, 6.0)
