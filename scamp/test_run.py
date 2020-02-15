"""
Simple module with the a :code:`play` function that can be used to verify that SCAMP is installed successfully.
"""

from . import Session


def play(show_lilypond: bool = False, show_xml: bool = False) -> None:
    """
    Simple method for determining if scamp was installed correctly. Should play a sequence of pitches telescoping
    towards middle C.

    :param show_lilypond: shows a PDF LilyPond rendering of demo played (requires abjad package).
    :param show_xml: opens up a MusicXML rendering of the music played
    """
    s = Session()

    piano = s.new_part()

    if show_xml or show_lilypond:
        s.start_transcribing()

    s.set_rate_target(4, 10)

    for n in reversed(range(1, 40)):
        piano.play_note(60 + n * (-1) ** n, 1, 0.25)

    piano.play_note(60, 1.0, 6.25)

    if show_xml or show_lilypond:
        score = s.stop_transcribing().to_score()
        if show_lilypond:
            score.show()
        if show_xml:
            score.show_xml()
