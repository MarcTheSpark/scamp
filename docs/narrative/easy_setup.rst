Easy Setup for New Python Users
===============================

Below you will find instructions on getting setup with SCAMP running in a simple Python editor called `Thonny
<https://thonny.org/>`_. Take a look at the instructions applicable to your operating system.

Easy Setup on MacOS
-------------------

The easiest way to get setup with SCAMP and Python on MacOS, is to download `a custom version of the Thonny Python
editor with all of the SCAMP libraries pre-installed <https://marcevanstein.ddns.net/s/6kxBSxGrtxjAyCw>`__. (Thonny is a
simple development environment designed specifically for beginners. You can read more about it
`here <https://thonny.org/>`__.)

After installing the Thonny/SCAMP bundle, the next step is to `download and install LilyPond <http://lilypond.org>`__.
Place the installed copy of LilyPond in the Applications directory so that SCAMP can find it.

..  note::

    If you are running MacOS Catalina 10.15 (or future versions), the current official release of LilyPond will not work
    for you, since it is a 32-bit application, and Catalina abandons 32-bit support. However, you can download an
    experimental 64-bit build `here <https://marcevanstein.ddns.net/s/jZpXE3ZBY5add3G>`__.

This video provides a step-by-step walk-through of the installation process:

.. raw:: html

  <iframe class="youtube" frameborder=0 allowfullscreen="" src="https://www.youtube.com/embed/PRM-FxBtAfo?rel=0&showinfo=0&listen=0"></iframe>


Easy Setup on Linux
-------------------

Setting up SCAMP on Linux involves four very simple steps:

- Installing Thonny
- Installing the SCAMP libraries and dependencies
- Installing FluidSynth
- Installing LilyPond

Installing Thonny
~~~~~~~~~~~~~~~~~

Instructions for installing Thonny on Linux can be found at `<https://thonny.org/>`__. One good approach is to open a
terminal window and type:

.. code::

    bash <(wget -O - https://thonny.org/installer-for-linux)

This will download and install Thonny bundled with its own copy of Python. You can also install Thonny via your package
manager, though this will likely give you a significantly less up-to-date version.

Installing SCAMP and its Dependencies
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Open up Thonny, and go to the `Tools > Manage Packages` menu. You should be presented with a window that looks like
this:

.. figure:: InstallingSCAMP.png
   :scale: 40 %
   :align: center
   :alt: Thonny package manager

   Installing the *scamp* package using the Thonny package manager.


Type “scamp” into the textbox and click “Find package from PyPI”. PyPI is an online repository of Python libraries from
which SCAMP can be downloaded and installed. Click the “Install” button.

Having done that, you will want to search for and install the following optional dependencies in order to get the full
functionality that SCAMP has to offer:

- `python-rtmidi` (offers the ability to stream MIDI to an external synthesizer or application. Note that, on linux, you may have to install some development packages such as `python3-dev` for this packages to install successfully.)

- `abjad` (makes it possible to generate scores via LilyPond)

- `pynput` (offers responsiveness to mouse and keyboard events)

- `scamp_extensions` (offers a range of useful extensions, like scales and other musical constructs)


Installing FluidSynth
~~~~~~~~~~~~~~~~~~~~~

The easiest way to install FluidSynth is through your distro's package manager. On Debian-based distros, simply open a
terminal and type:

.. code::

    sudo apt install fluidsynth

Installing Lilypond
~~~~~~~~~~~~~~~~~~~

As with FluidSynth, The easiest way to install LilyPond is through your distro's package manager. On Debian-based
distros, simply open a terminal and type:

.. code::

    sudo apt install lilypond

If you want the most up-to-date version, however, you can also follow the instructions on
`the LilyPond website <https://lilypond.org/unix.html>`__.

Testing it Out
~~~~~~~~~~~~~~

The easiest way to test things out is to create and run (by pressing the play button) a simple file containing the
following code::

    from scamp import test_run
    test_run.play(show_lilypond=True)

If you here a piano gesture sweeping inward towards middle C, and then see a PDF pop up with the music, then success!

Easy Setup on Windows
---------------------

If you're new to Python, the easiest way to get up and running with SCAMP on Windows is to:

1. Install Thonny, a simple Python editor for beginners

2. Install the SCAMP package and its dependencies from inside Thonny

3. Install LilyPond

Installing Thonny
~~~~~~~~~~~~~~~~~

To install Thonny, simply go to `the Thonny website <https://thonny.org/>`__ and download and run the Windows installer.
You may run into an issue with Windows Defender not trusting the installer; just click "More info" and
"Run anyway":

+-------+-------+
||pic1| | |pic2||
+-------+-------+


.. |pic1| image:: WindowsInstallingThonny.png
   :width: 100%

.. |pic2| image:: WindowsInstallingThonny2.png
   :width: 100%

Run the installer as you would any other installer, and then open up Thonny.


Installing SCAMP
~~~~~~~~~~~~~~~~

From inside scamp, go to the `Tools` menu and select `Manage Packages...`

.. image:: WindowsManagePackages.png
   :width: 70%
   :align: center

In the dialog that opens, type "scamp" into the textbox and click "Find package from PyPI". PyPI is an online repository
of Python libraries from which SCAMP can be downloaded and installed. Click the "Install" button:

.. image:: WindowsInstallSCAMP.png
   :width: 70%
   :align: center

Having done that, you will want to search for and install the following optional dependencies in order to get the full
functionality that SCAMP has to offer:

- `python-rtmidi` (offers the ability to stream MIDI to an external synthesizer or application)

- `abjad` (makes it possible to generate scores via LilyPond)

- `pynput` (offers responsiveness to mouse and keyboard events)

- `scamp_extensions` (offers a range of useful extensions, like scales and other musical constructs)


Installing LilyPond
~~~~~~~~~~~~~~~~~~~

One of the tools that SCAMP uses to produce music notation is a marvelous piece of free and open source music notation
software called LilyPond. Download and install LilyPond from `the LilyPond website <http://lilypond.org/windows.html>`__.
You may see an unnerving dialog about allowing and "unknown publisher to make changes". Just click yes and proceed with
the installation:

.. image:: WindowsLilypondUnnerving.png
   :width: 70%
   :align: center


Testing it Out
~~~~~~~~~~~~~~

To test if everything is working correctly, open up Thonny, and save and run the following script:

.. code-block:: python

    from scamp import test_run
    test_run.play(show_lilypond=True)

You should hear a piano gesture sweeping inward towards middle C, and then see the notation pop up!