from random import randint


class Strategy(object):
    L = 6
    """vid update strategy methods"""
    def __init__(self):
        pass

    @classmethod
    def genUpdatePrefixes(cls):
        prefixes = []
        # traverse all possible prefixes, hit each with possibility 1/2
        for pre_len in xrange(1, cls.L):
            for i in xrange(2**pre_len):
                pre = bin(i)[2:]
                if len(pre) < pre_len:
                    pre = '0' * (pre_len - len(pre)) + pre
                prefix = pre + '*' * (cls.L - pre_len)
                if randint(0, 1) == 1:
                    prefixes.append(prefix)
        # deal with pre_len == 0
        if randint(0, 1) == 1:
            prefixes.insert(0, '*' * cls.L)
        return prefixes

    @classmethod
    def spin(cls, prefix, old_vid):
        pre = prefix.split('*')[0]
        bit_location = len(pre)
        bit = '*'
        if old_vid[bit_location] == '1':
            bit = '0'
        elif old_vid[bit_location] == '0':
            bit = '1'

        new_vid = old_vid[:bit_location] + bit + old_vid[bit_location + 1:]
        return new_vid

    @classmethod
    def match(cls, vid, prefix):
        for i in xrange(cls.L):
            if prefix[i] == '*':
                return True
            if prefix[i] != vid[i]:
                return False

    @classmethod
    def genHostMac(cls, new_vid):
        pass