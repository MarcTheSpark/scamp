.. _video tutorials:

Tutorial Videos
===============

The following tutorial videos should help get you up and running with SCAMP. Each video is split into two halves: the
first half is a basic introduction, and second half goes into more advanced features.

These tutorials assume that you're a beginner in Python as well as in using the SCAMP library. If you are more experienced
with Python, you will probably still find them useful, but may find you want to fast-forward through some of the content.

Playing Notes
-------------

This video shows the basics of creating a :class:`~scamp.session.Session` object, adding an instrument, and playing some
notes using `for` and `while` loops. In the second half of the video, it goes into blocking vs. non-blocking
:func:`~scamp.instruments.ScampInstrument.play_note` calls, the extra `properties` argument, and playing glissandi,
along with other continuous playback animations.

.. raw:: html

    <iframe class="youtube" frameborder=0 allowfullscreen="" src="https://www.youtube.com/embed/xwxt32ollv0?rel=0&showinfo=0&listen=0"></iframe>

Forking Functions
-----------------

This video describes how to organize blocks of code into functions, and then :func:`~clockblocks.utilities.fork`
them so that they run in parallel (a key step in creating multi-part music). The second half of the video goes into the
use of function arguments, forking functions that have arguments, and playing multiple copies of the same function
simultaneously with different arguments and tempos.

.. raw:: html

    <iframe class="youtube" frameborder=0 allowfullscreen="" src="https://www.youtube.com/embed/WhNLNvugNy0?rel=0&showinfo=0&listen=0"></iframe>

Tempo Changes and Polytempo Music
---------------------------------

This video delves into the clock system in SCAMP, discussing how to set the tempo/rate of a :class:`~clockblocks.clock.Clock`,
how to create ritardandi and accelerandi with :func:`~clockblocks.clock.Clock.set_tempo_target`, and the difference
between time and beat duration units. The second half of the video demonstrates the possibilities for polytempo music in
SCAMP, with multiple parts that each have their own separate tempo curves. It also discusses looping tempo targets,
mapping tempo to a mathematical function, and the system of tempo inheritance in forked processes.

.. raw:: html

    <iframe class="youtube" frameborder=0 allowfullscreen="" src="https://www.youtube.com/embed/J4OqtHF4DYA?rel=0&showinfo=0&listen=0"></iframe>

Generating Music Notation
-------------------------

This video goes into the process of transcribing and generating music notation from a SCAMP script. The first half
explains how to transcribe the notes played within a :class:`~scamp.session.Session` to a :class:`~scamp.performance.Performance`
object, convert that Performance to a :class:`~scamp.score.Score` object, adjust time signatures, note spelling, and
articulations, and ultimately render to both LilyPond and MusicXML. The second half goes into the notation of microtonal
music, glissandi, and polytempo music, as well as the thorny details of quantization.

.. raw:: html

    <iframe class="youtube" frameborder=0 allowfullscreen="" src="https://www.youtube.com/embed/2XjX1-FXNWs?rel=0&showinfo=0&listen=0"></iframe>
