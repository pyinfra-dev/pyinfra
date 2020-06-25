from six.moves import shlex_quote


class MaskString(str):
    pass


class QuoteString(object):
    def __init__(self, obj):
        self.object = obj


class StringCommand(object):
    def __init__(self, *bits):
        self.bits = bits

    def __str__(self):
        return self.get_masked_value()

    def __repr__(self):
        return 'StringCommand({0})'.format(self.get_masked_value())

    def _get_all_bits(self, bit_accessor):
        all_bits = []

        for bit in self.bits:
            quote = False
            if isinstance(bit, QuoteString):
                quote = True
                bit = bit.object

            if isinstance(bit, StringCommand):
                bit = bit_accessor(bit)

            if quote:
                bit = shlex_quote(bit)

            all_bits.append(bit)

        return all_bits

    def get_raw_value(self):
        return ' '.join(self._get_all_bits(lambda bit: bit.get_raw_value()))

    def get_masked_value(self):
        return ' '.join([
            '***' if isinstance(bit, MaskString) else bit
            for bit in self._get_all_bits(lambda bit: bit.get_masked_value())
        ])
