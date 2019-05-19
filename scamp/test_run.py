from . import Session


def play():
    """
    Simple method for determining if scamp was installed correctly. Should play a sequence of pitches telescoping
    towards middle C
    """
    session = Session()

    piano = session.new_part()

    session.set_rate_target(4, 10)

    for n in reversed(range(1, 40)):
        piano.play_note(60 + n * (-1) ** n, 1, 0.25)

    piano.play_note(60, 1.0, 6.0)
