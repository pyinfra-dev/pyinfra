#!/usr/bin/env python
"""Generate a changelog from commits since the last git tag.

Usage:
    python scripts/generate_changelog.py [FROM_REF]

If FROM_REF is not provided, the most recent tag is used.
Outputs changelog entries grouped by category, with GitHub usernames for
external contributors.
"""

import re
import subprocess
import sys
from collections import defaultdict

# The repo owner - commits by this user don't get (@username) attribution
OWNER = "Fizzadar"
REPO = "pyinfra-dev/pyinfra"

# Map a scope's leading component (e.g. "operations" in "operations.files") to a
# changelog category. Also used to categorise legacy "component.sub: desc" subjects.
COMPONENT_CATEGORIES = {
    "api": "Core",
    "arguments": "Core",
    "connectors": "Connectors",
    "cli": "CLI",
    "docs": "Docs/meta",
    "meta": "Docs/meta",
    "tests": "Docs/meta",
    "operations": "Operations/facts",
    "facts": "Operations/facts",
}

# Fallback by conventional-commit type when the scope is absent or unrecognised.
TYPE_CATEGORIES = {
    "docs": "Docs/meta",
    "test": "Docs/meta",
    "ci": "Docs/meta",
    "build": "Docs/meta",
    "chore": "Docs/meta",
    "style": "Docs/meta",
}

CATEGORY_ORDER = [
    "Core",
    "Operations/facts",
    "Connectors",
    "CLI",
    "Docs/meta",
]

# Conventional commit subject: type(scope)!: description
CONVENTIONAL_RE = re.compile(
    r"^(?P<type>[a-z]+)(?:\((?P<scope>[^)]*)\))?(?P<breaking>!)?:\s*(?P<desc>.+)$",
)


def get_previous_tag():
    result = subprocess.run(
        ["git", "describe", "--tags", "--abbrev=0", "HEAD"],
        capture_output=True,
        text=True,
    )
    return result.stdout.strip()


def get_commits(from_ref):
    result = subprocess.run(
        [
            "git",
            "log",
            f"{from_ref}..HEAD",
            "--format=%H|||%s",
            "--reverse",
        ],
        capture_output=True,
        text=True,
    )
    commits = []
    for line in result.stdout.strip().splitlines():
        if not line:
            continue
        sha, subject = line.split("|||", 1)
        commits.append((sha, subject))
    return commits


def get_github_username(sha):
    print(f"Get commit username: {sha}", file=sys.stderr)
    result = subprocess.run(
        ["gh", "api", f"repos/{REPO}/commits/{sha}", "--jq", ".author.login"],
        capture_output=True,
        text=True,
    )
    return result.stdout.strip() or None


def categorize(subject):
    parsed = CONVENTIONAL_RE.match(subject)
    if parsed:
        scope = parsed["scope"]
        if scope:
            component = scope.split(".")[0]
            if component in COMPONENT_CATEGORIES:
                return COMPONENT_CATEGORIES[component]
        return TYPE_CATEGORIES.get(parsed["type"], "Other")

    # Legacy "component.sub: desc" subjects (pre-conventional-commits).
    if ":" in subject:
        prefix = subject.split(":")[0].split(".")[0]
        return COMPONENT_CATEGORIES.get(prefix, "Other")
    return "Other"


def format_entry(subject, username):
    parsed = CONVENTIONAL_RE.match(subject)
    if parsed and parsed["scope"]:
        # Drop the redundant type, keeping "scope: desc" to match historical entries.
        text = f"{parsed['scope']}: {parsed['desc']}"
    else:
        text = subject
    if parsed and parsed["breaking"]:
        text = f"**BREAKING** {text}"

    entry = f"- {text}"
    if username and username != OWNER:
        entry += f" (@{username})"
    return entry


def main():
    from_ref = sys.argv[1] if len(sys.argv) > 1 else get_previous_tag()
    if not from_ref:
        print("Error: could not determine previous tag", file=sys.stderr)
        sys.exit(1)

    print(f"# Changelog: {from_ref}..HEAD\n", file=sys.stderr)

    commits = get_commits(from_ref)
    if not commits:
        print("No commits found.", file=sys.stderr)
        sys.exit(0)

    grouped = defaultdict(list)
    for sha, subject in commits:
        # Skip release commits ("Release v3.8.0" or "chore(release): ...")
        if subject.startswith("Release ") or subject.startswith("chore(release)"):
            continue

        username = get_github_username(sha)
        category = categorize(subject)
        grouped[category].append(format_entry(subject, username))

    # Print in defined order, then any remaining
    printed = set()
    for cat in CATEGORY_ORDER:
        if cat in grouped:
            print(f"{cat}:\n")
            for entry in grouped[cat]:
                print(entry)
            print()
            printed.add(cat)

    for cat, entries in grouped.items():
        if cat not in printed:
            print(f"{cat}:\n")
            for entry in entries:
                print(entry)
            print()


if __name__ == "__main__":
    main()
