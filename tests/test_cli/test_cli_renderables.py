"""Unit tests for the CLI descriptor -> Rich renderable registry."""

from dataclasses import dataclass

from rich.padding import Padding
from rich.syntax import Syntax
from rich.text import Text

from pyinfra.api.renderable import CodeBlock, Diff, OutputBlock

from pyinfra_cli import renderables
from pyinfra_cli.renderables import register_renderable, to_renderable


class TestBuiltinRenderers:
    def test_diff_renders_as_syntax(self):
        r = to_renderable(Diff("@@ -1 +1 @@\n- a\n+ b"))
        assert isinstance(r, Syntax)
        assert r.lexer.name.lower() == "diff"

    def test_code_block_uses_its_lexer(self):
        r = to_renderable(CodeBlock("SELECT 1;", "sql"))
        assert isinstance(r, Syntax)
        assert r.lexer.name.lower() == "sql"

    def test_indent_wraps_in_padding(self):
        r = to_renderable(Diff("@@ -1 +1 @@\n- a\n+ b"), indent=4)
        assert isinstance(r, Padding)


class TestRegistry:
    def test_subclass_falls_back_to_base_renderer(self):
        @dataclass(frozen=True)
        class SpecialDiff(Diff):
            pass

        # No renderer registered for SpecialDiff -> resolves to Diff's via MRO.
        r = to_renderable(SpecialDiff("@@ -1 +1 @@\n- a\n+ b"))
        assert isinstance(r, Syntax)
        assert r.lexer.name.lower() == "diff"

    def test_unknown_descriptor_degrades_to_repr(self):
        @dataclass(frozen=True)
        class Unknown(OutputBlock):
            value: int = 1

        r = to_renderable(Unknown())
        assert isinstance(r, Text)
        assert "Unknown" in str(r)

    def test_register_renderable(self):
        @dataclass(frozen=True)
        class Custom(OutputBlock):
            body: str = ""

        marker = Text("custom!")
        register_renderable(Custom, lambda d: marker)
        try:
            assert to_renderable(Custom("x")) is marker
        finally:
            renderables._RENDERERS.pop(Custom, None)
