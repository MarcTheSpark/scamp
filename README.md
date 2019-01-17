# SCAMP (Suite for Composing Algorithmic Music in Python)

SCAMP is an algorithmic composition framework in Python that manages the flow of musical time, plays back notes via [FluidSynth](http://www.fluidsynth.org/) or over OSC, and quantizes and exports the result to music notation in the form of MusicXML or Lilypond. This framework is the distillation of years of practice composing algorithmic music in Python and aims to address pervasive technical challenges while imposing as little as possible on the aesthetic choices of the user. 

## Features

- Flexible and extensible playback: Although SCAMP comes with a basic general MIDI soundfont, 
any .sf2 soundfont can be used, and multiple soundfonts can be used simultaneously. Beyond 
that, the OSCScampInstrument class allows playback to be done by controlling an external 
synth over OSC. For even broader flexibility, custom instruments can inherit from the 
ScampInstrument class and redefine how notes are played.
- Note-based, but in a broad sense: Although SCAMP conceives of music in terms of notes, 
the ability to use anything as a soundfont and to control synths over OSC lends a great deal 
of variety to what a note represents.
- Effortless microtonality: to play the G above middle C 30 cents sharp, the user has only 
to use the MIDI pitch 67.3. Behind the scenes, SCAMP manages all of the MIDI pitchbend 
messages, placing notes on separate channels where necessary so that these pitch bends do 
not conflict.
- Effortless playback of glissandi and dynamic envelopes. Both pitch and volume can follow 
arbitrary curves defined using the [_expenvelope_](https://github.com/MarcTheSpark/expenvelope) package.
- Flexible and precise polyphonic tempo control using [_clockblocks_](https://github.com/MarcTheSpark/clockblocks). 
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
and share their own extensions to suit their own compositional inclinations.

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
[_pymusicxml_](http://www.github.com/MarcTheSpark/pymusicxml), the flexible musical Envelope 
class is available separately as [_expenvelope_](http://www.github.com/MarcTheSpark/expenvelope), 
and the system for managing musical time is available separately as [_clockblocks_](http://www.github.com/MarcTheSpark/clockblocks).


## Installation & Requirements

On a properly configured computer, installing SCAMP is as simple as opening a terminal and 
running:

`pip3 install --user scamp`

(This installs it for a single user. To install it for all users on a computer, use `sudo pip3 install scamp` and enter your administrator password.)

Properly configuring your computer involves:

1) Installing Python 3.6 or greater
2) Installing FluidSynth
3) (Optional) Installing [_python-rtmidi_](https://spotlightkid.github.io/python-rtmidi/)
4) (Optional) Installing [_abjad_](https://github.com/Abjad/abjad) (Note: currently SCAMP only 
works with the cutting-edge version of abjad available on GitHub -- see below)

Each of these steps is described in greater detail below. After configuring the computer and 
running `pip3 install --user scamp`, you should be able to test the installation by:

1) Opening a terminal and typing `python3` to start an interactive python session.
2) Typing in `from scamp import test_run` and pressing return.

If you here a piano gesture sweeping inward towards middle C, SCAMP has installed correctly!

### 1) Installing Python 3.6 or greater

___Mac & Windows___

For Mac and Windows, you can download and install Python 3 here: [https://www.python.org/downloads/](https://www.python.org/downloads/). After installation, open up a terminal and type:

`python3 --version`

You should be greeted with "Python 3.7.2" or something similar in response. If so, you're all set! 
If you get something like "command not found" instead, it's likely that something went wrong in the process of installation.

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

### 2) Installing Fluidsynth

___Mac___

Fluidsynth is best installed through a package manager like [Homebrew](https://brew.sh). If you 
don't already have Homebrew, you can follow the instructions on the website, or simply open a 
terminal and type:

`/usr/bin/ruby -e "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/master/install)"`

...and then return. You will then be prompted to hit return again, and then to enter your password. Mysterious words will appear on the screen. It may take some time. Chill out. Have some tea.

Once it stops, run the following commands:

```
brew update
brew upgrade
```

If it doesn't throw an error, you now have a package manager! Now run:

`brew install fluidsynth`

More strange and occult text will appear before you. When it's done simply type:

`fluidsynth`

Hopefully, something along the lines of this will appear:

```
FluidSynth version 1.1.9
Copyright (C) 2000-2018 Peter Hanappe and others.
Distributed under the LGPL license.
SoundFont(R) is a registered trademark of E-mu Systems, Inc.

Type 'help' for help topics.

> 
```

Type "quit", hit return, and let out a deep breath. You are now the proud owner of a fluidsynthesizer.

___Windows___

Unfortunately, it seems that the suggested way of acquiring fluidsynth on Windows is to compile 
it from source. Since this is rather a lot to ask of some users, SCAMP contains a working copy 
of the windows fluidsynth library to fall back on if no installation is present.

___Linux___

On Linux distros, since you already have a package manager, this is easy. For instance, on 
apt-based distros like Debian, Ubuntu or Trisquel, you can simply run:

`sudo apt install fluidsynth`

Yay, Linux!

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

### 4) (Optional) Installing abjad

For lilypond output, you will need the [_abjad_](http://abjad.mbrsi.org/installation.html) library. In future, this should be as simple as:

`pip3 install --user abjad`

...however, currently you will need the newest version of abjad from the github repository. You can install this with the following:

```
git clone https://github.com/Abjad/abjad.git
cd abjad
pip3 install .
```

The first line might take a while, since the git repository is hundreds of megabytes. Once you've
installed the package, you can remove the bulky repo with:

```
cd ..
rm abjad
```
