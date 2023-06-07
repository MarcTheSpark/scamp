Easy Setup for New Python Users
===============================

If you're new to Python, the instructions below will help you get set up with SCAMP running in a simple Python editor
called `Thonny <https://thonny.org/>`_. These steps are largely the same for different operating systems, except as
noted below. If you're on MacOS, you can also follow along with this video:

.. raw:: html

    <iframe class="youtube" frameborder=0 allowfullscreen="" src="https://www.youtube.com/embed/cghGKwWSdWI?rel=0&showinfo=0&listen=0"></iframe>


Step 1: Install Thonny
----------------------

You can download and install the latest version of Thonny `from the Thonny website <https://thonny.org/>`_.


..  note::

    On Windows, you may run into an issue with Windows Defender not trusting the installer; just click "More info" and
    "Run anyway":

    +-------+-------+
    ||pic1| | |pic2||
    +-------+-------+


    .. |pic1| image:: WindowsInstallingThonny.png
       :width: 100%

    .. |pic2| image:: WindowsInstallingThonny2.png
       :width: 100%


Step 2: Install SCAMP and its dependencies
------------------------------------------

Open up Thonny, and go to `Tools > Manage Packages` in the menu. You should be presented with a window that looks like
this:

.. figure:: InstallingSCAMP.png
   :scale: 40 %
   :align: center
   :alt: Thonny package manager

   Installing the *scamp* package using the Thonny package manager.


Type “scamp” into the textbox and click “Find package from PyPI”. PyPI is an online repository of Python libraries from
which SCAMP can be downloaded and installed. Click the “Install” button.

Having done that, in order to get the full functionality that SCAMP has to offer, you will want to use the same method
to search for and install the following:

- ``python-rtmidi`` (offers the ability to stream MIDI to an external synthesizer or application)

- ``pynput`` (offers responsiveness to mouse and keyboard events)

- ``scamp_extensions`` (offers a range of useful extensions, like scales and other musical constructs)

- ``abjad`` (generate PDFs of music notation using LilyPond)

.. note::

    On Linux, in order to install ``python-rtmidi`` you may have to first install the Python development headers.
    On Debian-based distros, simply run ``sudo apt install python3-dev`` from a terminal.

+--------+--------+
||pic1b| | |pic2b||
+--------+--------+


.. |pic1b| image:: AlternateVersionAbjad.png
   :width: 100%

.. |pic2b| image:: SelectVersionAbjad.png
   :width: 100%


Step 3: Install FluidSynth
--------------------------

`FluidSynth <https://www.fluidsynth.org/>`_ is the synthesizer that SCAMP uses behind the scenes to play notes. On
intel-based Macs and Windows, it comes bundled with SCAMP, and so does not need to be separately installed.

On the new Apple Silicon Macs, the bundled intel-based copy of of FluidSynth will not work. I'm working on bundling a
version that will work, but in the meantime, you can install FluidSynth via `homebrew <https://brew.sh/>`_. Simply
install homebrew via the script on the website, and then run ``brew install fluid-synth`` from a terminal.

On Linux, the easiest way to install FluidSynth is through your distro's package manager. On Debian-based distros,
simply open a terminal and type ``sudo apt install fluidsynth``.


Step 4: Install LilyPond
------------------------

LilyPond is a program for engraving music notation that SCAMP uses to generate PDFs of the music you create. You can
download it from `here <http://lilypond.org/download.html>`_. If you're on a Mac, after unzipping the download, place it
in the Applications folder so that SCAMP can find it. If you're on Windows, place it in the Program Files folder
(e.g. ``C:\Program Files (x86)``). On Linux, the easiest thing is to install LilyPond via your package manager.

When you first try to generate a LilyPond score using SCAMP, SCAMP will search for LilyPond and post a message
informing you that it (hopefully) found it.

If you're on a Mac, when you first try to generate notation using LilyPond, you will likely see a dialog come up
saying that LilyPond cannot be opened because it's from an unidentified developer (first image below). You have two options:
reverse course and install lilypond via homebrew (``brew install lilypond``, similar to fluidsynth above), or go through
an irritating sequence of steps to convince your computer that LilyPond is okay.

If you choose the latter, click "cancel", and then open up your security and privacy settings (second image).
You should see an option to "allow" lilypond to run. Then, the next time you try to generate notation using LilyPond,
you should get a different dialog with the option of opening it (third image).

+--------+--------+--------+
||pic1c| | |pic2c|| |pic3c||
+--------+--------+--------+

.. |pic1c| image:: LilyWarning.png
   :width: 100%

.. |pic2c| image:: SecuritySettings.png
   :width: 100%

.. |pic3c| image:: OpenLilyPondAnyway.png
   :width: 100%

You will then probably have to follow this sequence one more time for a program called `gs`, which LilyPond depends on.

Note that this whole irritating sequence is Apple's fault: in order to become an "identified developer" you have no
choice but to pay Apple money, and the developers of LilyPond are volunteers who understandably don't want to pay
Apple to offer you free software.


Testing it Out
--------------

To test if everything is working correctly, open up Thonny, and save and run (by pressing the green arrow) the
following script:

.. code-block:: python

    from scamp import test_run
    test_run.play(show_lilypond=True)

If you hear a piano gesture sweeping inward towards middle C, and then see a PDF pop up with the music, then
the setup process has been successful!
