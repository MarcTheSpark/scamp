# SCAMP (Suite for Computer-Assisted Music in Python)

SCAMP is an computer-assisted composition framework in Python designed to act as a hub, flexibly connecting the 
composer-programmer to a wide variety of resources for playback and notation. SCAMP allows the user to 
manage the flow of musical time, play notes either using [FluidSynth](http://www.fluidsynth.org/) or via MIDI or OSC messages
to an external synthesizer, and ultimately quantize and export the result to music notation in the form of MusicXML or Lilypond. 
Overall, the framework aims to address pervasive technical challenges while imposing as little as possible on the aesthetic choices 
of the composer-programmer. 

## Features

- Flexible and extensible playback: Although SCAMP comes with a basic general MIDI soundfont, 
any .sf2 or .sf3 soundfont can be used, and playback can also include MIDI or OSC messages to external 
programs or synthesizers, which effectively offers limitless sonic possibilities.

- Note-based, but in a broad sense: Although SCAMP conceives of music in terms of notes, notes in
SCAMP are extremely flexible sound-objects that can include the continuous evolution of arbitrary 
playback parameters.

- Effortless microtonality: to play the G above middle C 30 cents sharp, the user has only 
to use the MIDI pitch 67.3. Behind the scenes, SCAMP manages all the MIDI pitchbend 
messages, placing notes on separate channels where necessary so that these messages do 
not conflict.

- Effortless playback of glissandi and dynamic envelopes. Both pitch and volume can follow 
arbitrary curves defined using the [_expenvelope_](https://github.com/MarcTheSpark/expenvelope) package.

- Flexible and precise polyphonic tempo control using [_clockblocks_](https://github.com/MarcTheSpark/clockblocks). 
In SCAMP, different layers of music moving at different tempi can be interwoven with one 
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
extensions are available in the [_scamp_extensions_](https://github.com/MarcTheSpark/scamp_extensions) package.)

Other key values underlying this framework are:

- Playback first, notation second: SCAMP has been designed so that the user interacts with an 
ensemble, not a score. This way, ideas can be quickly auditioned and iterated over based on the 
sonic result. Once the result is deemed satisfactory, the user can then export it as music notation.
- Compact and expressive code: Efforts have been made to make user code simple, yet powerful. 
One of the ways this is accomplished is through sensible defaults; although there is a lot of 
functionality under the hood, it shouldn't be encountered by the user until it is needed.
- Modularity and adherence as much as possible to the [Unix Philosophy](https://en.wikipedia.org/wiki/Unix_philosophy). 
SCAMP bundles a number of tools together for convenience, but it may be more than a given user 
needs. For this reason, the MusicXML export capability is available separately as 
[_pymusicxml_](https://github.com/MarcTheSpark/pymusicxml), the flexible musical Envelope 
class is available separately as [_expenvelope_](https://github.com/MarcTheSpark/expenvelope), 
and the system for managing musical time is available separately as [_clockblocks_](https://github.com/MarcTheSpark/clockblocks).


## Installation & Requirements

SCAMP requires **Python 3.12 or greater**. With Python installed, opening a terminal and running:

```
pip install scamp
```

is usually all you need. Prebuilt wheels on PyPI bundle the FluidSynth library for Linux, macOS
(both Intel and Apple Silicon), and Windows, so soundfont playback works out of the box on all
three platforms with no separate install step.

To pull in the optional extras (LilyPond export, MIDI input/output, keyboard/mouse input) in
one go:

```
pip install "scamp[all]"
```

This installs `abjad==3.31` (pinned for compatibility), `python-rtmidi`, and `pynput`.

Test the installation by:

1) Opening a terminal and typing `python` to start an interactive python session.
2) Typing in `from scamp import test_run; test_run.play()` and pressing return.

If you hear a piano gesture sweeping inward towards middle C, SCAMP has installed correctly!

### Optional dependencies, individually

You don't need any of these for a basic install — they only matter if you want the
corresponding feature.

**python-rtmidi** — needed for MIDI input and for generating an outgoing MIDI stream (e.g. into
a DAW). On Linux, if `pip install python-rtmidi` fails, you may first need the Python development
headers: `sudo apt install python3-dev`. See the [python-rtmidi installation
instructions](https://spotlightkid.github.io/python-rtmidi/installation.html) for details.

**abjad + LilyPond** — needed for LilyPond output. SCAMP pins to `abjad==3.31`; newer abjad
releases sometimes break compatibility, so prefer `pip install "scamp[all]"` (which uses the
pinned version) over `pip install abjad`. After installing abjad, also [download and install
LilyPond](https://lilypond.org/), which abjad calls out to.

**pynput** — needed for the keyboard/mouse input helpers in `scamp.utilities`.

### Building FluidSynth from source (Linux, advanced)

Linux wheels include a bundled FluidSynth, but if you have FluidSynth installed system-wide
(e.g. `sudo apt install fluidsynth`), SCAMP will prefer that copy. This is useful if you want
SCAMP to share a FluidSynth build with the rest of your system, or you're running on a distro
the wheels weren't built for.

### Installing scamp_extensions

The *scamp_extensions* package is the place for models of music-theoretical concepts (e.g.
scales, pitch-class sets), additional conveniences for interacting with various types of input
and output, and in general anything that builds upon SCAMP but is outside the scope of the main
framework.

```
pip install scamp_extensions
```

To install the latest development version directly from GitHub:

```
pip install git+https://github.com/MarcTheSpark/scamp_extensions
```
