from unittest import TestCase

from pyinfra.api.util import (
    format_exception,
    get_caller_frameinfo,
    try_int,
    underscore,
)


class TestApiUtil(TestCase):
    def test_try_int_number(self):
        assert try_int('1') == 1

    def test_try_int_fail(self):
        assert try_int('hello') == 'hello'

    def test_get_caller_frameinfo(self):
        def _get_caller_frameinfo():
            return get_caller_frameinfo()

        frameinfo = _get_caller_frameinfo()
        assert frameinfo.lineno == 22  # called by the line above

    def test_underscore(self):
        for camel_string, snake_string in (
            ('ThisIsHowYouDoIt', 'this_is_how_you_do_it'),
            ('This What_nope', 'this _what_nope'),
            ('myNameIs', 'my_name_is'),
        ):
            assert underscore(camel_string) == snake_string

    def test_format_exception(self):
        exception = Exception('I am a message', 1)
        assert format_exception(exception) == "Exception('I am a message', 1)"
