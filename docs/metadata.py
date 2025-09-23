"""
Support parsing pyinfra plugins and parsing
their metadata to docs generator.
"""

import tomllib
from dataclasses import dataclass
from typing import Literal

AllowedTagType = Literal[
    "boot",
    "containers",
    "database",
    "service-management",
    "package-manager",
    "python",
    "ruby",
    "javascript",
    "configuration-management",
    "security",
    "storage",
    "system",
    "system-ops",
    "system-facts",
    "rust",
    "version-control-system",
]


@dataclass(frozen=True)
class Tag:
    """Representation of a plugin tag."""

    value: AllowedTagType

    def __post_init__(self):
        allowed_tags = set(AllowedTagType.__args__)
        if self.value not in allowed_tags:
            raise ValueError(f"Invalid tag: {self.value}. Allowed: {allowed_tags}")

    @property
    def title_case(self) -> str:
        return " ".join([t.title() for t in self.value.split("-")])

    def __eq__(self, other):
        if isinstance(other, Tag):
            return self.value == other.value
        if isinstance(other, str):
            return self.value == other
        return NotImplemented


ALLOWED_TAGS = [Tag(tag) for tag in set(AllowedTagType.__args__)]


@dataclass
class Plugin:
    """Representation of a pyinfra plugin."""

    name: str
    # description: str # FUTURE we should grab these from doc strings
    path: str
    type: Literal["operation", "fact", "connector", "deploy"]
    tags: list[Tag]


def parse_plugins(metadata_text: str) -> list[Plugin]:
    """Given the contents of a pyinfra-metadata.toml parse out the plugins."""
    pyinfra_metadata = tomllib.loads(metadata_text).get("pyinfra", None)
    if not pyinfra_metadata:
        raise ValueError("Missing [pyinfra.plugins] section in pyinfra-metadata.toml")

    plugins = []
    for p in pyinfra_metadata["plugins"]:
        data = pyinfra_metadata["plugins"][p]
        # ensure Tag types and not strings
        data["tags"] = [Tag(t) for t in data["tags"]]
        plugin = Plugin(**data)
        plugins.append(plugin)
    return plugins
