import re
from pathlib import Path


def get_version_from_changelog():
    # Regex matching pattern followed by 3 numerical values separated by '.'
    pattern = re.compile(r"^# v(?P<version>[0-9]+\.[0-9]+(\.[0-9]+)?(\.?[a-z0-9]+)?)$")

    changelog_path = Path(__file__).parent.parent / "CHANGELOG.md"

    with open(changelog_path, "r", encoding="utf-8") as fn:
        for line in fn.readlines():
            match = pattern.match(line.strip())
            if match:
                return "".join(match.group("version"))
    raise RuntimeError("No version found in CHANGELOG.md")


if __name__ == "__main__":
    print(get_version_from_changelog(), end="")
