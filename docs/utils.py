import re


def title_line(char, string):
    return "".join(char for _ in range(0, len(string)))


def format_doc_line(line):
    # Bold the <arg>: part of each line, escaping * prefixes for RST compatibility
    def _bold_arg(m):
        stars = m.group(1).replace("*", "\\*")
        return f"+ **{stars}{m.group(2)}**{m.group(3)}"

    line = re.sub(r"\+ (\*{0,2})([0-9a-z_\/]+)(.*)", _bold_arg, line)

    # Python's __doc__ attribute already dedents docstrings, so we don't need to strip anything
    return line
