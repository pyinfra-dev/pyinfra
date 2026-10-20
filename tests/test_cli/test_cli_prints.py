from pyinfra_cli.prints import _display_width, print_rows


def _rows(*rows: list[str]) -> list[str]:
    output: list[str] = []
    print_rows([(output.append, row) for row in rows])
    return output


def test_display_width_counts_terminal_cells():
    assert _display_width("ascii") == 5
    # East Asian wide and fullwidth characters take two cells each
    assert _display_width("中文") == 4
    assert _display_width("ＡＢＣ") == 6
    # A skin tone modifier and a combining sound mark add no cells
    # (\u304b\u3099 is ka + combining voiced mark, the NFD form of ga)
    assert _display_width("👍🏽") == 2
    assert _display_width("\u304b\u3099") == 2
    # ANSI codes are not printed, so they take no cells
    assert _display_width("\033[1mhello\033[0m") == 5


def test_print_rows_ascii_table_is_unchanged():
    assert _rows(["Operation", "Hosts"], ["short", "1"]) == [
        "Operation   Hosts   ",
        "short       1       ",
    ]


def test_print_rows_pads_cjk_by_display_width():
    # The example from the issue: the CJK row must not push the next column
    # right of the header.
    assert _rows(["Operation", "Hosts"], ["随便输出一些中文试试", "1"]) == [
        "Operation" + " " * 14 + "Hosts   ",
        "随便输出一些中文试试" + " " * 3 + "1       ",
    ]


def test_print_rows_pads_coloured_cjk_in_a_later_column():
    green_ok = "\033[32m成功\033[0m"
    assert _rows(["Name", "Result", "Hosts"], ["a", green_ok, "1"], ["b", "ok", "2"]) == [
        "Name   Result   Hosts   ",
        "a      " + green_ok + " " * 5 + "1       ",
        "b      ok       2       ",
    ]


def test_print_rows_does_not_widen_zero_width_characters():
    # A skin tone modifier and a combining mark are drawn inside the
    # character before them, so they must not add padding.
    assert _rows(["Operation", "Hosts"], ["echo 👍🏽", "1"], ["\u304b\u3099", "2"]) == [
        "Operation   Hosts   ",
        "echo 👍🏽" + " " * 5 + "1       ",
        "\u304b\u3099" + " " * 10 + "2       ",
    ]
