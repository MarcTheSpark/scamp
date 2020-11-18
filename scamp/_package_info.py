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

version = "0.8.1"

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

install_requires = ['pymusicxml >= 0.3.5', 'expenvelope >= 0.6.6', 'clockblocks >= 0.5.7', 'sf2utils', 'python-osc']

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
