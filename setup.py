import setuptools

with open("README.md", "r") as fh:
    long_description = fh.read()

setuptools.setup(
    name="scamp",
    version="0.4",
    author="Marc Evanstein",
    author_email="marc@marcevanstein.com",
    description="An algorithmic composition framework that manages the flow of musical time, plays back notes via "
                "fluidsynth, MIDI or though osc, and quantizes and saves the result to music notation.",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/MarcTheSpark/scamp",
    packages=setuptools.find_packages(),
    install_requires=['pymusicxml >= 0.1.0', 'expenvelope >= 0.3.0', 'clockblocks >= 0.3.0',
                      'pyfluidsynth', 'sf2utils', 'python-osc'],
    extras_require={
        'lilypond': 'abjad==3.1',
        'midistream': 'python-rtmidi',
        'mouse and keyboard input': 'pynput'
    },
    package_data={
        'scamp': ['settings/*', 'soundfonts/*', 'thirdparty/libfluidsynth64.dll', 'thirdparty/libfluidsynth.dll',
                  'thirdparty/libfluidsynth.1.5.2.dylib']
    },
    classifiers=[
        "Programming Language :: Python :: 3.6",
        "License :: OSI Approved :: GNU General Public License v3 (GPLv3)",
        "Operating System :: OS Independent",
    ],
)
