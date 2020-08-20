SCAMP (Suite for Computer-Assisted Music in Python) |release|
=============================================================

`Source Code <https://sr.ht/~marcevanstein/scamp>`_ |
`PyPI <https://pypi.org/project/scamp>`_ |
`Paper <http://marcevanstein.com/Writings/Evanstein_MAT_Thesis_SCAMP.pdf>`_

SCAMP is a computer-assisted composition framework in Python designed to act as a hub, flexibly connecting the
composer-programmer to a variety of resources for playback and notation. SCAMP provides functionality to manage the
flow of musical time, play back notes via SoundFonts or MIDI or OSC messages to an external synthesizer, and quantizes
and exports the result to music notation in the form of MusicXML or LilyPond.

Below, you will find instructions for getting SCAMP up and running on your computer, as well as complete API Documentation.
Narrative documentation is on the way; for now, the following video provides a good introduction to the framework:

.. raw:: html

  <iframe class="youtube" frameborder=0 allowfullscreen="" src="https://www.youtube.com/embed/vpv686Rasds?rel=0&showinfo=0&listen=0"></iframe>

You can also read the `paper introducing the framework <http://marcevanstein.com/Writings/Evanstein_MAT_Thesis_SCAMP.pdf>`_,
and check out the "tutorial" examples found at https://git.sr.ht/~marcevanstein/scamp/tree/master/examples/Tutorial.

.. toctree::
   :maxdepth: 2
   :caption: Set Up and Installation:

   narrative/easy_setup

   narrative/experienced_setup

.. toctree::
   :maxdepth: 2
   :caption: API Reference:

   scamp

   clockblocks

   expenvelope

   pymusicxml

   scamp_extensions


Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`
