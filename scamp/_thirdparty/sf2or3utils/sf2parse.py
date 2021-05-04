# sf2utils, SoundFont2 library
# Copyright (C) 2016  Olivier Jolly
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Lesser General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

# NOTE: Modified 5/3/2021 by Marc Evanstein <marc@marcevanstein.com> in order to allow parsing of .sf3 files
# (Only changes are in preset.py where `self.name == 'EOP'` is replaced by `self.name == 'EOP' or len(self.name) == 0`)
# Apparently, the .sf3 files (at least the MuseScore ones) use a blank name as a sentinel instead of "EOP"

import argparse
import logging
import sys

import io
import os
import struct
from collections import namedtuple

from .instrument import Sf2Instrument
from .preset import Sf2Preset
from .riffparser import RiffParser, ensure_chunk_size, from_cstr
from .sample import Sf2Sample

__date__ = '2016-01-07'
__updated__ = '2017-02-08'
__author__ = 'olivier@pcedev.com'


class Sf2Info(object):
    def __init__(self, raw_info):
        super(Sf2Info, self).__init__()

        # mandatory fields
        self.version = raw_info.get(b'ifil') or '<missing info>'
        self.sound_engine = from_cstr(raw_info.get(b'isng')) or '<missing info>'
        self.bank_name = from_cstr(raw_info.get(b'INAM')) or '<missing info>'

        if self.version is None:
            logging.warning("Missing mandatory version info")

        if self.sound_engine is None:
            logging.warning("Missing mandatory sound engine info")

        if self.bank_name is None:
            logging.warning("Missing mandatory bank name info")

        # optional fields
        self.rom_name = from_cstr(raw_info.get(b'irom'))
        self.rom_version = raw_info.get(b'iver')
        self.creation_date = from_cstr(raw_info.get(b'ICRD'))
        self.designers = from_cstr(raw_info.get(b'IENG'))
        self.intended_product = from_cstr(raw_info.get(b'IPRD'))
        self.copyright = from_cstr(raw_info.get(b'ICOP'))
        self.comments = from_cstr(raw_info.get(b'ICMT'))
        self.tool = from_cstr(raw_info.get(b'ISFT'))

    def __unicode__(self):
        result = u"Version: {0.version}\nSound engine: {0.sound_engine}\nBank name: {0.bank_name}\n"
        if self.rom_name is not None:
            result += u"Rom name: {0.rom_name}\n"
        if self.rom_version is not None:
            result += u"Rom version: {0.rom_version}\n"
        if self.creation_date is not None:
            result += u"Creation date: {0.creation_date}\n"
        if self.designers is not None:
            result += u"Sound designers and engineers: {0.designers}\n"
        if self.intended_product is not None:
            result += u"Intended product: {0.intended_product}\n"
        if self.copyright is not None:
            result += u"Copyright: {0.copyright}\n"
        if self.comments is not None:
            result += u"Comments: {0.comments}\n"
        if self.tool is not None:
            result += u"Tool: {0.tool}"
        return result.format(self)

    def __repr__(self):
        return self.__unicode__()


class Sf2Root(object):
    def __init__(self, info, sdta, pdta):
        self.info = info
        self.sdta = sdta
        self.pdta = pdta


class Sf2File(RiffParser):
    # Preset structures
    Phdr = namedtuple('Phdr', ['name', 'preset', 'bank', 'bag', 'library', 'genre', 'morphology'])
    Pbag = namedtuple('Pbag', ['gen', 'mod'])
    Pmod = namedtuple('Pmod', ['src_oper', 'dest_oper', 'amount', 'amount_src_oper', 'trans_oper'])
    Pgen = namedtuple('Pgen', ['oper', 'amount'])

    # Instrument structures
    Inst = namedtuple('Inst', ['name', 'bag'])
    Ibag = namedtuple('Ibag', ['gen', 'mod'])
    Imod = namedtuple('Imod', ['src_oper', 'dest_oper', 'amount', 'amount_src_oper', 'trans_oper'])
    Igen = namedtuple('Igen', ['oper', 'amount'])

    # Sample structure
    Shdr = namedtuple('Shdr',
                      ['sample_name', 'start', 'end', 'start_loop', 'end_loop', 'sample_rate', 'original_pitch',
                       'pitch_correction', 'sample_link', 'sample_type'])

    def __init__(self, sf2_file):
        super(Sf2File, self).__init__(sf2_file)
        self._instruments = None
        self._presets = None
        self._samples = None
        self._info = None
        self._raw = self.parse_next_chunk()
        self.simplify_tree()

    @property
    def instruments(self):
        if self._instruments is None:
            self._instruments = self.build_instruments()
        return self._instruments

    @property
    def presets(self):
        if self._presets is None:
            self._presets = self.build_presets()
        return self._presets

    @property
    def samples(self):
        if self._samples is None:
            self._samples = self.build_samples()
        return self._samples

    @property
    def info(self):
        if self._info is None:
            self._info = self.build_info()
        return self._info

    @property
    def raw(self):
        return self._raw

    def build_instruments(self):
        return [Sf2Instrument(self._raw.pdta, idx, self) for idx in range(len(self._raw.pdta['Inst']))]

    def build_presets(self):
        return [Sf2Preset(self._raw.pdta, idx, self) for idx in range(len(self._raw.pdta['Phdr']))]

    def build_samples(self):
        return [Sf2Sample(sample_header, self._raw.smpl_offset, self._raw.sm24_offset, self) for sample_header
                in self._raw.pdta['Shdr']]

    def build_info(self):
        return Sf2Info(self._raw.info)

    def simplify_tree(self):
        """simplify raw tree"""

        if len(self._raw) == 0:
            raise ValueError("Empty soundfont file")
        if len(self.raw) > 1:
            logging.warning("Multiple soundfont roots, using first one")
        self._raw = self._raw[0]

        # INFO section

        if len(self._raw.info) == 0:
            raise ValueError("No INFO section")
        if len(self._raw.info) > 1:
            logging.warning("Multiple INFO section, using first one")
        self._raw.info = self._raw.info[0]

        # SDTA section

        if len(self._raw.sdta) == 0:
            raise ValueError("No SDTA section")
        if len(self._raw.sdta) > 1:
            logging.warning("Multiple SDTA section, using first one")
        self._raw.sdta = self._raw.sdta[0]

        if len(self._raw.sdta) == 0:
            raise ValueError("No inside SDTA section")
        if len(self._raw.sdta) > 1:
            logging.warning("Multiple inside SDTA section, using first one")
        self._raw.sdta = self._raw.sdta[0]

        self._raw.smpl_offset = self._raw.sdta.get('smpl_offset')
        self._raw.sm24_offset = self._raw.sdta.get('sm24_offset')

        # PDTA section

        if len(self._raw.pdta) == 0:
            raise ValueError("No PDTA section")
        if len(self._raw.pdta) > 1:
            logging.warning("Multiple PDTA section, using first one")
        self._raw.pdta = self._raw.pdta[0]

        self._raw.pdta = {
            self.extract_type_from_list(subsection): subsection for subsection in self._raw.pdta if subsection
            }

    def extract_type_from_list(self, subsection):
        return type(subsection[0]).__name__

    # low level riff parsers

    @ensure_chunk_size(4)
    def parse_version_chunk(self, chunk_id):
        major, minor = struct.unpack(r'<HH', self.read(4))
        return chunk_id, "{:.2}".format(major + minor / 100.)

    def parse_sfbk_chunk(self, chunk_id):
        info_list = self.parse_next_chunk()
        sdta_list = self.parse_next_chunk()
        pdta_list = self.parse_next_chunk()
        return Sf2Root(info=info_list, sdta=sdta_list, pdta=pdta_list)

    def parse_smpl_chunk(self, chunk_id):
        chunk_size = self.parse_chunk_size()
        # keep track of smpl_offset
        smpl_offset = self.tell()
        self.seek(chunk_size, io.SEEK_CUR)
        return {'smpl_offset': smpl_offset}

    def parse_sm24_chunk(self, chunk_id):
        chunk_size = self.parse_chunk_size()
        # keep track of sm24_offset
        sm24_offset = self.tell()
        self.seek(chunk_size, io.SEEK_CUR)
        return {'sm24_offset': sm24_offset}

    def parse_phdr_chunk(self, chunk_id):
        return self.parse_sized_array(chunk_id, self.Phdr, 38, r'<20sHHHIII')

    def parse_pbag_chunk(self, chunk_id):
        return self.parse_sized_array(chunk_id, self.Pbag, 4, r'<HH')

    def parse_pmod_chunk(self, chunk_id):
        return self.parse_sized_array(chunk_id, self.Pmod, 10, r'<HHHHH')

    def parse_pgen_chunk(self, chunk_id):
        return self.parse_sized_array(chunk_id, self.Pgen, 4, r'<HH')

    def parse_inst_chunk(self, chunk_id):
        return self.parse_sized_array(chunk_id, self.Inst, 22, r'<20sH')

    def parse_ibag_chunk(self, chunk_id):
        return self.parse_sized_array(chunk_id, self.Ibag, 4, r'<HH')

    def parse_imod_chunk(self, chunk_id):
        return self.parse_sized_array(chunk_id, self.Imod, 10, r'<HHHHH')

    def parse_igen_chunk(self, chunk_id):
        return self.parse_sized_array(chunk_id, self.Igen, 4, r'<HH')

    def parse_shdr_chunk(self, chunk_id):
        return self.parse_sized_array(chunk_id, self.Shdr, 46, r'<20sIIIIIbBHH')

    parser_map = {
        b'RIFF': RiffParser.parse_riff_chunk,
        b'LIST': RiffParser.parse_riff_chunk,

        b'INFO': RiffParser.parse_fixed_array_chunk,
        b'ifil': parse_version_chunk,
        b'isng': RiffParser.parse_short_str_chunk,
        b'INAM': RiffParser.parse_short_str_chunk,
        b'irom': RiffParser.parse_short_str_chunk,
        b'iver': parse_version_chunk,
        b'ICRD': RiffParser.parse_short_str_chunk,
        b'IENG': RiffParser.parse_short_str_chunk,
        b'IPRD': RiffParser.parse_short_str_chunk,
        b'ICOP': RiffParser.parse_short_str_chunk,
        b'ICMT': RiffParser.parse_long_str_chunk,
        b'ISFT': RiffParser.parse_short_str_chunk,

        b'sdta': RiffParser.parse_fixed_array_chunk,
        b'pdta': RiffParser.parse_fixed_array_chunk,
    }

    def pretty_print(self, prefix=u''):
        return u"\n".join([self.info.__unicode__()] + [preset.pretty_print() for preset in self.presets])


def main(argv=None):
    program_name = os.path.basename(sys.argv[0])
    program_version = "v0.9"
    program_build_date = "%s" % __updated__

    program_version_string = 'sf2parse %s (%s)' % (program_version, program_build_date)
    program_longdesc = '''Parse sf2 file and display info about it'''
    program_license = "LGPL v3+ 2016-2017 Olivier Jolly"

    if argv is None:
        argv = sys.argv[1:]

    try:
        parser = argparse.ArgumentParser(epilog=program_longdesc,
                                         description=program_license)
        parser.add_argument("-d", "--debug", dest="debug", action="store_true",
                            default=False,
                            help="debug parsing [default: %(default)s]")
        parser.add_argument("-v", "--version", action="version", version=program_version_string)

        parser.add_argument("sf2_filename", help="input file in SoundFont2 format", nargs="+")

        # process options
        opts = parser.parse_args(argv)

    except Exception as e:
        indent = len(program_name) * " "
        sys.stderr.write(program_name + ": " + repr(e) + "\n")
        sys.stderr.write(indent + "  for help use --help")
        return 2

    if opts.debug:
        logging.root.setLevel(logging.DEBUG)
    else:
        logging.root.setLevel(logging.INFO)

    for single_sf2_filename in opts.sf2_filename:
        with open(single_sf2_filename, "rb") as sf2_file:
            sf2 = Sf2File(sf2_file)

            print(sf2.pretty_print())

            # pprint.pprint(sf2.samples)
            # pprint.pprint(sf2.presets)
            # pprint.pprint(sf2.instruments)

    return 0


if __name__ == "__main__":
    sys.exit(main())
