from typing_extensions import override


class HiddenValue:
    """
    A class to contain a hidden value
    To retrieve the real value use .unmask()
    """

    def unmask(self) -> str:
        # A HiddenValue handed to another one must not stay wrapped. Returning it would hand back
        # the mask — `*MASKED*` is what its __str__ produces — and a StringCommand built from it
        # would run with the literal "*MASKED*" where the real value belongs: no error, no warning,
        # just a wrong credential. Unwrapping here rather than in __init__ keeps a subclass in
        # charge of its own unmask().
        value = self.raw_value
        while isinstance(value, HiddenValue):
            value = value.unmask()
        return value

    def __init__(self, content="", masked_value="*MASKED*"):
        self.masked_value = masked_value
        self.raw_value = content

    @override
    def __str__(self) -> str:
        return str(self.masked_value)

    @override
    def __repr__(self) -> str:
        return repr(self.masked_value)
