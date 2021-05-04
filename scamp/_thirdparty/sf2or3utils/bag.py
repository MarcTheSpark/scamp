from .generator import Sf2Gen
from .modulator import Sf2Mod


# noinspection PyPep8Naming
class search_gen(object):
    def __init__(self, tag):
        self.tag = tag

    def __call__(self, func):
        def inner(bag):
            try:
                return func(bag, bag[self.tag])
            except KeyError:
                return None

        return inner


class Sf2Bag(object):
    def __init__(self, hydra_header, idx, parent, hydra_bag_name, hydra_mod_name, hydra_gen_name):
        bag_header = hydra_header[hydra_bag_name][idx]

        self.idx = idx
        self.mod_idx = bag_header.mod
        self.gen_idx = bag_header.gen

        self.mod_size = hydra_header[hydra_bag_name][idx + 1].mod - self.mod_idx
        self.gen_size = hydra_header[hydra_bag_name][idx + 1].gen - self.gen_idx

        self.mods = self.build_mods(hydra_header, hydra_mod_name)
        self.gens = self.build_gens(hydra_header, hydra_gen_name)

        self.parent = parent

    def build_mods(self, hydra_header, hydra_mod_name):
        return [Sf2Mod(mod_header) for mod_header in
                hydra_header[hydra_mod_name][self.mod_idx:self.mod_idx + self.mod_size]]

    def build_gens(self, hydra_header, hydra_gen_name):
        return {gen_header.oper: Sf2Gen(gen_header) for gen_header in
                hydra_header[hydra_gen_name][self.gen_idx:self.gen_idx + self.gen_size]}

    @property
    def unused_gens(self):
        result = set()
        for gen in self.gens.values():
            if not getattr(gen, 'consumed', False):
                result.add(gen)
        return result

    @property
    @search_gen(Sf2Gen.OPER_INSTRUMENT)
    def instrument(self, gen):
        try:
            return self.parent.parent.instruments[gen.word]
        except AttributeError:
            return None

    @property
    @search_gen(Sf2Gen.OPER_KEY_RANGE)
    def key_range(self, gen):
        return gen.amount_as_sorted_range

    @property
    @search_gen(Sf2Gen.OPER_VEL_RANGE)
    def velocity_range(self, gen):
        return gen.amount_as_sorted_range

    @property
    @search_gen(Sf2Gen.OPER_SAMPLE_ID)
    def sample(self, gen):
        return self.parent.parent.samples[gen.word]

    @property
    @search_gen(Sf2Gen.OPER_SAMPLE_MODES)
    def sample_loop(self, gen):
        return gen.sample_loop

    @property
    @search_gen(Sf2Gen.OPER_SAMPLE_MODES)
    def sample_loop_on_noteoff(self, gen):
        return gen.sample_loop_on_noteoff

    @property
    @search_gen(Sf2Gen.OPER_PAN)
    def pan(self, gen):
        return max(-0.5, min(0.5, gen.pan))

    @property
    @search_gen(Sf2Gen.OPER_REVERB_EFFECTS_SEND)
    def reverb_send(self, gen):
        return gen.send_amount

    @property
    @search_gen(Sf2Gen.OPER_CHORUS_EFFECTS_SEND)
    def chorus_send(self, gen):
        return gen.send_amount

    @property
    @search_gen(Sf2Gen.OPER_COARSE_TUNE)
    def tuning(self, gen):
        return gen.short

    @property
    @search_gen(Sf2Gen.OPER_FINE_TUNE)
    def fine_tuning(self, gen):
        return gen.short

    @property
    @search_gen(Sf2Gen.OPER_ATTACK_VOL_ENV)
    def volume_envelope_attack(self, gen):
        return gen.cents

    @property
    @search_gen(Sf2Gen.OPER_DECAY_VOL_ENV)
    def volume_envelope_decay(self, gen):
        return gen.cents

    @property
    @search_gen(Sf2Gen.OPER_HOLD_VOL_ENV)
    def volume_envelope_hold(self, gen):
        return gen.cents

    @property
    @search_gen(Sf2Gen.OPER_SUSTAIN_VOL_ENV)
    def volume_envelope_sustain(self, gen):
        return gen.positive_attenuation * 10.

    @property
    @search_gen(Sf2Gen.OPER_RELEASE_VOL_ENV)
    def volume_envelope_release(self, gen):
        return gen.cents

    @property
    @search_gen(Sf2Gen.OPER_OVERRIDING_ROOT_KEY)
    def base_note(self, gen):
        return gen.word

    @property
    @search_gen(Sf2Gen.OPER_INITIAL_FILTER_CUTOFF)
    def lp_cutoff(self, gen):
        return gen.absolute_cents

    @property
    @search_gen(Sf2Gen.OPER_SCALE_TUNING)
    def midi_key_pitch_influence(self, gen):
        return gen.word

    @property
    def cooked_loop_start(self):
        try:
            result = self.sample.start_loop
        except AttributeError:
            result = 0

        try:
            result += self[Sf2Gen.OPER_START_LOOP_ADDR_OFFSET].short
        except KeyError:
            pass

        try:
            result += self[Sf2Gen.OPER_START_LOOP_ADDR_COARSE_OFFSET].short * 32768
        except KeyError:
            pass

        return result

    @property
    def cooked_loop_end(self):
        try:
            result = self.sample.end_loop
        except AttributeError:
            result = 0

        try:
            result += self[Sf2Gen.OPER_END_LOOP_ADDR_OFFSET].short
        except KeyError:
            pass

        try:
            result += self[Sf2Gen.OPER_END_LOOP_ADDR_COARSE_OFFSET].short * 32768
        except KeyError:
            pass

        return result

    def __getitem__(self, item):
        try:
            gen = self.gens[item]
            gen.consumed = True
            return gen
        except KeyError as e:
            raise e

    def pretty_print(self, prefix=u''):
        return u"\n".join([prefix + self.__unicode__()] +
                          [mod.pretty_print(prefix + u'\t') for mod in self.mods] +
                          [gen.pretty_print(prefix + u'\t') for gen in self.gens.values()])

    def __unicode__(self):
        return u"Bag #{0.idx}, {0.mod_size} modulator(s) from {0.mod_idx}, " \
               u"{0.gen_size} generator(s) from {0.gen_idx}".format(self)

    def __repr__(self):
        return self.__unicode__()
