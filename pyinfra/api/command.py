class Mask(str):
    hide_me = 'wear a mask'


class StringCommand:
    def __init__(self, bits):
        self.bits = bits
        self.value = ' '.join(bits)
        self.masked = ' '.join(['***' if hasattr(i, 'hide_me') else i for i in bits])
        self.sensitive = set([i for i in bits if hasattr(i, 'hide_me')])

    def __str__(self):
        return self.value
