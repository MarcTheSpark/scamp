name = "scamp"

version = "0.6.8"

author = "Marc Evanstein"

author_email = "marc@marcevanstein.com"

description = "A computer-assisted composition framework that manages the flow of musical time, plays back notes via "\
              "SoundFonts, MIDI or OSC, and quantizes and saves the result to music notation."

url = "http://scamp.marcevanstein.com"

project_urls = {
    "Source Code": "https://github.com/MarcTheSpark/scamp",
    "Documentation": "http://scamp.marcevanstein.com",
}

install_requires = ['pymusicxml >= 0.3.0', 'expenvelope >= 0.6.0', 'clockblocks >= 0.5.2', 'sf2utils', 'python-osc']

extras_require = {
    'lilypond': 'abjad==3.1',
    'midistream': 'python-rtmidi',
    'mouse and keyboard input': 'pynput'
}

package_data = {
    'scamp': ['settings/*', 'soundfonts/*', '_thirdparty/*.dll', '_thirdparty/*.dylib']
}

classifiers = [
    "Programming Language :: Python :: 3.6",
    "License :: OSI Approved :: GNU General Public License v3 (GPLv3)",
    "Operating System :: OS Independent",
]
