#!/usr/bin/env python

from os import path


def cleanup_words():
    with open(path.join("tests", "words.txt"), "r", encoding="utf-8") as f:
        data = f.read()

    lines = data.splitlines()
    lines = [line for line in lines if not line.startswith("#")]

    lines = sorted(set(lines))

    lines.insert(0, "# it is automatically cleaned/sorted by scripts/cleanup_words.py")
    lines.insert(0, "# This is a list of additional words for flake8-spellcheck")

    with open(path.join("tests", "words.txt"), "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
        f.write("\n")


if __name__ == "__main__":
    cleanup_words()
