import re


def title_line(char, string):
    return "".join(char for _ in range(0, len(string)))


def format_doc_line(line):
    # Bold the <arg>: part of each line
    line = re.sub(r"\+ ([0-9a-z_\/\*]+)(.*)", r"+ **\1**\2", line)

    # Strip the first 4 characters (first indent from docstring)
    return line[4:]
