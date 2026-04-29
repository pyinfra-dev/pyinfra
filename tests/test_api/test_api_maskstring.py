from unittest import TestCase
from pyinfra.api import MaskString
import copy


class OtherMaskString(MaskString):
    """Subclass of MaskString to validate basic usage"""

    def __new__(cls, service: str = "", username: str = "") -> "OtherMaskString":
        mask_string = super().__new__(cls, "fake_value", masked_value="FAKE NEWS")
        mask_string.__service = service
        mask_string.__username = username
        return mask_string

    def unmask(self) -> str:
        return self.__service + self.__username


class TestMaskString(TestCase):
    def test_capitalize(self):
        s = MaskString("secret value")
        new_s = s.capitalize()
        assert new_s.unmask() == "Secret value"
        assert new_s == "*masked*"

    def test_casefold(self):
        s = MaskString("SECRET")
        new_s = s.casefold()
        assert new_s.unmask() == "secret"
        assert new_s == "*masked*"

    def test_center(self):
        s = MaskString("hi")
        new_s = s.center(10)
        assert new_s.unmask() == "    hi    "

        new_s = s.center(10, "-")
        assert new_s.unmask() == "----hi----"

    def test_contains(self):
        s = MaskString("Secret Value")
        inner = MaskString("Secret")
        assert inner in s
        assert "Secret" not in s
        assert "MASKED" in s
        assert "*" in s

    def test_count(self):
        s = MaskString("hello world")
        sub = "l"
        assert s.count(sub) == 0  # counts in masked value '*MASKED*'
        sub = MaskString("l")
        assert s.count(sub) == 3  # counts in unmasked value
        assert s.count(sub, 0, 3) == 1
        assert s.count(sub, 3) == 2

    def test_endswith(self):
        s = MaskString("secret value")
        end = MaskString("value")
        assert s.endswith("*") is True
        assert s.endswith(end) is True
        assert s.endswith("SKED*")
        assert not s.endswith("value")

    def test_expandtabs(self):
        s = MaskString("a\tb")
        new_s = s.expandtabs(4)
        assert new_s.unmask() == "a   b"

        new_s = s.expandtabs()
        assert new_s.unmask() == "a       b"

    def test_find(self):
        s = MaskString("hello world")
        assert s.find("hello") == -1  # searches masked value

        sub = MaskString("missing")  # searches unmasked value
        assert s.find(sub) == -1

        sub = MaskString("l")
        assert s.find(sub) == 2

        assert s.find(sub, 4) == 9
        assert s.find(sub, 10) == -1

    def test_eq(self):
        s1 = MaskString("Secret Value")
        s2 = MaskString("Secret Value")
        s3 = MaskString("Other Value")

        assert s1 == s2
        assert s1 != s3

        assert s1 == "*MASKED*"
        assert s2 == "*MASKED*"
        assert s3 == "*MASKED*"

    def test_ne(self):
        s1 = MaskString("secret")
        s2 = MaskString("other")
        s3 = MaskString("secret")
        assert s1 != s2
        assert not (s1 != s3)
        # plain str compares against masked value
        assert s1 != "secret"
        assert s1 == "*MASKED*"

    def test_add_str(self):
        s = MaskString("Secret Value")
        new_s = s + " test"
        assert new_s == "*MASKED* test"
        assert new_s.unmask() == "Secret Value test"

        new_s = s + MaskString(" test")
        assert new_s == "*MASKED*"
        assert new_s.unmask() == "Secret Value test"

    def test_radd(self):
        s = MaskString("Secret Value")
        new_s = "test " + s
        assert new_s == "test *MASKED*"
        assert new_s.unmask() == "test Secret Value"

        s2 = MaskString("test ")
        new_s = s.__radd__(s2)
        assert new_s == "*MASKED*"
        assert new_s.unmask() == "test Secret Value"

    def test_ge(self):
        s1 = MaskString("b")
        s2 = MaskString("a")
        s3 = MaskString("b")
        assert s1 >= s2
        assert s1 >= s3
        assert s1 >= "!"  # '*' > '!'
        assert s1 >= "*"  # len(s1) > len('*')
        assert s1 == "*MASKED*"
        assert s2 == "*MASKED*"
        assert s3 == "*MASKED*"

    def test_gt(self):
        s1 = MaskString("b")
        s2 = MaskString("a")
        assert s1 > s2
        assert s1 > "!"  # '*' > '!'
        assert s1 > "*"  # len(s1) > len('*')
        assert s1 == "*MASKED*"
        assert s2 == "*MASKED*"

    def test_le(self):
        s1 = MaskString("a")
        s2 = MaskString("b")
        s3 = MaskString("a")
        assert s1 <= s2
        assert s1 <= s3
        assert s1 <= "0"  # '*' <= '0'
        assert not s1 <= "*"  # len(s1) > len('*')
        assert s1 == "*MASKED*"
        assert s2 == "*MASKED*"
        assert s3 == "*MASKED*"

    def test_lt(self):
        s = MaskString("a")
        s1 = MaskString("b")
        assert s < s1
        assert s1 < "0"  # '*' <= '0'
        assert not s1 < "*"  # len(s1) > len('*')
        assert s == "*MASKED*"
        assert s1 == "*MASKED*"

    def test_mul(self):
        s = MaskString("ab")
        new_s = s * 3
        assert new_s == "*MASKED**MASKED**MASKED*"
        assert new_s.unmask() == "ababab"

    def test_rmul(self):
        s = MaskString("ab")
        new_s = 3 * s
        assert new_s == "*MASKED**MASKED**MASKED*"
        assert new_s.unmask() == "ababab"

    def test_hash(self):
        s1 = MaskString("secret")
        s2 = MaskString("secret")
        assert hash(s1) == hash(s2)
        assert hash(s1) == hash("secret")

    def test_hash_dict_key(self):
        s = MaskString("key")
        d = {s: "value"}
        assert d[MaskString("key")] == "value"
        assert (
            d.get("key", None) != "value"
        )  # plain str won't match since dict takes the type into account

    def test_index_found(self):
        s = MaskString("secret value")
        sub = MaskString("value")
        assert s.index(sub) == 7

        sub = MaskString("missing")
        with self.assertRaises(ValueError):
            s.index(sub)

        # plain str searches the masked value '*MASKED*'
        assert s.index("*") == 0

    def test_join(self):
        s = MaskString("-")
        parts = [MaskString("a"), MaskString("b"), MaskString("c")]
        new_s = s.join(parts)
        assert new_s.unmask() == "a-b-c"
        assert (
            new_s == "*MASKED*"
        )  # The other option is to make it return '*MASKED**MASKED**MASKED**MASKED**MASKED*' which seems unnecessary

        parts = ["a", MaskString("b"), "c"]
        new_s = s.join(parts)
        assert new_s.unmask() == "a-b-c"
        assert new_s == "*MASKED*"

        parts = ["a", "b", "c"]
        new_s = s.join(parts)
        assert new_s.unmask() == "a-b-c"
        assert new_s == "*MASKED*"

    def test_ljust(self):
        s = MaskString("hi")
        new_s = s.ljust(10)
        assert new_s.unmask() == "hi        "
        assert new_s == "*MASKED*  "

        new_s = s.ljust(10, "-")
        assert new_s.unmask() == "hi--------"
        assert new_s == "*MASKED*--"

    def test_lower(self):
        s = MaskString("SECRET")
        new_s = s.lower()
        assert new_s.unmask() == "secret"
        assert new_s == "*masked*"

    def test_lstrip(self):
        s = MaskString("  secret  ")
        new_s = s.lstrip()
        assert new_s.unmask() == "secret  "

        s = MaskString("**secret**")
        new_s = s.lstrip("*")
        assert new_s.unmask() == "secret**"
        assert new_s == "MASKED*"

        s = MaskString("**secret**")
        new_s = s.lstrip(MaskString("*"))
        assert new_s.unmask() == "secret**"
        assert new_s == "*MASKED*"

        s = MaskString("  secret  ")
        new_s = s.lstrip(MaskString(" "))
        assert new_s.unmask() == "secret  "
        assert new_s == "*MASKED*"

    def test_partition(self):
        s = MaskString("secret:value")
        before, sep, after = s.partition(":")
        assert before.unmask() == "secret"
        assert sep.unmask() == ":"
        assert after.unmask() == "value"

        assert before == "*MASKED*"
        assert sep == ""  # maybe set these to '*MASKED*' since this output isn't helpful
        assert after == ""

        before, sep, after = s.partition(MaskString(":"))
        assert before.unmask() == "secret"
        assert sep.unmask() == ":"
        assert after.unmask() == "value"

        assert before == ""
        assert sep == "*MASKED*"
        assert after == ""

        before, sep, after = s.partition("|")
        assert before.unmask() == "secret:value"
        assert sep.unmask() == ""
        assert after.unmask() == ""

        assert before == "*MASKED*"
        assert sep == ""  # maybe set these to '*MASKED*' since this output isn't helpful
        assert after == ""

        before, sep, after = s.partition(MaskString("|"))
        assert before.unmask() == "secret:value"
        assert sep.unmask() == ""
        assert after.unmask() == ""

        assert before == ""
        assert sep == "*MASKED*"
        assert after == ""

    def test_pickle(self):
        import pickle

        s = MaskString("secret")
        pickled = pickle.dumps(s)
        restored = pickle.loads(pickled)
        assert isinstance(restored, MaskString)
        assert restored.unmask() == "secret"
        assert restored == "*MASKED*"

    def test_removeprefix(self):
        s = MaskString("secret value")
        new_s = s.removeprefix("secret ")
        assert new_s.unmask() == "value"

        prefix = MaskString("secret ")
        new_s = s.removeprefix(prefix)
        assert new_s.unmask() == "value"

        new_s = s.removeprefix("other")
        assert new_s.unmask() == "secret value"
        assert new_s == "*MASKED*"

    def test_removesuffix(self):
        s = MaskString("secret value")
        new_s = s.removesuffix(" value")
        assert new_s.unmask() == "secret"

        suffix = MaskString(" value")
        new_s = s.removesuffix(suffix)
        assert new_s.unmask() == "secret"

        new_s = s.removesuffix("other")
        assert new_s.unmask() == "secret value"
        assert new_s == "*MASKED*"

    def test_replace(self):
        s = MaskString("secret value")
        new_s = s.replace("value", "data")
        assert new_s.unmask() == "secret data"
        assert new_s == "*MASKED*"

        old = MaskString("value")
        new = MaskString("data")
        new_s = s.replace(old, new)
        assert new_s.unmask() == "secret data"

    def test_replace_maxsplit(self):
        s = MaskString("aaa")
        new_s = s.replace("a", "b", 2)
        assert new_s.unmask() == "bba"

    def test_result_is_maskstring(self):
        # Verify all transform methods return MaskString instances
        s = MaskString("secret")
        assert isinstance(s.upper(), MaskString)
        assert isinstance(s.lower(), MaskString)
        assert isinstance(s.capitalize(), MaskString)
        assert isinstance(s.swapcase(), MaskString)
        assert isinstance(s.title(), MaskString)
        assert isinstance(s.strip(), MaskString)
        assert isinstance(s.lstrip(), MaskString)
        assert isinstance(s.rstrip(), MaskString)
        assert isinstance(s + "", MaskString)
        assert isinstance("" + s, MaskString)
        assert isinstance(s * 2, MaskString)
        assert isinstance(s.center(10), MaskString)
        assert isinstance(s.ljust(10), MaskString)
        assert isinstance(s.rjust(10), MaskString)
        assert isinstance(s.zfill(10), MaskString)
        assert isinstance(s.replace("x", "y"), MaskString)
        assert isinstance(s.removeprefix("x"), MaskString)
        assert isinstance(s.removesuffix("x"), MaskString)
        assert isinstance(s.expandtabs(), MaskString)
        assert isinstance(s.casefold(), MaskString)

    def test_rfind(self):
        s = MaskString("abcabc")
        sub = MaskString("a")
        assert s.rfind(sub) == 3
        assert s.rfind("*") == 7  # last '*' in '*MASKED*'

    def test_rindex_found(self):
        s = MaskString("abcabc")
        sub = MaskString("a")
        assert s.rindex(sub) == 3

        sub = MaskString("missing")
        with self.assertRaises(ValueError):
            s.rindex(sub)
        # plain str searches the masked value '*MASKED*'
        assert s.rindex("*") == 7

    def test_rjust(self):
        s = MaskString("hi")
        new_s = s.rjust(10)
        assert new_s.unmask() == "        hi"

        new_s = s.rjust(10, "-")
        assert new_s.unmask() == "--------hi"

    def test_rpartition(self):
        s = MaskString("secret:value")
        before, sep, after = s.rpartition(":")
        assert before.unmask() == "secret"
        assert sep.unmask() == ":"
        assert after.unmask() == "value"

        assert before == ""  # maybe set these to '*MASKED*' since this output isn't helpful
        assert sep == ""
        assert after == "*MASKED*"

        before, sep, after = s.rpartition(MaskString(":"))
        assert before.unmask() == "secret"
        assert sep.unmask() == ":"
        assert after.unmask() == "value"

        assert before == ""
        assert sep == "*MASKED*"
        assert after == ""

        before, sep, after = s.rpartition("|")
        assert before.unmask() == ""
        assert sep.unmask() == ""
        assert after.unmask() == "secret:value"

        assert before == ""
        assert sep == ""
        assert after == "*MASKED*"

        before, sep, after = s.rpartition(MaskString("|"))
        assert before.unmask() == ""
        assert sep.unmask() == ""
        assert after.unmask() == "secret:value"

        assert before == ""
        assert sep == "*MASKED*"
        assert after == ""

    def test_rstrip(self):
        s = MaskString("  secret  ")
        new_s = s.rstrip()
        assert new_s.unmask() == "  secret"

        s = MaskString("**secret**")
        new_s = s.rstrip("*")
        assert new_s.unmask() == "**secret"
        assert new_s == "*MASKED"

        s = MaskString("**secret**")
        new_s = s.rstrip(MaskString("*"))
        assert new_s.unmask() == "**secret"
        assert new_s == "*MASKED*"

        s = MaskString("  secret  ")
        new_s = s.rstrip(MaskString(" "))
        assert new_s.unmask() == "  secret"
        assert new_s == "*MASKED*"

    def test_startswith(self):
        s = MaskString("secret value")
        assert s.startswith("*")
        assert not s.startswith("secret")
        prefix = MaskString("secret")
        assert s.startswith(prefix)

        prefix = MaskString("value")
        assert s.startswith(prefix, 7)

    def test_str_repr_masked(self):
        s = MaskString("top secret")
        assert str(s) == "*MASKED*"
        assert repr(s) == "'*MASKED*'"

    def test_strip(self):
        s = MaskString("  secret  ")
        new_s = s.strip()
        assert new_s.unmask() == "secret"

        s = MaskString("**secret**")
        new_s = s.strip("*")
        assert new_s.unmask() == "secret"
        assert new_s == "MASKED"

        s = MaskString("**secret**")
        new_s = s.strip(MaskString("*"))
        assert new_s.unmask() == "secret"
        assert new_s == "*MASKED*"

        s = MaskString("  secret  ")
        new_s = s.strip(MaskString(" "))
        assert new_s.unmask() == "secret"
        assert new_s == "*MASKED*"

    def test_swapcase(self):
        s = MaskString("Secret")
        new_s = s.swapcase()
        assert new_s.unmask() == "sECRET"
        assert new_s == "*masked*"

    def test_title(self):
        s = MaskString("secret value")
        new_s = s.title()
        assert new_s.unmask() == "Secret Value"
        assert new_s == "*Masked*"

    def test_upper(self):
        s = MaskString("secret")
        new_s = s.upper()
        assert new_s.unmask() == "SECRET"
        assert new_s == "*MASKED*"

    def test_viral_add_chain(self):
        s = MaskString("secret")
        result = s + " part1" + " part2"
        assert result.unmask() == "secret part1 part2"
        assert result == "*MASKED* part1 part2"

        result = "part1 " + s + " part2"
        assert result.unmask() == "part1 secret part2"
        assert result == "part1 *MASKED* part2"

    def test_zfill(self):
        s = MaskString("12345")
        new_s = s.zfill(6)
        assert new_s.unmask() == "012345"

        new_s = s.zfill(3)
        assert new_s.unmask() == "12345"
        assert new_s == "*MASKED*"

    def test_deepcopy(self):
        s = MaskString("12345")
        new_s = copy.deepcopy(s)
        assert new_s.unmask() == "12345"
        assert new_s == "*MASKED*"

    def test_deepcopy(self):
        s = OtherMaskString(service="ssh", username="pyinfra")
        new_s = copy.deepcopy(s)
        assert isinstance(new_s, OtherMaskString)
        assert new_s.unmask() == "sshpyinfra"
        assert new_s == "FAKE NEWS"
