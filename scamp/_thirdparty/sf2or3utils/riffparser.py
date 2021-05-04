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

import io
import logging
import struct


class RiffParseException(Exception):
    pass


def insert_generator_in_result(generator, result):
    next_chunk = next(generator)

    # if generator returns None, there is nothing more to parse
    if next_chunk is None:
        raise StopIteration

    # if tuple, insert as dict entry
    if isinstance(next_chunk, tuple):
        subchunk_name, subchunk_content = next_chunk
        if result is None:
            result = {}
        elif not isinstance(result, dict):
            raise RiffParseException(
                "internal error, change of chunk nature (from list to dict on chunk '{}')".format(subchunk_name))

        result[subchunk_name] = subchunk_content

    else:  # if not tuple, insert as list entry
        if result is None:
            result = []
        elif not isinstance(result, list):
            raise RiffParseException("internal error, change of chunk nature (from dict to dict)")

        result.append(next_chunk)

    return result


def parse_fixed_array(func):
    def inner(self, *args, **kwargs):
        result = None

        generator = func(self, *args, **kwargs)

        while True:
            old_offset = self.tell()

            try:
                result = insert_generator_in_result(generator, result)
            except StopIteration:
                logging.debug("no more data expected for the current list chunk")
                break

            if self.tell() == old_offset:
                logging.warning(
                    "internal error, chunk parser did not consume any data. "
                    "Aborting current list parsing to avoid deadlock")
                break

        return result

    return inner


def from_cstr(b):
    if b is None:
        return None

    result, _, _ = b.partition(b'\0')

    # latin1 is a common superset of ascii to handle strings which might err in the non ascii range
    return result.decode('latin1', errors='replace')


def parse_list(func):
    def inner(self, *args, **kwargs):
        result = None

        chunk_size, = struct.unpack(r'<I', self.read(4))
        chunk_end_offset = self.tell() + chunk_size

        generator = func(self, *args, **kwargs)

        # mark all read beyond this offset as returning no data
        self.push_list_end_offset(chunk_end_offset)

        try:
            while True:
                old_offset = self.tell()

                try:
                    result = insert_generator_in_result(generator, result)
                except StopIteration:
                    logging.debug("no more data expected for the current list chunk")
                    break

                if self.tell() == old_offset:
                    logging.warning(
                        "internal error, chunk parser did not consume any data. "
                        "Aborting current list parsing to avoid deadlock")
                    break
        finally:
            # now allows read to keep going
            self.pop_list_end_offset()

        # if the current file position isn't exactly as expected from the chunk list size, warn about the situation
        # and try to fix it as much as possible
        if self.tell() < chunk_end_offset:
            logging.warning("corrupted but salvageable file, list chunk was not fully consumed (remain %d byte(s))" % (
                chunk_end_offset - self.tell()))
            self.seek(chunk_end_offset)
        elif self.tell() > chunk_end_offset:
            logging.warning("corrupted file, incoherent LIST/RIFF chunk size (overlap %d byte(s))" % (
                self.tell() - chunk_end_offset))
            self.seek(chunk_end_offset)

        return result

    return inner


# noinspection PyPep8Naming
class ensure_chunk_name():
    def __init__(self, name):
        self.name = name

    def __call__(self, func):
        def inner(sf2parser, *args, **kwargs):
            chunk_name, = struct.unpack(r'4s', sf2parser.read(4))
            if chunk_name != self.name:
                raise RiffParseException(
                    "found wrong subchunk (expected '{}', got '{}')".format(self.name, chunk_name))
            return func(sf2parser, *args, **kwargs)

        return inner


# noinspection PyPep8Naming
class ensure_chunk_size():
    def __init__(self, size):
        self.size = size

    def __call__(self, func):
        def inner(sf2parser, *args, **kwargs):
            chunk_size, = struct.unpack(r'<I', sf2parser.read(4))
            if chunk_size != self.size:
                raise RiffParseException(
                    "found chunk of wrong size (expected '{}', got '{}')".format(self.size, chunk_size))
            return func(sf2parser, *args, **kwargs)

        return inner


class RiffParser(object):
    parser_map = {}

    def __init__(self, riff_file):
        self.riff_file = riff_file
        self.list_end_offset = []

    def read(self, size, pos=None):

        if len(self.list_end_offset) > 0 and pos is not None:
            logging.error(
                "Unsupported file position change while list with known size is being read. "
                "Probable API use error. Expect the unexpected!")

        if pos is not None:
            self.seek(pos)

        # ensure that when reading a list, we don't go beyond its boundary
        # this enables nested lists of arbitrary content to be parsed
        if len(self.list_end_offset) > 0 and self.tell() >= self.list_end_offset[len(self.list_end_offset) - 1]:
            return b''
        return self.riff_file.read(size)

    def tell(self):
        return self.riff_file.tell()

    def seek(self, offset, whence=io.SEEK_SET):
        self.riff_file.seek(offset, whence)

    def push_list_end_offset(self, chunk_end_offset):
        self.list_end_offset.append(chunk_end_offset)

    def pop_list_end_offset(self):
        self.list_end_offset.pop()

    # generic parsers

    def parse_next_chunk(self):
        data = self.read(4)

        if len(data) < 4:
            return None

        chunk_id, = struct.unpack(r'4s', data)
        logging.debug("found chunk [%s]" % chunk_id)

        chunk_parser = self.parser_map.get(chunk_id)
        if chunk_parser is None:

            # if no explicit parser was associated with this chunk_id, try
            # to use a parser method based on its name
            try:
                parser_auto_name = "parse_{}_chunk".format(chunk_id.decode('ascii'))
                parser_method = getattr(self, parser_auto_name)
            except AttributeError:
                logging.warning("unknown chunk [%s]" % chunk_id)
                return None
            except UnicodeDecodeError:
                logging.warning("invalid chunk [%s]" % chunk_id)
                return None

            return parser_method(chunk_id=chunk_id)

        return chunk_parser(self, chunk_id=chunk_id)

    @parse_list
    def parse_riff_chunk(self, chunk_id):
        while True:
            yield self.parse_next_chunk()

    @parse_fixed_array
    def parse_fixed_array_chunk(self, chunk_id):
        while True:
            yield self.parse_next_chunk()

    def parse_short_str_chunk(self, chunk_id):
        return chunk_id, self.read(self.parse_chunk_size(max_size=256))

    def parse_long_str_chunk(self, chunk_id):
        return chunk_id, self.read(self.parse_chunk_size(max_size=65536))

    def parse_sized_array(self, chunk_id, cls, cls_len, pack_format):
        result = []

        # TODO ensure size is a multiple of pack_format
        for count in range(int(self.parse_chunk_size() / cls_len)):
            result.append(cls(*struct.unpack(pack_format, self.read(cls_len))))
        return result

    def parse_chunk_size(self, max_size=None):
        chunk_size, = struct.unpack("<I", self.read(4))

        if max_size is not None:
            if chunk_size > max_size:
                raise RiffParseException(
                    "chunk size is too large (expected <= {}, got {})".format(max_size, chunk_size))

        return chunk_size
