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

.. note::

    On Linux, in order to install ``python-rtmidi`` you may have to first install the Python development headers.
    On Debian-based distros, simply run ``sudo apt install python3-dev`` from a terminal.

Finally, if you want to be able generate PDFs of music notation using LilyPond, you will need to install the ``abjad``
package, as well as LilyPond itself (see step 4). One wrinkle here is that SCAMP is based on version 3.4 of abjad,
rather than the latest version. To install that specific version of abjad, search for abjad, and then click the
three dots to the right of the install button. A dialog will pop up allowing you to select the desired version.
Choose 3.4, and click install.

+--------+--------+
||pic1b| | |pic2b||
+--------+--------+


.. |pic1b| image:: AlternateVersionAbjad.png
   :width: 100%

.. |pic2b| image:: SelectVersionAbjad.png
   :width: 100%


Step 3: Install FluidSynth
--------------------------

`FluidSynth <https://www.fluidsynth.org/>`_ is the synthesizer that SCAMP uses behind the scenes to play notes. On Mac
and Windows, it comes bundled with SCAMP, and so does not need to be separately installed.

..  note::

    On new Apple Silicon Macs, you will need to install Rosetta 2 in order for the bundled Intel-based copy of
    FluidSynth to work. You can do this by opening a terminal and running ``softwareupdate --install-rosetta``. (See
    `this link <https://osxdaily.com/2020/12/04/how-install-rosetta-2-apple-silicon-mac/>`_ for more details.)


On Linux, the easiest way to install FluidSynth is through your distro's package manager. On Debian-based distros,
simply open a terminal and type:

.. code::

    sudo apt install fluidsynth


Step 4: Install LilyPond
------------------------

LilyPond is a program for engraving music notation that SCAMP uses to generate PDFs of the music you create. You can
download and install it `here <http://lilypond.org/download.html>`_. If you're on a Mac, after you download and unpack
the application, be sure to drag it into the Applications folder, since this is where SCAMP expects to find it.

..  note::

    If you are running MacOS 10.15 (Catalina) or later, the current official release of LilyPond will not work
    for you, since it is a 32-bit application, and Catalina abandons 32-bit support. However, you can download an
    unofficial 64-bit build `here <https://gitlab.com/marnen/lilypond-mac-builder/-/package_files/9872804/download>`__.


.. note::

    On Windows, you may see an unnerving dialog about allowing an "unknown publisher to make changes". Just click yes
    and proceed with the installation:

    .. image:: WindowsLilypondUnnerving.png
       :width: 70%
       :align: center


Testing it Out
--------------

To test if everything is working correctly, open up Thonny, and save and run (by pressing the green arrow) the
following script:

.. code-block:: python

    from scamp import test_run
    test_run.play(show_lilypond=True)

If you hear a piano gesture sweeping inward towards middle C, and then see a PDF pop up with the music, then
the setup process has been successful!
