from __future__ import annotations

from typing_extensions import override

from pyinfra.api import FactBase


class GoPackages(FactBase):
    """
    Returns a dict of installed Go binary packages (those installed via
    ``go install``) keyed by their import path:

    .. code:: python

        {
            "github.com/example/tool": {"v1.2.3"},
        }
    """

    default = dict

    @override
    def requires_command(self) -> str:
        return "go"

    @override
    def command(self) -> str:
        return (
            "BINDIR=$(go env GOBIN); "
            '[ -z "$BINDIR" ] && BINDIR="$(go env GOPATH)/bin"; '
            '! test -d "$BINDIR" || '
            'find "$BINDIR" -maxdepth 1 -type f -perm -u+x '
            "-exec go version -m {} + 2>/dev/null"
        )

    @override
    def process(self, output: list[str]) -> dict[str, set[str]]:
        packages: dict[str, set[str]] = {}
        current_path: str | None = None

        for line in output:
            if not line.startswith("\t"):
                current_path = None
                continue

            parts = line.split("\t")
            if len(parts) < 3:
                continue

            key = parts[1]
            if key == "path":
                current_path = parts[2]
            elif key == "mod" and current_path is not None and len(parts) >= 4:
                version = parts[3]
                # `(devel)` is `go build` output, not `go install` — skip it so
                # the fact only reports versioned installs (mirrors `gem list`).
                if version != "(devel)":
                    packages.setdefault(current_path, set()).add(version)
                current_path = None

        return packages
