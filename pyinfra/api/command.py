
class Mask(str):
    hide_me = "wear a mask"

class StringCommand:

    def __init__(self, value, masked=None):
        self.value = value
        self.masked = masked if masked else value

    def __str__(self):
        return self.value

    @classmethod
    def join(cls, lst):
        value = " ".join(lst)
        masked = " ".join(["***" if hasattr(i, "hide_me") else i for i in lst])
        return cls(value, masked)

