Setup for Experienced Python Users
==================================

Basic Installation
------------------

If you're already familiar with Python and you know how to install packages using `pip <https://realpython.com/what-is-pip/>`_,
then installing SCAMP is a simple process. Simply run from the command line:

.. code-block:: bash

    pip3 install --user scamp

From there, Linux users will need to install the FluidSynth library through their package manager.
On apt-based distros like Debian, Ubuntu or Trisquel, this is as simple as running:

.. code-block:: bash

    sudo apt install fluidsynth

Mac and Windows users will not need to manually install FluidSynth, since a binary version of the library
has been included within the SCAMP package. (This was the path of least resistance, since there is not a
built-in package manager for Mac or Windows.)

Optional (but recommended) Components
-------------------------------------

Installing python-rtmidi
~~~~~~~~~~~~~~~~~~~~~~~~

For midi input, and also to generate an outgoing midi stream (which could, for instance, be routed to a DAW),
you will need the python-rtmidi library. You can get this by running from the command line:

.. code-block:: bash

    pip3 install --user python-rtmidi

On Linux, if you're running into an error you may need to first install the python3-dev package, for
instance with the command:

.. code-block:: bash

    sudo apt install python3-dev

For any other python-rtmidi installation woes, take a look at the installation instructions here.

Installing abjad and LilyPond
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

For LilyPond output, you will need the `abjad` library. To do so, run the following:

.. code-block:: bash

    pip3 install --user abjad==3.4

Note the '==' in the command, which specifies the exact version of abjad to install. This is the version
that SCAMP has been built to be compatible with. You are free to use a newer version, but it is possible
there will be unexpected errors due to changes in the abjad API.

After installing `abjad`, you will also need to `download and install LilyPond <https://lilypond.org/>`_,
since `abjad` relies upon it.

Installing scamp_extensions
~~~~~~~~~~~~~~~~~~~~~~~~~~~

The `scamp_extensions` package is the place for models of music-theoretical concepts (e.g. scales,
pitch-class sets), additional conveniences for interacting with various types of input and output,
and in general anything that builds upon SCAMP but is outside of the scope of the main framework.

The easiest way to install `scamp_extensions` is by running the command:

.. code-block:: bash

    pip3 install --user scamp_extensions

To install the most up-to-date version (assuming you have git installed), you can instead run:

.. code-block:: bash

    pip3 install git+https://git.sr.ht/~marcevanstein/scamp_extensions

This will install the latest version from this repo.
