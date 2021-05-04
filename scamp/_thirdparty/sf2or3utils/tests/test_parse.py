import os

from sf2utils.sf2parse import Sf2File


def open_file(filename):
    return open(os.path.join(os.path.dirname(os.path.abspath(__file__)), filename), 'rb')


def test_basic_parse():
    """make sure that parsing a simple file loads the right amount of instruments, samples and presets"""
    with open_file('sf2utils_test.sf2') as file:
        sf2_file = Sf2File(file)
        assert len(sf2_file.instruments) == 3
        assert len(sf2_file.samples) == 3
        assert len(sf2_file.presets) == 2

        assert sf2_file.instruments[0].name == 'inst1'
        assert sf2_file.instruments[1].name == 'inst2'

        assert sf2_file.presets[0].bank == 13
        assert sf2_file.presets[0].preset == 37
