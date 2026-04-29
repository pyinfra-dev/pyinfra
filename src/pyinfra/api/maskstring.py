import sys
from typing import override


class MaskString(str):
    """
    A string subclass that contains the equivalent of "*MASKED*"
    when used as a normal string.
    To retrieve the real value use .unmask()

    Most methods are copied from UserString
    """

    # Note that adding or otherwise modifying a MaskString (or subclass)
    # will create this base class as a base class could take for example a secret ID instead of a plain value to use

    def unmask(self) -> str:
        return self.raw_value  # type: ignore[attr-defined]

    @override
    def __new__(cls, content="", masked_value="*MASKED*"):
        # Create a new string object with the value "*MASKED*"
        s = super().__new__(cls, masked_value)
        # Real value is stored here so that only those aware of the type can get the real value
        s.raw_value = content  # type: ignore[attr-defined]
        return s

    @override
    def __hash__(self):
        # We want hashing to work correctly so we hash the unmasked string
        return hash(self.unmask())

    # Transparently allow operations with other MaskString
    # Use the masked value if it's not a MaskString
    @override
    def __eq__(self, other) -> bool:
        if isinstance(other, MaskString):
            return self.unmask() == other.unmask()
        return super().__eq__(other)

    @override
    def __ne__(self, other) -> bool:
        if isinstance(other, MaskString):
            return self.unmask() != other.unmask()
        return super().__ne__(other)

    @override
    def __lt__(self, other) -> bool:
        if isinstance(other, MaskString):
            return self.unmask() < other.unmask()
        return super().__lt__(other)

    @override
    def __le__(self, other) -> bool:
        if isinstance(other, MaskString):
            return self.unmask() <= other.unmask()
        return super().__le__(other)

    @override
    def __gt__(self, other) -> bool:
        if isinstance(other, MaskString):
            return self.unmask() > other.unmask()
        return super().__gt__(other)

    @override
    def __ge__(self, other) -> bool:
        if isinstance(other, MaskString):
            return self.unmask() >= other.unmask()
        return super().__ge__(other)

    @override
    def __contains__(self, other) -> bool:
        if isinstance(other, MaskString):
            other = other.unmask()
            return other in self.unmask()
        return super().__contains__(other)

    # Explicitly don't support len and index access to the real string
    # @override
    # def __len__(self) -> int:
    #     return len(self.unmask())
    # @override
    # def __getitem__(self, index) -> str:
    #     return MaskString(self.unmask()[index])

    # MaskString is viral if you do an operation with it it becomes a mask string.
    # This will probably break things like pathlib.Path
    @override
    def __add__(self, other) -> "MaskString":
        other_s = other
        if isinstance(other, MaskString):
            other_s = other.unmask()
            other = ""
        return MaskString(self.unmask() + other_s, masked_value=super().__add__(other))

    def __radd__(self, other) -> "MaskString":
        other_s = other
        if isinstance(other, MaskString):
            other_s = other.unmask()
            other = ""
        return MaskString(other_s + self.unmask(), masked_value=other + str(self))

    # strings don't multiply together. Let default exception propagate
    @override
    def __mul__(self, n) -> "MaskString":
        return MaskString(self.unmask() * n, masked_value=super().__mul__(n))

    __rmul__ = __mul__

    # % formatting will fail if there are unused format directives so don't allow formatting a MaskString
    # @override
    # def __mod__(self, args):
    #     return MaskString(self.unmask() % args)

    # % formatting will fail if there are unused format directives so don't allow formatting a MaskString
    # @override
    # def __rmod__(self, template):
    #     return MaskString(str(template) % self)

    @override
    # the following methods are defined in alphabetical order:
    def capitalize(self) -> "MaskString":
        return MaskString(self.unmask().capitalize(), masked_value=super().capitalize())

    @override
    def casefold(self) -> "MaskString":
        return MaskString(self.unmask().casefold(), masked_value=super().casefold())

    @override
    def center(self, width, *args) -> "MaskString":
        return MaskString(
            self.unmask().center(width, *args), masked_value=super().center(width, *args)
        )

    @override
    def count(self, sub, start=0, end=sys.maxsize) -> int:
        if isinstance(sub, MaskString):
            sub = sub.unmask()
            return self.unmask().count(sub, start, end)
        return super().count(sub, start, end)

    @override
    def removeprefix(self, prefix, /) -> "MaskString":
        prefix_s = prefix
        if isinstance(prefix, MaskString):
            prefix_s = prefix.unmask()
        return MaskString(
            self.unmask().removeprefix(prefix_s), masked_value=super().removeprefix(prefix)
        )

    @override
    def removesuffix(self, suffix, /) -> "MaskString":
        suffix_s = suffix
        if isinstance(suffix, MaskString):
            suffix_s = suffix.unmask()
        return MaskString(
            self.unmask().removesuffix(suffix_s), masked_value=super().removesuffix(suffix)
        )

    # @override
    # def encode(self, encoding="utf-8", errors="strict") -> bytes:
    #     encoding = "utf-8" if encoding is None else encoding
    #     errors = "strict" if errors is None else errors
    #     return super().encode(encoding, errors)

    @override
    def endswith(self, suffix, start=0, end=sys.maxsize) -> bool:
        if isinstance(suffix, MaskString):
            return self.unmask().endswith(suffix.unmask(), start, end)
        return super().endswith(suffix, start, end)

    @override
    def expandtabs(self, tabsize=8):
        return MaskString(
            self.unmask().expandtabs(tabsize), masked_value=super().expandtabs(tabsize)
        )

    @override
    def find(self, sub, start=0, end=sys.maxsize) -> int:
        if isinstance(sub, MaskString):
            return self.unmask().find(sub.unmask(), start, end)
        return super().find(sub, start, end)

    # format will fail if there are unused format directives so don't allow formatting a MaskString
    # @override
    # def format(self, /, *args, **kwds) -> str:
    #     unmask = kwds.pop("unmask", False)
    #     return str(self)

    # format will fail if there are unused format directives so don't allow formatting a MaskString
    # @override
    # def format_map(self, mapping) -> str:
    #     return str(self)

    @override
    def index(self, sub, start=0, end=sys.maxsize) -> int:
        if isinstance(sub, MaskString):
            return self.unmask().index(sub.unmask(), start, end)
        return super().index(sub, start, end)

    # Not sure if this should return the unmasked result or the masked result
    # @override
    # def isalpha(self) -> bool:
    #     return self.unmask().isalpha()

    # @override
    # def isalnum(self) -> bool:
    #     return self.unmask().isalnum()

    # @override
    # def isascii(self) -> bool:
    #     return self.unmask().isascii()

    # @override
    # def isdecimal(self) -> bool:
    #     return self.unmask().isdecimal()

    # @override
    # def isdigit(self) -> bool:
    #     return self.unmask().isdigit()

    # @override
    # def isidentifier(self) -> bool:
    #     return self.unmask().isidentifier()

    # @override
    # def islower(self) -> bool:
    #     return self.unmask().islower()

    # @override
    # def isnumeric(self) -> bool:
    #     return self.unmask().isnumeric()

    # @override
    # def isprintable(self) -> bool:
    #     return self.unmask().isprintable()

    # @override
    # def isspace(self) -> bool:
    #     return self.unmask().isspace()

    # @override
    # def istitle(self) -> bool:
    #     return self.unmask().istitle()

    # @override
    # def isupper(self) -> bool:
    #     return self.unmask().isupper()

    @override
    def join(self, seq) -> "MaskString":
        seq = list(seq)
        seq_s = [x.unmask() if isinstance(x, MaskString) else x for x in seq]
        # We just make the masked_value the default. Otherwise we end up with '*MASKED*' repeated a bunch which doesn't really help anything
        return MaskString(self.unmask().join(seq_s))

    @override
    def ljust(self, width, *args) -> "MaskString":
        return MaskString(
            self.unmask().ljust(width, *args), masked_value=super().ljust(width, *args)
        )

    @override
    def lower(self) -> "MaskString":
        return MaskString(self.unmask().lower(), masked_value=super().lower())

    @override
    def lstrip(self, chars=None) -> "MaskString":
        chars_s = chars
        if isinstance(chars, MaskString):
            # we want the resulting masked string to stay the same as otherwise it would most likely just strip all the characters
            chars_s = chars.unmask()
            return MaskString(self.unmask().lstrip(chars_s), masked_value=str(self))
        return MaskString(self.unmask().lstrip(chars), masked_value=super().lstrip(chars))

    # I don't know how maketrans works... default to using the masked value
    # maketrans = str.maketrans

    @override
    def partition(self, sep) -> tuple["MaskString", "MaskString", "MaskString"]:
        sep_s = sep
        if isinstance(sep, MaskString):
            sep_s = sep.unmask()

        s = self.unmask().partition(sep_s)
        u = super().partition(sep)
        return (
            MaskString(s[0], masked_value=u[0]),
            MaskString(s[1], masked_value=u[1]),
            MaskString(s[2], masked_value=u[2]),
        )

    @override
    def replace(self, old, new, maxsplit=-1) -> "MaskString":
        old_s = old
        new_s = new
        if isinstance(old, MaskString):
            old_s = old.unmask()
        if isinstance(new, MaskString):
            new_s = new.unmask()
        return MaskString(
            self.unmask().replace(old_s, new_s, maxsplit), masked_value=super().replace(old, new)
        )

    @override
    def rfind(self, sub, start=0, end=sys.maxsize) -> int:
        if isinstance(sub, MaskString):
            return self.unmask().rfind(sub.unmask(), start, end)
        return super().rfind(sub, start, end)

    @override
    def rindex(self, sub, start=0, end=sys.maxsize) -> int:
        if isinstance(sub, MaskString):
            return self.unmask().rindex(sub.unmask(), start, end)
        return super().rindex(sub, start, end)

    @override
    def rjust(self, width, *args) -> "MaskString":
        return MaskString(
            self.unmask().rjust(width, *args), masked_value=super().rjust(width, *args)
        )

    @override
    def rpartition(self, sep) -> tuple["MaskString", "MaskString", "MaskString"]:
        sep_s = sep
        if isinstance(sep, MaskString):
            sep_s = sep.unmask()

        s = self.unmask().rpartition(sep_s)
        u = super().rpartition(sep)
        return (
            MaskString(s[0], masked_value=u[0]),
            MaskString(s[1], masked_value=u[1]),
            MaskString(s[2], masked_value=u[2]),
        )

    @override
    def rstrip(self, chars=None) -> "MaskString":
        chars_s = chars
        if isinstance(chars, MaskString):
            # we want the resulting masked string to stay the same as otherwise it would most likely just strip all the characters
            chars_s = chars.unmask()
            return MaskString(self.unmask().rstrip(chars_s), masked_value=str(self))
        return MaskString(self.unmask().rstrip(chars_s), masked_value=super().rstrip(chars))

    # There is no way to keep the split functions "in-sync" with the masked string and the raw_value
    # @override
    # def split(self, sep=None, maxsplit=-1) -> list[MaskString]:
    #     if isinstance(sep, MaskString):
    #         sep = sep.unmask()
    #         return [MaskString(x) for x in self.unmask().split(sep, maxsplit)]
    #     return super().split(sep, maxsplit)

    # @override
    # def rsplit(self, sep=None, maxsplit=-1) -> list[MaskString]:
    #     if isinstance(sep, MaskString):
    #         sep = sep.unmask()
    #         return [MaskString(x) for x in self.unmask().rsplit(sep, maxsplit)]
    #     return super().rsplit(sep, maxsplit)

    # @override
    # def splitlines(self, keepends=False) -> list[MaskString]:
    #     return [MaskString(x) for x in self.unmask().splitlines(keepends)]

    @override
    def startswith(self, prefix, start=0, end=sys.maxsize) -> bool:
        if isinstance(prefix, MaskString):
            prefix = prefix.unmask()
            return self.unmask().startswith(prefix, start, end)
        return super().startswith(prefix, start, end)

    @override
    def strip(self, chars=None) -> "MaskString":
        chars_s = chars
        if isinstance(chars, MaskString):
            # we want the resulting masked string to stay the same as otherwise it would most likely just strip all the characters
            chars_s = chars.unmask()
            return MaskString(self.unmask().strip(chars_s), masked_value=str(self))
        return MaskString(self.unmask().strip(chars_s), masked_value=super().strip(chars))

    @override
    def swapcase(self) -> "MaskString":
        return MaskString(self.unmask().swapcase(), masked_value=super().swapcase())

    @override
    def title(self) -> "MaskString":
        return MaskString(self.unmask().title(), masked_value=super().title())

    # I don't know how translate works... default to using the masked value
    # @override
    # def translate(self, *args) -> 'MaskString':
    #     return MaskString(self.unmask().translate(*args))

    @override
    def upper(self) -> "MaskString":
        return MaskString(self.unmask().upper(), masked_value=super().upper())

    @override
    def zfill(self, width) -> "MaskString":
        return MaskString(self.unmask().zfill(width), masked_value=super().zfill(width))
