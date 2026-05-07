Setup for Experienced Python Users
==================================

Basic Installation
------------------

SCAMP requires **Python 3.12 or greater**. If you're already familiar with Python and
you know how to install packages using `pip <https://realpython.com/what-is-pip/>`_, installing
SCAMP is a one-liner:

.. code-block:: bash

    pip install scamp

The prebuilt wheels on PyPI bundle the FluidSynth library for Linux, macOS (both Intel and Apple
Silicon), and Windows, so soundfont playback works out of the box on all three platforms — no
separate FluidSynth install is required.

To pull in the optional extras (LilyPond export, MIDI I/O, keyboard/mouse input) all at once:

.. code-block:: bash

    pip install "scamp[all]"

This installs ``abjad==3.31`` (pinned for compatibility), ``python-rtmidi``, and ``pynput``.

A note about FluidSynth
-----------------------

The way that SCAMP plays notes out of the box is through a free and open source library called
FluidSynth, which renders sound from short recordings of individual notes stored in soundfonts (.sf2 files).
You usually shouldn't need to think about it — the bundled FluidSynth that ships with the SCAMP
wheels is enough on all supported platforms. It's worth knowing the mechanism, though, in case
you want to swap in a system copy (especially on Linux, where a package-managed FluidSynth is
often better integrated with the host audio stack — JACK, PipeWire, PulseAudio routing, etc.).

Two ``playback_settings`` flags govern what gets loaded:

- ``try_system_fluidsynth_first`` — if ``True``, SCAMP tries to ``dlopen`` the *system*
  ``libfluidsynth`` first and falls back to the bundled binary if that fails. Defaults to
  ``True`` on Linux and ``False`` on Mac/Windows. Set it to ``True`` on any platform if you've
  installed FluidSynth yourself (e.g. ``brew install fluid-synth``,
  ``sudo apt install fluidsynth``) and want SCAMP to use it.
- ``use_bundled_pyfluidsynth`` — if ``True`` (the default everywhere), SCAMP uses its own copy
  of the *pyfluidsynth* Python wrapper, which can dlopen either the system or bundled
  ``libfluidsynth``. Set to ``False`` to use a separately ``pip install``\ ed ``pyfluidsynth``
  instead.

You can change either of these via :class:`~scamp.settings.PlaybackSettings` and persist with
``save_to_json()``. To inspect what actually got loaded in the current process, see the testing
section below.

Optional (but recommended) Components
-------------------------------------

Installing python-rtmidi
~~~~~~~~~~~~~~~~~~~~~~~~

For midi input, and also to generate an outgoing midi stream (which could, for instance, be routed to a DAW),
you will need the python-rtmidi library. You can get this by running from the command line:

.. code-block:: bash

    pip install python-rtmidi

On Linux, if you're running into an error you may need to first install the python3-dev package, for
instance with the command:

.. code-block:: bash

    sudo apt install python3-dev

For any other python-rtmidi installation woes, take a look at the installation instructions here.

Installing abjad and LilyPond
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

For LilyPond output, you will need the `abjad` library. To do so, run the following:

.. code-block:: bash

    pip install abjad==3.31

Note the '==' in the command, which specifies the exact version of abjad to install. This is the version
that SCAMP has been built to be compatible with. abjad has historically made breaking API changes
between releases, so newer versions may not work; if you're not sure which version you have, the
simplest path is ``pip install "scamp[all]"``, which pins this version for you.

After installing `abjad`, you will also need to `download and install LilyPond <https://lilypond.org/>`_,
since `abjad` relies upon it. You may run into security issues, which are further explained in :doc:`easy_setup`.

Installing scamp_extensions
~~~~~~~~~~~~~~~~~~~~~~~~~~~

The `scamp_extensions` package is the place for models of music-theoretical concepts (e.g. scales,
pitch-class sets), additional conveniences for interacting with various types of input and output,
and in general anything that builds upon SCAMP but is outside of the scope of the main framework.

The easiest way to install `scamp_extensions` is by running the command:

.. code-block:: bash

    pip install scamp_extensions

To install the most up-to-date version (assuming you have git installed), you can instead run:

.. code-block:: bash

    pip install git+https://github.com/MarcTheSpark/scamp_extensions

This will install the latest version from this repo.

Testing the install
-------------------

To make sure that everything is working correctly, you can run the following short script:

.. code-block:: python

    from scamp import test_run, print_dependency_status

    print_dependency_status()
    test_run.play(show_lilypond=True)

Ideally, you should see a bunch of checkmarks and hear a short piano gesture sweeping inward toward middle C.

``print_dependency_status()`` prints a one-line-per-dependency report covering FluidSynth (with
the wrapper and the resolved ``libfluidsynth`` binary path, so you can confirm whether the
system or bundled copy got loaded), ``sf2utils``, ``python-osc``, ``python-rtmidi``, ``pynput``,
and ``abjad`` (with installed-vs-tested-version comparison). States are ``ok`` / ``warn`` /
``missing``. If you're excessively nerdy and would rather consume the data programmatically,
``dependency_status()`` returns the same information as a list of ``(name, state, detail)`` tuples.

``test_run.play()`` plays the aforementioned piano gesture; with
``show_lilypond=True`` it also exercises the abjad → LilyPond → PDF path to display notation.
