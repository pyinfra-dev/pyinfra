import re


def title_line(char, string):
    return "".join(char for _ in range(0, len(string)))


def format_doc_line(line):
    # Bold the <arg>: part of each line
    line = re.sub(r"\+ ([0-9a-z_\/\*]+)(.*)", r"+ **\1**\2", line)

    # Python's __doc__ attribute already dedents docstrings, so we don't need to strip anything
    return line
