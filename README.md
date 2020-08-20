# SCAMP (Suite for Computer-Assisted Music in Python)

SCAMP is an computer-assisted composition framework in Python designed to act as a hub, flexibly connecting the 
composer-programmer to a wide variety of resources for playback and notation. SCAMP provides functionality to 
manage the flow of musical time, play back notes via [FluidSynth](http://www.fluidsynth.org/) or MIDI or OSC messages
to an external synthesizer, and quantizes and exports the result to music notation in the form of MusicXML or Lilypond. 
This framework is the distillation of years of practice composing algorithmic and computer-assisted music in Python 
and aims to address pervasive technical challenges while imposing as little as possible on the aesthetic choices 
of the user. 

## Features

- Flexible and extensible playback: Although SCAMP comes with a basic general MIDI soundfont, 
any .sf2 soundfont can be used, and playback can also include MIDI or OSC messages to external 
programs or synthesizers, which effectively offers limitless sonic possibilities.

- Note-based, but in a broad sense: Although SCAMP conceives of music in terms of notes, notes in
SCAMP are extremely flexible sound-objects that can include the continuous evolution of arbitrary 
playback parameters.

- Effortless microtonality: to play the G above middle C 30 cents sharp, the user has only 
to use the MIDI pitch 67.3. Behind the scenes, SCAMP manages all of the MIDI pitchbend 
messages, placing notes on separate channels where necessary so that these pitch bends do 
not conflict.

- Effortless playback of glissandi and dynamic envelopes. Both pitch and volume can follow 
arbitrary curves defined using the [_expenvelope_](https://git.sr.ht/~marcevanstein/expenvelope) package.

- Flexible and precise polyphonic tempo control using [_clockblocks_](https://git.sr.ht/~marcevanstein/clockblocks). 
In SCAMP, different layers of music moving at different tempi can be interweaved with one 
another while remaining coordinated. Smooth accelerandi and ritardandi are possible, and the 
resulting music can be quantized according to the tempo of any layer.

- Sensible and flexible quantization. The user has a fine degree of control over how rhythms 
are quantized and over the degree of complexity in the resulting notation.

## Philosophy

Compositional tools always feature some degree of trade-off between functionality and freedom; 
every feature that is made available to the user steers them in a certain direction. For 
instance, if a framework provides abstractions for manipulating harmonies, the user may find 
themselves (perhaps unconsciously) pushed in the direction of a particular harmonic language. 
While this may be a worthwhile trade-off in many cases, it is not the goal of SCAMP. Here, 
the goal is to provide general purpose tools, to remove the drudgery of implementing practical 
functionality that is needed again and again. Beyond this scope, users are encouraged to write 
and share their own extensions to suit their own compositional inclinations. (Several such 
extensions are available in the [_scamp_extensions_](https://git.sr.ht/~marcevanstein/scamp_extensions) package.)

Other key values underlying this framework are:

- Playback first, notation second: SCAMP has been designed so that the user interacts with an 
ensemble, not a score. This way, ideas can be quickly auditioned and iterated over based on the 
sonic result. Once the result is deemed satisfactory, the user can then export it as music notation.
- Compact and expressive code: Efforts have been made to make user code simple and but powerful. 
One of the ways this is accomplished is through sensible defaults; although there is a lot of 
functionality under the hood, it shouldn't be encountered by the user until it is needed.
- Modularity and adherence as much as possible to the [Unix Philosophy](https://en.wikipedia.org/wiki/Unix_philosophy). 
SCAMP bundles a number of tools together for convenience, but it may be more than a given user 
needs. For this reason, the MusicXML export capability is available separately as 
[_pymusicxml_](https://git.sr.ht/~marcevanstein/pymusicxml), the flexible musical Envelope 
class is available separately as [_expenvelope_](https://git.sr.ht/~marcevanstein/expenvelope), 
and the system for managing musical time is available separately as [_clockblocks_](https://git.sr.ht/~marcevanstein/clockblocks).


## Installation & Requirements

On a properly configured computer, installing SCAMP is as simple as opening a terminal and 
running:

`pip3 install --user scamp`

(This installs it for a single user. To install it for all users on a computer, use `sudo pip3 install scamp` and enter your administrator password.)

Properly configuring your computer involves:

1) Installing Python 3.6 or greater
2) (Linux only) Installing FluidSynth
3) (Optional) Installing [_python-rtmidi_](https://spotlightkid.github.io/python-rtmidi/)
4) (Optional) Installing [_abjad_](https://github.com/Abjad/abjad) and [LilyPond](https://lilypond.org/)

Each of these steps is described in greater detail below. After configuring the computer and 
running `pip3 install --user scamp`, you should be able to test the installation by:

1) Opening a terminal and typing `python3` to start an interactive python session.
2) Typing in `from scamp import test_run; test_run.play()` and pressing return.

If you here a piano gesture sweeping inward towards middle C, SCAMP has installed correctly!

### 1) Installing Python 3.6 or greater

___Mac___

You can download and install Python 3 here: [https://www.python.org/downloads/](https://www.python.org/downloads/). After installation, open up a terminal and type:

`python3 --version`

You should be greeted with "Python 3.7.2" or something similar in response. If so, you're all set! 
If you get something like "command not found" instead, it's likely that something went wrong in the process of installation.

___Windows___

As on a Mac, you can download and install Python 3 here: [https://www.python.org/downloads/](https://www.python.org/downloads/). 
In the installer, be sure to select "Add Python 3.7 to PATH". This allows you to invoke python from the Command Prompt 
by typing either `python` or `py`, and this should also default to the latest version of python. Test that all went
according to plan by typing:

`python --version`

You should be greeted with "Python 3.7.2" or something similar in response. If so, you're all set! For all other installation instructions below, use `python` instead of `python3` and `pip` instead of `pip3`.

___Linux___

On Linux, Python 3.6 or greater is often already installed by default. Again, you can check this 
by opening a terminal and running:

`python3 --version`

If your version of python is already 3.6 or greater, you're good to go. However, if your version 
of Python 3 is less than 3.6, as might happen on an older distro, you can install Python 3.6 via 
a PPA, such as Felix Krull's deadsnakes PPA on Ubuntu:

```
sudo add-apt-repository ppa:deadsnakes/ppa
sudo apt-get update
sudo apt-get install python3.6
```

It might then be useful to add the following line to your `~/.bashrc` file:

`alias pip3.6="python3.6 -m pip"`

From there on, you can proceed to use the commands `pip3.6` and `python3.6` in place of `pip3` 
and `python3` to install SCAMP, manage dependencies, and invoke the correct version of Python. 
(Don't do anything with the earlier version of Python; it's used by the operating system.)

### 2) (Linux only) Installing FluidSynth

SCAMP requires FluidSynth for soundfont playback, but on both Mac and Windows &mdash; due to
the lack of a default package manager &mdash; it became clear that the path of least resistance was to 
include the compiled FluidSynth library within the SCAMP package. For this reason, you don't need to
take the step of installing FluidSynth to use SCAMP on Mac or Windows.

Since Linux distros have package managers, it makes more sense to have users take the extra
step to install FluidSynth that way. On apt-based distros like Debian, Ubuntu or Trisquel, 
it's as simple as running:

`sudo apt install fluidsynth`

You are now the proud owner of a FluidSynthesizer!

### 3) (Optional) Installing python-rtmidi

For midi input, and also to generate an outgoing midi stream (which could, for instance, be 
routed to a DAW), you will need the [_python-rtmidi_](https://pypi.org/project/python-rtmidi/) 
library. You can get this by running from a terminal:

`pip3 install --user python-rtmidi` 

On Linux, if you're running into an error you may need to first install the `python3-dev` 
package, for instance with the command:

`sudo apt install python3-dev`

For any other _python-rtmidi_ installation woes, take a look at the installation instructions 
[here](https://spotlightkid.github.io/python-rtmidi/installation.html).

### 4) (Optional) Installing abjad and LilyPond

For LilyPond output, you will need the [_abjad_](http://abjad.mbrsi.org/installation.html) library. To do so, 
run the following:

```
pip3 install abjad==3.1
```

Note the '==' in the command, which specifies the exact version of abjad to install. This is the version that SCAMP 
has been built to be compatible with. You are free to use a newer version, but it is possible there will be unexpected
errors due to changes in the abjad API.

After installing _abjad_, you will also need to [download and install LilyPond](https://lilypond.org/), since it
is a dependency of abjad.

### 5) (Optional) Installing scamp_extensions

The *scamp_extensions* package is the place for models of music-theoretical concepts (e.g. scales, pitch-class sets), 
additional conveniences for interacting with various types of input and output, and in general anything that builds 
upon SCAMP but is outside of the scope of the main framework.

The easiest way to install `scamp_extensions` is by running the command:

```
pip3 install --user scamp_extensions
```

To install the most up-to-date version (assuming you have git installed), you can instead run:

```
pip3 install --user git+https://git.sr.ht/~marcevanstein/scamp_extensions
```

This will install the latest version from this repository.
