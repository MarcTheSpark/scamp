import logging
import sys
import wave
from contextlib import closing
import numpy as np
from .riffparser import from_cstr


def byteswap_np(fragment, width):
    """
    Reverse the byte order in each sample of the given fragment using NumPy. Replaces audioop.byteswap for python>3.13.
    Written by ChatGPT o3-mini

    :param fragment: A bytes object containing the audio data.
    :param width: The number of bytes per sample.
    :return: A new bytes object with each sample's bytes reversed.
    :raises ValueError: If len(fragment) is not a multiple of width.
    """
    if width == 1:
        return fragment

    if len(fragment) % width != 0:
        raise ValueError("Length of fragment is not a multiple of width")

    # Create a NumPy array of type uint8 from the input bytes
    arr = np.frombuffer(fragment, dtype=np.uint8)

    # Reshape into rows of 'width' bytes (each row is a sample)
    arr = arr.reshape(-1, width)

    # Reverse the bytes in each sample (i.e., reverse each row)
    swapped = arr[:, ::-1]

    return swapped.tobytes()


class Sf2Sample(object):
    DEFAULT_PITCH = 60
    UNPITCHED_PITCH = 255
    INVALID_LOW_PITCH = 128
    INVALID_HIGH_PITCH = 254

    CHANNEL_MONO = 1
    CHANNEL_RIGHT = 2
    CHANNEL_LEFT = 4
    CHANNEL_MASK = 0x07

    def __init__(self, sample_header, smpl_offset, sm24_offset, sf2parser):
        self.name = from_cstr(sample_header.sample_name)

        # don't process the sentinel sample
        if self.name == 'EOS':
            return

        self.smpl_offset = smpl_offset
        self.sm24_offset = sm24_offset
        self.sf2parser = sf2parser

        self.start = sample_header.start
        self.end = sample_header.end
        self.start_loop = sample_header.start_loop - self.start
        self.end_loop = sample_header.end_loop - self.start
        self.sample_rate = sample_header.sample_rate
        self.original_pitch = sample_header.original_pitch if sample_header.original_pitch <= 127 else 60
        self.pitch_correction = sample_header.pitch_correction
        self.in_rom = sample_header.sample_type & 0x8000

        self.sample_type = sample_header.sample_type & Sf2Sample.CHANNEL_MASK
        if self.sample_type == 0:
            logging.warning("Sample %s has unspecified mono/stereo type", self.name)

        if self.is_mono:
            self.sample_link = None
        else:
            self.sample_link = sample_header.sample_link

        if self.end < self.start + 48:
            logging.warning("Sample %s is too small (%d sample(s) while expected minimum is 48)", self.name,
                            self.end - self.start)

        if self.start_loop < 7:
            logging.warning("Sample %s has loop starting too early", self.name)

        if self.end_loop < 31:
            logging.warning("Sample %s has loop too short", self.name)

        if self.end_loop > self.end - 7:
            logging.warning("Sample %s has loop ending too late", self.name)

        if Sf2Sample.INVALID_LOW_PITCH <= self.original_pitch <= Sf2Sample.INVALID_HIGH_PITCH:
            logging.warning("Sample %s has invalid original pitch (%d while forbidden range is [%d, %d])",
                            self.name, self.original_pitch, Sf2Sample.INVALID_LOW_PITCH,
                            Sf2Sample.INVALID_HIGH_PITCH)
            self.original_pitch = Sf2Sample.DEFAULT_PITCH

        # make unpitched samples back to the default pitch
        if self.original_pitch == Sf2Sample.UNPITCHED_PITCH:
            self.original_pitch = Sf2Sample.DEFAULT_PITCH

    @property
    def is_mono(self):
        return self.sample_type & Sf2Sample.CHANNEL_MONO

    @property
    def is_left(self):
        return self.sample_type & Sf2Sample.CHANNEL_LEFT

    @property
    def duration(self):
        return self.end - self.start

    @property
    def loop_duration(self):
        return self.end_loop - self.start_loop

    @property
    def raw_sample_data(self):
        """return native endian linear buffer of samples (as expected by python wavfile)"""

        higher_part = self.sf2parser.read(self.duration * 2, pos=self.smpl_offset + self.start * 2)

        # soundfont smpl samples are packed as 16bits little endian, switch order if our system is big endian
        if sys.byteorder == 'big':
            higher_part = byteswap_np(higher_part, 2)

        # in 16bits only, return the top 16bits
        if self.sm24_offset is None:
            return higher_part

        # else read the complementary 8bits
        lower_part = self.sf2parser.read(self.duration, pos=self.sm24_offset + self.start)

        # and merge the result
        result = bytearray(self.duration * 3)
        for idx in range(self.duration):
            result[idx * 3: idx * + 1] = higher_part[idx * 2: idx * 2 + 1]
            result[idx * 3 + 2] = lower_part[idx]

        return result

    @property
    def sample_width(self):
        if self.sm24_offset is not None:
            return 3
        return 2

    def export(self, file):

        if self.smpl_offset is None:
            raise ValueError('no SMPL section found in Soundfont file, aborting sample export')

        # use of ''closing'' here allows the same code to be ran on python2 and python3
        with closing(wave.open(file, 'w')) as wav_file:
            wav_file.setnchannels(1)
            wav_file.setsampwidth(self.sample_width)
            wav_file.setframerate(self.sample_rate)
            wav_file.writeframes(self.raw_sample_data)

    def __unicode__(self):

        if self.name == 'EOS':
            return u"Sample EOS"

        result = u"Sample {0.name} at {0.start} + {0.duration} (loop at {0.start_loop} + {0.loop_duration}) " \
                 u"sampled at {0.sample_rate}Hz "

        if self.pitch_correction:
            result += u"replay correction {0.pitch_correction} cent(s) "

        if self.original_pitch != Sf2Sample.DEFAULT_PITCH:
            result += u"original pitch {0.original_pitch} "

        if self.is_mono:
            result += u"MONO"
        else:
            if self.is_left:
                result += u"LEFT"
            else:
                result += u"RIGHT"

            if self.sample_link:
                result += u" linked to sample {0.sample_link}"
        return result.format(self)

    def __repr__(self):
        return self.__unicode__()
