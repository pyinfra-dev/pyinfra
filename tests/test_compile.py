from unittest import TestCase

from pyinfra_cli.compile import compile_deploy_code


class TestCompile(TestCase):
    def assert_compiles(self, code, wanted_code):
        compiled_code = compile_deploy_code(code).strip()
        self.assertEqual(compiled_code, wanted_code)

    def test_if(self):
        self.assert_compiles(
            'if True: pass',
            'with state.when(True): pass',
        )

    def test_if_else(self):
        self.assert_compiles(
            'if True: pass\nelse: pass',
            (

                'with state.when(True): pass\n'
                'with state.when(not ((True))): pass'
            ),
        )

    def test_if_elif(self):
        self.assert_compiles(
            'if True: pass\nelif False: pass\nelse: pass',
            (
                'with state.when(True): pass\n'
                'with state.when((False) and not ((True))): pass\n'
                'with state.when(not ((True) and (False))): pass'
            ),
        )
