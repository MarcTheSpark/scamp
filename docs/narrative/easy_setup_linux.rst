Easy Setup on Linux
===================

Setting up SCAMP on Linux involves four very simple steps:

- Installing Thonny
- Installing the SCAMP libraries and dependencies
- Installing FluidSynth
- Installing LilyPond

Installing Thonny
-----------------

Instructions for installing Thonny on Linux can be found at `<https://thonny.org/>`_. One good approach is to open a
terminal window and type:

.. code::

    bash <(wget -O - https://thonny.org/installer-for-linux)

This will download and install Thonny bundled with its own copy of Python. You can also install Thonny via your package
manager, though this will likely give you a significantly less up-to-date version.

Installing SCAMP and its Dependencies
-------------------------------------

Open up Thonny, and go to the `Tools > Manage Packages` menu. You should be presented with a window that looks like
this:

.. figure:: InstallingSCAMP.png
   :scale: 40 %
   :align: center
   :alt: Thonny package manager

   Installing the *scamp* package using the Thonny package manager.

Using this tool, search for and install the following packages: *scamp*, *pynput*, *python-rtmidi*, and *abjad*. (If you
run into an issue with *python-rtmidi*, try opening a terminal and running :code:`sudo apt install python3-dev`.)

Installing FluidSynth
---------------------

The easiest way to install FluidSynth is through your distro's package manager. On Debian-based distros, simply open a
terminal and type:

.. code::

    sudo apt install fluidsynth

Installing Lilypond
-------------------

As with FluidSynth, The easiest way to install LilyPond is through your distro's package manager. On Debian-based
distros, simply open a terminal and type:

.. code::

    sudo apt install lilypond

If you want the most up-to-date version, however, you can also follow the instructions on
`the LilyPond website <https://lilypond.org/unix.html>`_.

Testing it Out
--------------

The easiest way to test things out is to create and run (by pressing the play button) a simple file containing the
following code::

    from scamp import test_run
    test_run.play(show_lilypond=True)

If you here a piano gesture sweeping inward towards middle C, and then see a PDF pop up with the music, then success!