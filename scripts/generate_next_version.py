import argparse
import re
from pathlib import Path


def get_version_from_changelog() -> str:
    # Regex matching pattern followed by 3 numerical values separated by '.'
    pattern = re.compile(r"^# v(?P<version>[0-9]+\.[0-9]+(\.[0-9]+)?(\.?[a-z0-9]+)?)$")

    changelog_path = Path(__file__).parent.parent / "CHANGELOG.md"

    with open(changelog_path, encoding="utf-8") as fn:
        for line in fn.readlines():
            match = pattern.match(line.strip())
            if match:
                return "".join(match.group("version"))
    raise RuntimeError("No version found in CHANGELOG.md")


def set_pyproject_version(version: str) -> None:
    pyproject_path = Path(__file__).parent.parent / "pyproject.toml"
    content = pyproject_path.read_text(encoding="utf-8")

    new_content, count = re.subn(
        r'^version = "[^"]*"',
        f'version = "{version}"',
        content,
        count=1,
        flags=re.MULTILINE,
    )
    if count != 1:
        raise RuntimeError("No version found in pyproject.toml")

    pyproject_path.write_text(new_content, encoding="utf-8")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--write",
        action="store_true",
        help="write the version into pyproject.toml",
    )
    args = parser.parse_args()

    version = get_version_from_changelog()
    if args.write:
        set_pyproject_version(version)
    print(version, end="")
