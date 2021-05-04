import logging

from .bag import Sf2Bag
from .riffparser import from_cstr


class Sf2Preset(object):
    def __init__(self, hydra_header, idx, sf2parser):
        preset_header = hydra_header['Phdr'][idx]

        self.name = from_cstr(preset_header.name)

        # don't process the sentinel item
        if self.name == 'EOP' or len(self.name) == 0:
            self.bags = []
            return

        self.hydra_header = hydra_header

        self.preset = preset_header.preset
        self.bank = preset_header.bank

        self.bag_idx = preset_header.bag
        self.bag_size = hydra_header['Phdr'][idx + 1].bag - self.bag_idx

        if self.bank > 128:
            logging.warning("Bag %s has invalid bank number (%d while expected <= 128)", self.name, self.bank)

        self.bags = self.build_bags()

        self.sf2parser = sf2parser

    def build_bags(self):
        return [Sf2Bag(self.hydra_header, idx, self, 'Pbag', 'Pmod', 'Pgen') for idx in
                range(self.bag_idx, self.bag_idx + self.bag_size)]

    @property
    def gens(self):
        for bag in self.bags:
            for gen in bag.gens:
                yield gen

    @property
    def instruments(self):
        if len(self.bags) <= 0:
            yield None, None, None
        else:
            for bag in self.bags:
                yield bag.instrument

    def pretty_print(self, prefix=u''):
        return u"\n".join([prefix + self.__unicode__()] +
                          ["{bag}\n{prefix}\tkeys: {key}\tvels: {vel}\n{instrument}".format(
                              bag=bag.pretty_print(prefix + u'\t'),
                              prefix=prefix,
                              key=bag.key_range or "ALL",
                              vel=bag.velocity_range or "ALL",
                              instrument=bag.instrument.pretty_print(
                                  prefix + u'\t') if bag.instrument else prefix + "\tNo Instrument / Global") for bag in
                           self.bags if self.bags])

    def __unicode__(self):
        if self.name == "EOP" or len(self.name) == 0:
            return "Preset EOP"

        return u"Preset[{0.bank:03}:{0.preset:03}] {0.name} {0.bag_size} bag(s) from #{0.bag_idx}".format(self)

    def __repr__(self):
        return self.__unicode__()
