import struct


class Sf2Gen(object):
    OPER_START_ADDR_OFFSET = 0
    OPER_END_ADDR_OFFSET = 1
    OPER_START_LOOP_ADDR_OFFSET = 2
    OPER_END_LOOP_ADDR_OFFSET = 3
    OPER_START_ADDR_COARSE_OFFSET = 4
    OPER_MOD_LFO_TO_PITCH = 5
    OPER_VIB_LFO_TO_PITCH = 6
    OPER_MOD_ENV_TO_PITCH = 7
    OPER_INITIAL_FILTER_CUTOFF = 8
    OPER_INITIAL_FILTER_Q = 9
    OPER_MOD_LFO_TO_FILTER_CUTOFF = 10
    OPER_MOD_ENV_TO_FILTER_CUTOFF = 11
    OPER_END_ADDR_COARSE_OFFSET = 12
    OPER_MOD_LFO_TO_VOLUME = 13
    OPER_CHORUS_EFFECTS_SEND = 15
    OPER_REVERB_EFFECTS_SEND = 16
    OPER_PAN = 17
    OPER_DELAY_MOD_LFO = 21
    OPER_FREQ_MOD_LFO = 22
    OPER_DELAY_VIB_LFO = 23
    OPER_FREQ_VIB_LFO = 24
    OPER_DELAY_MOD_ENV = 25
    OPER_ATTACK_MOD_ENV = 26
    OPER_HOLD_MOD_ENV = 27
    OPER_DECAY_MOD_ENV = 28
    OPER_SUSTAIN_MOD_ENV = 29
    OPER_RELEASE_MOD_ENV = 30
    OPER_DELAY_VOL_ENV = 33
    OPER_ATTACK_VOL_ENV = 34
    OPER_HOLD_VOL_ENV = 35
    OPER_DECAY_VOL_ENV = 36
    OPER_SUSTAIN_VOL_ENV = 37
    OPER_RELEASE_VOL_ENV = 38
    OPER_KEYNUM_TO_VOL_ENV_HOLD = 39
    OPER_KEYNUM_TO_VOL_ENV_DECAY = 40
    OPER_INSTRUMENT = 41
    OPER_KEY_RANGE = 43
    OPER_VEL_RANGE = 44
    OPER_START_LOOP_ADDR_COARSE_OFFSET = 45
    OPER_INITIAL_ATTENUATION = 48
    OPER_END_LOOP_ADDR_COARSE_OFFSET = 50
    OPER_COARSE_TUNE = 51
    OPER_FINE_TUNE = 52
    OPER_SAMPLE_ID = 53
    OPER_SAMPLE_MODES = 54
    OPER_SCALE_TUNING = 56
    OPER_EXCLUSIVE_CLASS = 57
    OPER_OVERRIDING_ROOT_KEY = 58

    def __init__(self, gen_header):
        self.oper = gen_header.oper
        self.amount = gen_header.amount

    @property
    def word(self):
        return self.amount

    @property
    def short(self):
        return struct.unpack('h', struct.pack('H', self.amount))[0]

    @property
    def amount_hi_byte(self):
        return struct.unpack('bb', struct.pack('H', self.amount))[1]

    @property
    def amount_lo_byte(self):
        return struct.unpack('bb', struct.pack('H', self.amount))[0]

    @property
    def amount_as_sorted_range(self):
        return sorted(struct.unpack('bb', struct.pack('H', self.amount)))

    @property
    def amount_as_bytes(self):
        return struct.unpack('bb', struct.pack('H', self.amount))

    @property
    def sample_loop(self):
        return self.amount_lo_byte & 1 != 0

    @property
    def sample_loop_on_noteoff(self):
        return self.amount_lo_byte & 2 != 0

    @property
    def coarse_offset(self):
        return 32768 * self.short

    @property
    def pan(self):
        return self.short / 10.

    @property
    def send_amount(self):
        return self.word / 10.

    @property
    def attenuation(self):
        """return the attenuation in Bells"""
        return self.word / 100.

    @property
    def absolute_cents(self):
        return 8.176 * 2 ** (self.short / 1200.)

    @property
    def positive_attenuation(self):
        """return the attenuation in Bell (negative values are considered 0)"""
        return max(0, self.short / 100.)

    @property
    def cents(self):
        return 2 ** (self.short / 1200.)

    @property
    def sustain_decrease(self):
        return min(1000, self.word)

    # noinspection PyTypeChecker
    def pretty_print(self, prefix=u''):
        if self.oper == self.OPER_START_ADDR_OFFSET:
            return prefix + "sample start offset {}".format(self.short)
        elif self.oper == self.OPER_END_ADDR_OFFSET:
            return prefix + "sample end offset {}".format(self.short)
        elif self.oper == self.OPER_START_LOOP_ADDR_OFFSET:
            return prefix + "sample loop start offset {}".format(self.short)
        elif self.oper == self.OPER_END_LOOP_ADDR_OFFSET:
            return prefix + "sample loop end offset {}".format(self.short)
        elif self.oper == self.OPER_START_ADDR_COARSE_OFFSET:
            return prefix + "sample start offset (coarse) {}".format(self.coarse_offset)
        elif self.oper == self.OPER_MOD_LFO_TO_PITCH:
            return prefix + "modulation LFO influence on pitch {:.4}%".format(self.cents)
        elif self.oper == self.OPER_VIB_LFO_TO_PITCH:
            return prefix + "modulation vibrato influence on pitch {:.4}%".format(self.cents)
        elif self.oper == self.OPER_MOD_ENV_TO_PITCH:
            return prefix + "modulation envelope influence on pitch {:.4}%".format(self.cents)
        elif self.oper == self.OPER_INITIAL_FILTER_CUTOFF:
            return prefix + "initial LP filter cutoff {}Hz".format(self.absolute_cents)
        elif self.oper == self.OPER_INITIAL_FILTER_Q:
            return prefix + "initial LP filter Q {}dB".format(self.attenuation * 10.)
        elif self.oper == self.OPER_MOD_LFO_TO_FILTER_CUTOFF:
            return prefix + "modulation LFO influence on LP filter cutoff {}".format(self.cents)
        elif self.oper == self.OPER_MOD_ENV_TO_FILTER_CUTOFF:
            return prefix + "modulation envelope influence on LP filter cutoff {}".format(self.cents)
        elif self.oper == self.OPER_END_ADDR_COARSE_OFFSET:
            return prefix + "sample end offset (coarse) {}".format(self.coarse_offset)
        elif self.oper == self.OPER_MOD_LFO_TO_VOLUME:
            return prefix + "modulation LFO influence on volume {}dB".format(self.attenuation * 10.)
        elif self.oper == self.OPER_CHORUS_EFFECTS_SEND:
            return prefix + "chorus send {:.4}%".format(self.send_amount)
        elif self.oper == self.OPER_REVERB_EFFECTS_SEND:
            return prefix + "reverb send {:.4}%".format(self.send_amount)
        elif self.oper == self.OPER_PAN:
            return prefix + "pan {:1}%".format(self.pan)
        elif self.oper == self.OPER_DELAY_MOD_LFO:
            return prefix + "modulation LFO delay {:.4}s".format(self.cents)
        elif self.oper == self.OPER_FREQ_MOD_LFO:
            return prefix + "modulation LFO triangular period {:.4}Hz".format(self.absolute_cents)
        elif self.oper == self.OPER_DELAY_VIB_LFO:
            return prefix + "vibrato LFO delay {:.4}s".format(self.cents)
        elif self.oper == self.OPER_FREQ_VIB_LFO:
            return prefix + "vibrato LFO triangular period {:.4}Hz".format(self.absolute_cents)
        elif self.oper == self.OPER_DELAY_MOD_ENV:
            return prefix + "delay modulation envelope {:.4}s".format(self.cents)
        elif self.oper == self.OPER_ATTACK_MOD_ENV:
            return prefix + "attack modulation envelope {:.4}s".format(self.cents)
        elif self.oper == self.OPER_HOLD_MOD_ENV:
            return prefix + "hold modulation envelope {:.4}s".format(self.cents)
        elif self.oper == self.OPER_DECAY_MOD_ENV:
            return prefix + "decay modulation envelope {:.4}s".format(self.cents)
        elif self.oper == self.OPER_SUSTAIN_MOD_ENV:
            return prefix + "sustain modulation decrease {}%".format(self.sustain_decrease)
        elif self.oper == self.OPER_RELEASE_MOD_ENV:
            return prefix + "release modulation envelope {:.4}%".format(self.cents)
        elif self.oper == self.OPER_DELAY_VOL_ENV:
            return prefix + "delay volume envelope {:.4}s".format(self.cents)
        elif self.oper == self.OPER_ATTACK_VOL_ENV:
            return prefix + "attack volume envelope {:.4}s".format(self.cents)
        elif self.oper == self.OPER_HOLD_VOL_ENV:
            return prefix + "hold volume envelope {:.4}s".format(self.cents)
        elif self.oper == self.OPER_DECAY_VOL_ENV:
            return prefix + "decay volume envelope {:.4}s".format(self.cents)
        elif self.oper == self.OPER_SUSTAIN_VOL_ENV:
            return prefix + "sustain decrease {:.4}dB".format(self.positive_attenuation * 10.)
        elif self.oper == self.OPER_RELEASE_VOL_ENV:
            return prefix + "release volume envelope {:.4}s".format(self.cents)
        elif self.oper == self.OPER_KEYNUM_TO_VOL_ENV_HOLD:
            return prefix + "MIDI key influence on hold volume envelope {}s per key number".format(self.cents)
        elif self.oper == self.OPER_KEYNUM_TO_VOL_ENV_DECAY:
            return prefix + "MIDI key influence on decay volume envelope {}s per key number".format(self.cents)
        elif self.oper == self.OPER_INSTRUMENT:
            return prefix + "instrument #{}".format(self.word)
        elif self.oper == self.OPER_KEY_RANGE:
            return prefix + "key range [{}, {}]".format(*self.amount_as_sorted_range)
        elif self.oper == self.OPER_VEL_RANGE:
            return prefix + "velocity range [{}, {}]".format(*self.amount_as_sorted_range)
        elif self.oper == self.OPER_START_LOOP_ADDR_COARSE_OFFSET:
            return prefix + "sample start loop offset (coarse) {}".format(self.coarse_offset)
        elif self.oper == self.OPER_INITIAL_ATTENUATION:
            return prefix + "initial attenuation {:.4}dB".format(self.attenuation * 10.)
        elif self.oper == self.OPER_END_LOOP_ADDR_COARSE_OFFSET:
            return prefix + "sample end loop offset (coarse) {}".format(self.coarse_offset)
        elif self.oper == self.OPER_COARSE_TUNE:
            return prefix + "pitch offset {} semitone(s)".format(self.short)
        elif self.oper == self.OPER_FINE_TUNE:
            return prefix + "pitch offset {} cent(s)".format(self.short)
        elif self.oper == self.OPER_SAMPLE_ID:
            return prefix + "sample #{}".format(self.word)
        elif self.oper == self.OPER_SAMPLE_MODES:
            if self.sample_loop:
                if self.sample_loop_on_noteoff:
                    return prefix + "sample loop (even after note-off)"
                else:
                    return prefix + "sample loop (until note-off)"
            else:
                return prefix + "no sample loop"
        elif self.oper == self.OPER_SCALE_TUNING:
            return prefix + "MIDI key influence on pitch {}%".format(self.word)
        elif self.oper == self.OPER_EXCLUSIVE_CLASS:
            return prefix + "exclusive class {}".format(self.word)
        elif self.oper == self.OPER_OVERRIDING_ROOT_KEY:
            return prefix + "MIDI root key override {}".format(self.word)
        return prefix + self.__unicode__()

    def __unicode__(self):
        return u"Generator oper {0.oper} amount {0.amount}".format(self)

    def __repr__(self):
        return self.__unicode__()
