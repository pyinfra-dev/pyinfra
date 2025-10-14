"""
Support parsing pyinfra-metadata.toml

Currently just parses plugins and their metadata.
"""

import tomllib
from typing import Literal, get_args

from pydantic import BaseModel, TypeAdapter, field_validator

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
    "rust",
    "version-control-system",
]


class Tag(BaseModel):
    """Representation of a plugin tag."""

    value: AllowedTagType

    @field_validator("value", mode="before")
    def _validate_value(cls, v) -> AllowedTagType:
        allowed_tags = set(get_args(AllowedTagType))
        if v not in allowed_tags:
            raise ValueError(f"Invalid tag: {v}. Allowed: {allowed_tags}")
        return v

    @property
    def title_case(self) -> str:
        return " ".join([t.title() for t in self.value.split("-")])


ALLOWED_TAGS = [Tag(value=tag) for tag in set(get_args(AllowedTagType))]


class Plugin(BaseModel):
    """Representation of a pyinfra plugin."""

    name: str
    # description: str # FUTURE we should grab these from doc strings
    path: str
    type: Literal["operation", "fact", "connector", "deploy"]
    tags: list[Tag]

    @field_validator("tags", mode="before")
    def _wrap_tags(cls, v):
        return [Tag(value=tag) if not isinstance(tag, Tag) else tag for tag in v]


def parse_plugins(metadata_text: str) -> list[Plugin]:
    """Given the contents of a pyinfra-metadata.toml parse out the plugins."""
    pyinfra_metadata = tomllib.loads(metadata_text).get("pyinfra", None)
    if not pyinfra_metadata:
        raise ValueError("Missing [pyinfra.plugins] section in pyinfra-metadata.toml")
    return TypeAdapter(list[Plugin]).validate_python(pyinfra_metadata["plugins"].values())
