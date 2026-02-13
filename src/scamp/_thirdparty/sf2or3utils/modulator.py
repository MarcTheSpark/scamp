class Sf2Mod(object):
    def __init__(self, mod_header):
        self.src_oper = mod_header.src_oper
        self.dest_oper = mod_header.dest_oper
        self.amount = mod_header.amount
        self.amount_src_oper = mod_header.amount_src_oper
        self.trans_oper = mod_header.trans_oper

    def build_link(self, parent_mods):
        """link mod if destination is another modulator"""
        # TODO indexing of destination mod is unclear and must be tested with an example
        if self.dest_oper & 0x8000:
            self.dest = parent_mods[self.dest_oper & 0x7FFF]

    def pretty_print(self, prefix=u''):
        return prefix + self.__unicode__()

    def __unicode__(self):
        return u"Modulation src oper {0.src_oper} dest oper {0.dest_oper} amount {0.amount} " \
               u"amount_src_oper {0.amount_src_oper} trans_oper {0.trans_oper}".format(self)

    def __repr__(self):
        return self.__unicode__()
