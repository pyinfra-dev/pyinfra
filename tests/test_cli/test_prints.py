"""
Tests for pyinfra_cli.prints module, particularly CJK character handling in tables.
"""

from unittest import TestCase
from unittest.mock import Mock

import wcwidth

from pyinfra_cli.prints import print_rows


class TestPrintRows(TestCase):
    """Test the print_rows function with various character types."""

    def _calculate_display_width(self, text):
        """Calculate the actual display width of text (for verification in tests)."""
        # Strip ANSI codes
        import re

        ansi_re = re.compile(r"\033\[((?:\d|;)*)([a-zA-Z])")
        text_clean = ansi_re.sub("", text)

        width = wcwidth.wcswidth(text_clean)
        return width if width >= 0 else len(text_clean)

    def test_print_rows_ascii_alignment(self):
        """Test that ASCII-only tables are properly aligned."""
        output = []
        mock_func = Mock(side_effect=lambda line: output.append(line))

        rows = [
            (mock_func, ["Op", "Status", "Count"]),
            (mock_func, ["install", "success", "5"]),
            (mock_func, ["restart", "pending", "1"]),
        ]

        print_rows(rows)

        # All rows should be printed
        assert len(output) == 3

        # For ASCII, string index position should match visual alignment
        # because each char = 1 display column
        status_pos = output[0].index("Status")

        # Check alignment in data rows
        assert output[1][status_pos : status_pos + 7].strip() == "success"
        assert output[2][status_pos : status_pos + 7].strip() == "pending"

    def test_print_rows_cjk_display_width(self):
        """
        Test that CJK characters are measured by display width, not character count.

        This is the core issue: Chinese chars take 2 display columns each.
        With wrong calculation, visual alignment breaks even though string indices match.
        """
        output = []
        mock_func = Mock(side_effect=lambda line: output.append(line))

        # Each Chinese char = 1 character but 2 display columns
        rows = [
            (mock_func, ["ABC", "Status"]),  # 3 chars, 3 display cols
            (mock_func, ["中文", "OK"]),  # 2 chars, 4 display cols
        ]

        print_rows(rows)

        # Calculate the display width of each row
        row0_display_width = self._calculate_display_width(output[0])
        row1_display_width = self._calculate_display_width(output[1])

        # The rows should have the same DISPLAY width for proper alignment
        # (they may have different string lengths, but display width must match)
        assert row0_display_width == row1_display_width, (
            f"Display width mismatch: row0={row0_display_width}, row1={row1_display_width}. "
            f"CJK characters not properly handled. Row0: {repr(output[0])}, Row1: {repr(output[1])}"
        )

    def test_print_rows_cjk_alignment(self):
        """Test that CJK tables maintain column alignment across rows."""
        output = []
        mock_func = Mock(side_effect=lambda line: output.append(line))

        rows = [
            (mock_func, ["操作", "状态", "计数"]),  # Operation, Status, Count
            (mock_func, ["安装", "成功", "5"]),  # Install, Success, 5
            (mock_func, ["重启", "待定", "1"]),  # Restart, Pending, 1
        ]

        print_rows(rows)

        # All rows should have the same display width
        display_widths = [self._calculate_display_width(row) for row in output]
        assert display_widths[0] == display_widths[1] == display_widths[2], (
            f"Rows have different display widths: {display_widths}"
        )

    def test_print_rows_mixed_ascii_cjk(self):
        """Test alignment with mixed ASCII and CJK characters in same table."""
        output = []
        mock_func = Mock(side_effect=lambda line: output.append(line))

        rows = [
            (mock_func, ["Name", "状态", "Count"]),  # Mixed columns
            (mock_func, ["test", "成功", "5"]),  # ASCII, CJK, ASCII
            (mock_func, ["prod", "失败", "0"]),  # ASCII, CJK, ASCII
        ]

        print_rows(rows)

        # All rows should have the same display width
        display_widths = [self._calculate_display_width(row) for row in output]
        assert len(set(display_widths)) == 1, (
            f"Mixed ASCII/CJK rows have inconsistent display widths: {display_widths}"
        )

    def test_print_rows_with_ansi_codes(self):
        """Test that ANSI codes are properly stripped before width calculation."""
        output = []
        mock_func = Mock(side_effect=lambda line: output.append(line))

        red = "\033[31m"
        green = "\033[32m"
        reset = "\033[0m"

        rows = [
            (mock_func, ["Operation", "Status"]),
            (mock_func, [f"{green}success{reset}", f"{red}fail{reset}"]),
        ]

        print_rows(rows)

        # ANSI codes should be in output
        assert green in output[1]

        # But should not affect display width calculation
        display_widths = [self._calculate_display_width(row) for row in output]
        assert display_widths[0] == display_widths[1], "ANSI codes affected width calculation"

    def test_print_rows_string_row(self):
        """Test that string rows (not arrays) pass through unchanged."""
        output = []
        mock_func = Mock(side_effect=lambda line: output.append(line))

        rows = [
            (mock_func, ["Col1", "Col2"]),
            (mock_func, "Plain string row"),
            (mock_func, ["Data1", "Data2"]),
        ]

        print_rows(rows)

        assert len(output) == 3
        assert output[1] == "Plain string row"

    def test_print_rows_empty_strings(self):
        """Test handling of empty strings."""
        output = []
        mock_func = Mock(side_effect=lambda line: output.append(line))

        rows = [
            (mock_func, ["Col1", "Col2", "Col3"]),
            (mock_func, ["", "data", ""]),
        ]

        print_rows(rows)

        assert len(output) == 2
        assert "data" in output[1]

    def test_print_rows_japanese_korean(self):
        """Test with Japanese and Korean characters."""
        output = []
        mock_func = Mock(side_effect=lambda line: output.append(line))

        rows = [
            (mock_func, ["日本語", "한글", "Text"]),  # Japanese, Korean, English
            (mock_func, ["テスト", "테스트", "test"]),  # All mean "test"
        ]

        print_rows(rows)

        # All CJK characters should be measured properly
        display_widths = [self._calculate_display_width(row) for row in output]
        assert display_widths[0] == display_widths[1], (
            f"Japanese/Korean characters not handled correctly: widths={display_widths}"
        )
