#!/usr/bin/env python

from distutils.core import setup

setup(name='Playcorder',
      version='0.1',
      description='Python interface for playing notes via pyFluidSynth and saving the result in formats that can be '
                  'imported to notation programs.',
      author='Marc Evans',
      author_email='marc.p.evans@gmail.com',
      url='https://github.com/MarcTheSpark/playcorder',
      py_modules=['playcorder', 'playcorder_utilities', 'musicXML_exporter', 'measures_beats_notes',
                  'interval', 'fluidsynth'],
 )