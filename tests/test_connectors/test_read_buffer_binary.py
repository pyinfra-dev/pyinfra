from queue import Queue

from pyinfra.connectors.util import OutputLine, read_buffer


def test_read_buffer_replaces_invalid_utf8_instead_of_raising():
    """Binary command output must not kill the reader greenlet (#2023)."""
    output_queue: Queue[OutputLine] = Queue()
    # A single "line" of non-UTF-8 bytes as subprocess pipes can yield
    read_buffer("stdout", [b"\xf5binary\xff\n"], output_queue)

    line = output_queue.get_nowait()
    assert line.buffer_name == "stdout"
    assert isinstance(line.line, str)
    assert output_queue.empty()
