from strategy import Strategy
import random


def gen_host_vid_pool():
    l = random.sample(range(1, 65536), 65535)
    while True:
        for x in l:
            yield x


host_vid_pool = gen_host_vid_pool()


class Vid(object):
    # length of the switch part in the vid (4-bytes)
    # which is used for routing computations
    L = 6

    # The string conversion of the switch (4-bytes) into
    # a binary string format
    binFormat = "{0:0%db}" % (L)

    """vid"""
    def __init__(self, sw, host):
        self.sw = sw
        self.host = host
        self.bin_str = Vid.binFormat.format(sw)

    def match(self, prefix):
        return Strategy.match(self.bin_str, prefix)

    def getLevel(self, vid):
        level = 0
        for i in xrange(Vid.L):
            if vid.bin_str[i] != self.bin_str[i]:
                return Vid.L - level
            level += 1

    def update(self, new_vid):
        self.sw = int(new_vid, 2)
        self.bin_str = Vid.binFormat.format(self.sw)

    @classmethod
    def prefix2mac(cls, prefix):
        # prefix is a string
        zero_len = 32 - Vid.L
        prefix = prefix.split('*')
        mask_len = zero_len + len(prefix[0])
        mask = '1' * mask_len + '0' * (48 - mask_len)
        mac = '0' * zero_len + prefix[0] + '0' * (48 - mask_len)
        # convert to mac address format
        mac = string2mac(mac)
        mask = string2mac(mask)
        return '/'.join([mac, mask])

    @classmethod
    def get_next_host_vid(cls):
        return Vid(0x00, next(host_vid_pool))

    @classmethod
    def vid2mac(cls, sw, host):
        # 4 bytes sw, 2 bytes host
        sw = bin(sw)[2:]
        len_sw = len(sw)
        host = bin(host)[2:]
        len_host = len(host)
        return string2mac('0' * (32 - len_sw) + sw + '0' * (16 - len_host) + host)

    def __eq__(self, vid):
        return self.sw == vid.sw and self.host == vid.host

    def __str__(self):
        return self.bin_str

    def __repr__(self):
        return self.bin_str


def string2mac(s):
    # len(s) should be 48
    mac = []
    while s:
        byte = s[:8]
        byte = hex(int(byte, 2))[2:]
        if len(byte) <= 1:
            byte = '0' + byte
        mac.append(byte)
        s = s[8:]
    return ':'.join(mac)