#!/usr/bin/env python

from distutils.core import setup

setup(name='Playcorder',
      version='0.1',
      description='Python interface for playing notes via pyFluidSynth and saving the result in formats that can be '
                  'imported to notation programs.',
      author='Marc Evans',
      author_email='marc.p.evans@gmail.com',
      requires=['midiutil', 'sf2utils', 'python-rtmidi', 'sortedcontainers'],
      url='https://github.com/MarcTheSpark/playcorder',
      packages=['playcorder', "playcorder.thirdparty"],
      package_dir={'playcorder': 'source'},
      package_data={'playcorder.thirdparty': ['soundfonts/*']},
      )
