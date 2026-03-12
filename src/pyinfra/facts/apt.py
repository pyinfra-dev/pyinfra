from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Union

from typing_extensions import TypedDict, override

from pyinfra.api import FactBase

from .gpg import GpgKeyrings


@dataclass(frozen=True)
class AptRepo:
    """Represents an APT repository configuration.

    This dataclass provides type safety for APT repository definitions,
    supporting both legacy .list style and modern deb822 .sources formats.

    Provides dict-like access for backward compatibility while offering
    full type safety for modern code.
    """

    type: str  # "deb" or "deb-src"
    url: str  # Repository URL
    distribution: str  # Suite/distribution name
    components: list[str]  # List of components (e.g., ["main", "contrib"])
    options: dict[str, Union[str, list[str]]]  # Repository options

    # Dict-like interface for backward compatibility
    def __getitem__(self, key: str):
        """Dict-like access: repo['type'] works like repo.type"""
        return getattr(self, key)

    def __setitem__(self, key: str, value):
        """Dict-like assignment: repo['type'] = 'deb' works like repo.type = 'deb'"""
        setattr(self, key, value)

    def __contains__(self, key: str) -> bool:
        """Support 'key' in repo syntax"""
        return hasattr(self, key)

    def get(self, key: str, default=None):
        """Dict-like get: repo.get('type', 'deb')"""
        return getattr(self, key, default)

    def keys(self):
        """Return dict-like keys"""
        return ["type", "url", "distribution", "components", "options"]

    def values(self):
        """Return dict-like values"""
        return [self.type, self.url, self.distribution, self.components, self.options]

    def items(self):
        """Return dict-like items"""
        return [(k, getattr(self, k)) for k in self.keys()]

    @override
    def __eq__(self, other) -> bool:
        """Enhanced equality that works with dicts and AptRepo instances"""
        if isinstance(other, dict):
            return (
                self.type == other.get("type")
                and self.url == other.get("url")
                and self.distribution == other.get("distribution")
                and self.components == other.get("components")
                and self.options == other.get("options")
            )
        elif isinstance(other, AptRepo):
            return (
                self.type == other.type
                and self.url == other.url
                and self.distribution == other.distribution
                and self.components == other.components
                and self.options == other.options
            )
        return False

    def to_json(self):
        """Convert to dict for JSON serialization"""
        return dict(self.items())


@dataclass(frozen=True)
class AptSourcesFile:
    """Represents a deb822 sources file entry before expansion into individual repositories.

    This preserves the original multi-value fields from deb822 format,
    while AptRepo represents individual expanded repositories.
    """

    types: list[str]  # ["deb", "deb-src"]
    uris: list[str]  # ["http://deb.debian.org", "https://mirror.example.com"]
    suites: list[str]  # ["bookworm", "bullseye"]
    components: list[str]  # ["main", "contrib", "non-free"]
    architectures: list[str] | None = None  # ["amd64", "i386"]
    signed_by: list[str] | None = None  # ["/path/to/key1.gpg", "/path/to/key2.gpg"]
    trusted: str | None = None  # "yes"/"no"

    @classmethod
    def from_deb822_lines(cls, lines: list[str]) -> "AptSourcesFile | None":
        """Parse deb822 stanza lines into AptSourcesFile.

        Handles multi-line field values (continuation lines starting with a space
        or tab) as defined in the deb822 specification, including inline GPG keys
        in the Signed-By field.  Within a continuation value a bare `.` encodes
        an empty line (per the deb822 spec).

        Returns None if parsing failed or repository is disabled.
        """
        if not lines:
            return None

        data: dict[str, str] = {}
        current_key: str | None = None

        for line in lines:
            # Pure comment lines are never continuation lines
            if line.startswith("#"):
                continue

            # Continuation line: starts with a space or tab
            if line and line[0] in (" ", "\t") and current_key is not None:
                # A bare `.` encodes an empty line within the value
                continuation = line[1:]
                data[current_key] += "\n" + ("" if continuation == "." else continuation)
                continue

            # Empty line within the loop – stanza boundaries are handled by the caller
            if not line.strip():
                continue

            # Regular field: Field-Name: value
            if ":" in line:
                key, value = line.split(":", 1)
                current_key = key.strip()
                data[current_key] = value.strip()
            # else: malformed line without ':', skip

        # Validate required fields
        required = ("Types", "URIs", "Suites")
        if not all(field in data for field in required):
            return None

        # Filter out disabled repositories
        enabled_str = data.get("Enabled", "yes").lower()
        if enabled_str != "yes":
            return None

        # Parse Signed-By: inline armored PGP key block vs. file path(s)
        signed_by: list[str] | None = None
        signed_by_raw = data.get("Signed-By", "").strip()
        if signed_by_raw:
            if "-----BEGIN PGP" in signed_by_raw:
                # Inline OpenPGP key block — keep the entire block as a single entry
                signed_by = [signed_by_raw]
            else:
                # Space- or newline-separated absolute file paths
                signed_by = signed_by_raw.split()

        return cls(
            types=data.get("Types", "").split(),
            uris=data.get("URIs", "").split(),
            suites=data.get("Suites", "").split(),
            components=data.get("Components", "").split(),
            architectures=(
                data.get("Architectures", "").split() if data.get("Architectures") else None
            ),
            signed_by=signed_by,
            trusted=data.get("Trusted", "").lower() if data.get("Trusted") else None,
        )

    @classmethod
    def parse_sources_file(cls, lines: list[str]) -> list[AptRepo]:
        """Parse a full deb822 .sources file into AptRepo instances.

        Splits on blank lines into stanzas and parses each one.
        Returns a combined list of AptRepo instances for all stanzas.

        Args:
            lines: Lines from a .sources file
        """
        repos = []
        stanza: list[str] = []
        for raw in lines + [""]:  # sentinel blank line to flush last stanza
            line = raw.rstrip("\n")
            if line.strip() == "":
                if stanza:
                    sources_file = cls.from_deb822_lines(stanza)
                    if sources_file:
                        repos.extend(sources_file.expand_to_repos())
                    stanza = []
                continue
            stanza.append(line)
        return repos

    def expand_to_repos(self) -> list[AptRepo]:
        """Expand this sources file entry into individual AptRepo instances."""
        # Build options dict in the same format as legacy parsing
        options: dict[str, Union[str, list[str]]] = {}

        if self.architectures:
            options["arch"] = (
                self.architectures if len(self.architectures) > 1 else self.architectures[0]
            )
        if self.signed_by:
            options["signed-by"] = self.signed_by if len(self.signed_by) > 1 else self.signed_by[0]
        if self.trusted:
            options["trusted"] = self.trusted

        repos = []
        # Produce combinations – in most real-world cases these will each be one.
        for repo_type in self.types:
            for uri in self.uris:
                for suite in self.suites:
                    repos.append(
                        AptRepo(
                            type=repo_type,
                            url=uri,
                            distribution=suite,
                            components=self.components.copy(),  # copy to avoid shared reference
                            options=dict(options),  # copy per entry
                        )
                    )
        return repos


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


def parse_apt_repo(name: str) -> AptRepo | None:
    """Parse a traditional apt source line into an AptRepo.

    Args:
        name: Apt source line (e.g., "deb [arch=amd64] http://example.com focal main")

    Returns:
        AptRepo instance or None if parsing failed
    """
    regex = r"^(deb(?:-src)?)(?:\s+\[([^\]]+)\])?\s+([^\s]+)\s+([^\s]+)\s+([a-z-\s\d]*)$"

    matches = re.match(regex, name)

    if not matches:
        return None

    # Parse any options
    options = {}
    options_string = matches.group(2)
    if options_string:
        for option in options_string.split():
            key, value = option.split("=", 1)
            if "," in value:
                value = value.split(",")

            options[key] = value

    return AptRepo(
        type=matches.group(1),
        url=matches.group(3),
        distribution=matches.group(4),
        components=list(matches.group(5).split()),
        options=options,
    )


def parse_apt_list_file(lines: list[str]) -> list[AptRepo]:
    """Parse legacy .list style apt source file.

    Each non-comment, non-empty line is a discrete repository definition in the
    traditional ``deb http://... suite components`` syntax.
    Returns a list of AptRepo instances.

    Args:
        lines: Lines from a .list file
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


class AptSources(FactBase):
    """Returns a list of installed apt sources (legacy .list + deb822 .sources).

    Returns a list of AptRepo instances that behave like dicts for backward compatibility:

        [AptRepo(type="deb", url="http://archive.ubuntu.org", ...)]

    Each AptRepo can be accessed like a dict:
        repo['type']  # works like repo.type
        repo.get('url')  # works like getattr(repo, 'url')
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
            'echo "##PYINFRA_FILE $f"; '
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
        repos: list[AptRepo] = []
        current_file: str | None = None
        buffer: list[str] = []

        def flush():
            nonlocal buffer, current_file, repos
            if current_file is None or not buffer:
                buffer = []
                return

            if current_file.endswith(".sources"):
                repos.extend(AptSourcesFile.parse_sources_file(buffer))
            else:  # .list files or /etc/apt/sources.list
                repos.extend(parse_apt_list_file(buffer))
            buffer = []

        for line in output:
            if line.startswith("##PYINFRA_FILE "):
                flush()  # flush previous file buffer
                current_file = line[15:].strip()  # remove "##PYINFRA_FILE " prefix
                continue
            buffer.append(line)

        flush()  # flush the final buffer
        return repos


class AptKeys(GpgKeyrings):
    """
    Returns information on GPG keys available to APT.

    This fact reuses the GpgKeyrings infrastructure to search APT's modern keyring
    directories instead of using the deprecated apt-key command. It provides
    compatibility with the old AptKeys interface while leveraging the modern
    GPG infrastructure.

    .. code:: python

        {
            "3B4FE6ACC0B21F32": {
                "validity": "-",
                "length": 4096,
                "subkeys": {},
                "fingerprint": "790BC7277767219C42C86F933B4FE6ACC0B21F32",
                "uid_hash": "B7A02867A0C1D32B594B36C00E20C8C57E397748",
                "uid": "Ubuntu Archive Automatic Signing Key (2012) <ftpmaster@ubuntu.com>"
            },
        }
    """

    @override
    def command(self, directories: list[str] | None = None) -> str:
        return super().command(
            directories or ["/etc/apt/trusted.gpg.d", "/etc/apt/keyrings", "/usr/share/keyrings"]
        )

    @override
    def process(self, output):
        # Get the full keyring structure from parent
        keyrings_data = super().process(output)

        # Flatten to match the traditional AptKeys format: {key_id: key_details}
        # Note: if the same key ID appears in multiple keyring files, the last one wins.
        flattened_keys: dict = {}
        for keyring_path, keyring_info in keyrings_data.items():
            if "keys" in keyring_info:
                flattened_keys.update(keyring_info["keys"])

        return flattened_keys


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
