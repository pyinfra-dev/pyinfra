from __future__ import annotations

import re

from typing_extensions import TypedDict, override

from pyinfra.api import FactBase

from .gpg import GpgFactBase


def noninteractive_apt(command: str, force=False):
    args = ["DEBIAN_FRONTEND=noninteractive apt-get -y"]

    if force:
        args.append("--force-yes")

    args.extend(
        (
            '-o Dpkg::Options::="--force-confdef"',
            '-o Dpkg::Options::="--force-confold"',
            command,
        ),
    )

    return " ".join(args)


APT_CHANGES_RE = re.compile(
    r"^(\d+) upgraded, (\d+) newly installed, (\d+) to remove and (\d+) not upgraded.$"
)


def parse_apt_repo(name):
    regex = r"^(deb(?:-src)?)(?:\s+\[([^\]]+)\])?\s+([^\s]+)\s+([^\s]+)\s+([a-z-\s\d]*)$"

    matches = re.match(regex, name)

    if not matches:
        return

    # Parse any options
    options = {}
    options_string = matches.group(2)
    if options_string:
        for option in options_string.split():
            key, value = option.split("=", 1)
            if "," in value:
                value = value.split(",")

            options[key] = value

    return {
        "options": options,
        "type": matches.group(1),
        "url": matches.group(3),
        "distribution": matches.group(4),
        "components": list(matches.group(5).split()),
    }


def parse_deb822_stanza(lines: list[str]) -> list[dict[str, object]]:
    """Parse a deb822 style repository stanza.

    deb822 sources are key/value pairs separated by blank lines, eg::

        Types: deb
        URIs: http://deb.debian.org/debian
        Suites: bookworm
        Components: main contrib
        Architectures: amd64
        Signed-By: /usr/share/keyrings/debian-archive-keyring.gpg

    Returns a list of dicts matching the legacy ``parse_apt_repo`` output so the
    rest of pyinfra can remain backwards compatible. A stanza may define
    multiple types/URIs/suites which we expand into individual repo dicts.
    """

    if not lines:
        return []

    data: dict[str, str] = {}
    for line in lines:
        if not line or line.startswith("#"):
            continue
        # Field-Name: value
        try:
            key, value = line.split(":", 1)
        except ValueError:  # malformed line
            continue
        data[key.strip()] = value.strip()

    required = ("Types", "URIs", "Suites")
    if not all(field in data for field in required):  # not a valid stanza
        return []

    types = data.get("Types", "").split()
    uris = data.get("URIs", "").split()
    suites = data.get("Suites", "").split()
    components = data.get("Components", "").split()

    # Map deb822 specific fields to legacy option names
    options: dict[str, object] = {}
    if architectures := data.get("Architectures"):
        archs = architectures.split()
        if archs:
            options["arch"] = archs if len(archs) > 1 else archs[0]
    if signed_by := data.get("Signed-By"):
        signed = signed_by.split()
        options["signed-by"] = signed if len(signed) > 1 else signed[0]
    if trusted := data.get("Trusted"):
        options["trusted"] = trusted.lower()

    repos = []
    # Produce combinations – in most real-world cases these will each be one.
    for _type in types or ["deb"]:
        for uri in uris:
            for suite in suites:
                repos.append(
                    {
                        "options": dict(options),  # copy per entry
                        "type": _type,
                        "url": uri,
                        "distribution": suite,
                        "components": components,
                    }
                )
    return repos


def parse_apt_list_file(lines: list[str]) -> list[dict[str, object]]:
    """Parse legacy .list style apt source file.

    Each non-comment, non-empty line is a discrete repository definition in the
    traditional ``deb http://... suite components`` syntax.
    Returns a list of repo dicts (may be empty).
    """
    repos = []
    for raw in lines:
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        repo = parse_apt_repo(line)
        if repo:
            repos.append(repo)
    return repos


def parse_deb822_sources_file(
    lines: list[str],
) -> list[dict[str, object]]:
    """Parse a full deb822 ``.sources`` file.

    Splits on blank lines into stanzas and uses ``parse_deb822_stanza`` for each
    stanza. Returns a combined list of repo dicts for all stanzas.
    """
    repos = []
    stanza: list[str] = []
    for raw in lines + [""]:  # sentinel blank line to flush last stanza
        line = raw.rstrip("\n")
        if line.strip() == "":
            if stanza:
                repos.extend(parse_deb822_stanza(stanza))
                stanza = []
            continue
        stanza.append(line)
    return repos


class AptSources(FactBase):
    """Returns a list of installed apt sources (legacy .list + deb822 .sources).

    Backwards compatible with historical output: a flat list of dicts:

        {
            "type": "deb",
            "url": "http://archive.ubuntu.org",
            "distribution": "bookworm",
            "components": ["main", "contrib"],
            "options": { ... },
        }
    """

    @override
    def command(self) -> str:
        # We emit file boundary markers so the parser can select the correct
        # parsing function based on filename extension.
        return (
            "sh -c '"
            "for f in "
            "/etc/apt/sources.list "
            "/etc/apt/sources.list.d/*.list "
            "/etc/apt/sources.list.d/*.sources; do "
            '[ -e "$f" ] || continue; '
            'echo "##FILE $f"; '
            'cat "$f"; '
            "echo; "
            "done'"
        )

    @override
    def requires_command(self) -> str:
        return "apt"

    default = list

    @override
    def process(self, output):  # type: ignore[override]
        repos: list = []
        current_file: str | None = None
        buffer: list[str] = []

        def flush():
            nonlocal buffer, current_file, repos
            if current_file is None or not buffer:
                buffer = []
                return
            if current_file.endswith(".sources"):
                repos.extend(parse_deb822_sources_file(buffer))
            else:  # treat anything else as legacy list syntax
                repos.extend(parse_apt_list_file(buffer))
            buffer = []

        for raw_line in output:
            if raw_line.startswith("##FILE "):
                # New file marker
                flush()
                current_file = raw_line.split(" ", 1)[1].strip()
                continue
            buffer.append(raw_line)

        # Flush last file
        flush()
        return repos


class AptKeys(GpgFactBase):
    """
    Returns information on GPG keys apt has in its keychain:

    .. code:: python

        {
            "KEY-ID": {
                "length": 4096,
                "uid": "Oxygem <hello@oxygem.com>"
            },
        }
    """

    @override
    def command(self) -> str:
        # Prefer not to use deprecated apt-key even if present. Iterate over keyrings
        # directly. This maintains backwards compatibility of output with the
        # previous implementation which fell back to this method.
        return (
            "for f in "
            "  /etc/apt/trusted.gpg "
            "  /etc/apt/trusted.gpg.d/*.gpg /etc/apt/trusted.gpg.d/*.asc "
            "  /etc/apt/keyrings/*.gpg /etc/apt/keyrings/*.asc "
            "  /usr/share/keyrings/*.gpg /usr/share/keyrings/*.asc "
            "; do "
            '  [ -e "$f" ] || continue; '
            '  case "$f" in '
            "    *.asc) "
            '      gpg --batch --show-keys --with-colons --keyid-format LONG "$f" '
            "      ;; "
            "    *) "
            '      gpg --batch --no-default-keyring --keyring "$f" '
            "          --list-keys --with-colons --keyid-format LONG "
            "      ;; "
            "  esac; "
            "done"
        )


class AptSimulationDict(TypedDict):
    upgraded: int
    newly_installed: int
    removed: int
    not_upgraded: int


class SimulateOperationWillChange(FactBase[AptSimulationDict]):
    """
    Simulate an 'apt-get' operation and try to detect if any changes would be performed.
    """

    @override
    def command(self, command: str) -> str:
        # LC_ALL=C: Ensure the output is in english, as we want to parse it
        return "LC_ALL=C " + noninteractive_apt(f"{command} --dry-run")

    @override
    def requires_command(self, command: str) -> str:
        return "apt-get"

    @override
    def process(self, output) -> AptSimulationDict:
        # We are looking for a line similar to
        # "3 upgraded, 0 newly installed, 0 to remove and 0 not upgraded."
        for line in output:
            result = APT_CHANGES_RE.match(line)
            if result is not None:
                return {
                    "upgraded": int(result[1]),
                    "newly_installed": int(result[2]),
                    "removed": int(result[3]),
                    "not_upgraded": int(result[4]),
                }

        # We did not find the line we expected:
        raise Exception("Did not find proposed changes in output")
