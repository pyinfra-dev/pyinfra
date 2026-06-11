from typing_extensions import override


class HiddenValue:
    """
    A class to contain a hidden value
    To retrieve the real value use .unmask()
    """

    def unmask(self) -> str:
        return self.raw_value

    def __init__(self, content="", masked_value="*MASKED*"):
        self.masked_value = masked_value
        self.raw_value = content

    @override
    def __str__(self) -> str:
        return str(self.masked_value)

    @override
    def __repr__(self) -> str:
        return repr(self.masked_value)
