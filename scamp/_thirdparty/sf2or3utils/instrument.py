from .bag import Sf2Bag
from .riffparser import from_cstr


class Sf2Instrument(object):
    SENTINEL_NAME = "EOI"

    def __init__(self, hydra_header, idx, sf2parser):
        instrument_header = hydra_header['Inst'][idx]

        self.name = from_cstr(instrument_header.name)

        # don't process the sentinel item
        if self.name == self.SENTINEL_NAME:
            return

        self.hydra_header = hydra_header

        self.bag_idx = instrument_header.bag
        self.bag_size = hydra_header['Inst'][idx + 1].bag - self.bag_idx

        self.bags = self.build_bags()

        self.parent = sf2parser

    def build_bags(self):
        return [Sf2Bag(self.hydra_header, idx, self, 'Ibag', 'Imod', 'Igen') for idx in
                range(self.bag_idx, self.bag_idx + self.bag_size)]

    def pretty_print(self, prefix=u''):
        return u"\n".join([prefix + self.__unicode__()] +
                          [bag.pretty_print(prefix + u'\t') for bag in self.bags if self.bags])

    def is_sentinel(self):
        return self.name == self.SENTINEL_NAME

    def __unicode__(self):
        if self.is_sentinel():
            return u"Instrument EOI"

        return u"Instrument {0.name} {0.bag_size} bag(s) from {0.bag_idx}".format(self)

    def __repr__(self):
        return self.__unicode__()
