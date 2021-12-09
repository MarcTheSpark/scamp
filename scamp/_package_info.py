#  ++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++  #
#  This file is part of SCAMP (Suite for Computer-Assisted Music in Python)                      #
#  Copyright © 2020 Marc Evanstein <marc@marcevanstein.com>.                                     #
#                                                                                                #
#  This program is free software: you can redistribute it and/or modify it under the terms of    #
#  the GNU General Public License as published by the Free Software Foundation, either version   #
#  3 of the License, or (at your option) any later version.                                      #
#                                                                                                #
#  This program is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY;     #
#  without even the implied warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.     #
#  See the GNU General Public License for more details.                                          #
#                                                                                                #
#  You should have received a copy of the GNU General Public License along with this program.    #
#  If not, see <http://www.gnu.org/licenses/>.                                                   #
#  ++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++  #

name = "scamp"

version = "0.8.9.5"

author = "Marc Evanstein"

author_email = "marc@marcevanstein.com"

description = "A computer-assisted composition framework that manages the flow of musical time, plays back notes via "\
              "SoundFonts, MIDI or OSC, and quantizes and saves the result to music notation."

url = "http://scamp.marcevanstein.com"

project_urls = {
    "Source Code": "https://sr.ht/~marcevanstein/scamp/",
    "Documentation": "http://scamp.marcevanstein.com",
    "Forum": "http://scampsters.marcevanstein.com"
}

install_requires = ['pymusicxml >= 0.5.4', 'expenvelope >= 0.6.8', 'clockblocks >= 0.6.5', 'python-osc']
# Note: pyfluidsynth and sf2utils are also dependencies, but needed to be tweaked,
# so they have been copied into the _third_party package

ABJAD_MIN_VERSION = "3.3"
ABJAD_VERSION = "3.4"

extras_require = {
    'lilypond': 'abjad==' + ABJAD_VERSION,
    'midistream': 'python-rtmidi',
    'HID': 'pynput',
}

extras_require['all'] = list(extras_require.values())

package_data = {
    'scamp': ['soundfonts/*', '_thirdparty/mac_libs/*', '_thirdparty/windows_libs/*']
}

classifiers = [
    "Programming Language :: Python :: 3.6",
    "License :: OSI Approved :: GNU General Public License v3 (GPLv3)",
    "Operating System :: OS Independent",
]
