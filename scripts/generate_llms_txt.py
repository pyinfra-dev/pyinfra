#!/usr/bin/env python

"""Generate llms.txt (curated index) and llms-full.txt (full-content monolith).

Follows the llmstxt.org convention so LLM-backed tools can consume the pyinfra
documentation without crawling the rendered site. Outputs land directly in
``docs/`` so zensical copies them verbatim to the build root next to the
rendered HTML pages.
"""

from __future__ import annotations

import sys
from inspect import getdoc, getfullargspec, getmembers, isclass, signature
from os import environ, makedirs, path
from pathlib import Path
from types import FunctionType, MethodType, ModuleType
from importlib import import_module

from pyinfra.api import metadata
from pyinfra.api.connectors import get_all_connectors
from pyinfra.api.facts import FactBase, ShortFactBase

sys.path.append(path.dirname(path.realpath(__file__)))
from docs_utils import including_sub_modules, prepare_docstring, remove_dups  # noqa: E402


BASE_URL = "https://docs.pyinfra.com/en"
VERSION = environ.get("DOCS_VERSION", "latest")
URL_PREFIX = f"{BASE_URL}/{VERSION}"

TAGLINE = (
    "pyinfra turns Python code into shell commands and runs them on your "
    "servers. Execute ad-hoc commands and write declarative operations against "
    "SSH, local, Docker, chroot, and other targets. Operations diff desired "
    "state against gathered facts and yield only the reconciling commands."
)

# Curated pages with summaries. Ordering mirrors the zensical.toml nav.
USING_PAGES = [
    ("getting-started", "Getting started", "Quickest path to your first pyinfra deploy."),
    ("using-operations", "Using operations", "Write reusable, committable deploys in Python."),
    (
        "inventory-data",
        "Inventory & data",
        "Groups, host/group data, and environment-driven config.",
    ),
    (
        "arguments",
        "Global arguments",
        "Arguments available on every operation: _sudo, _env, _serial, etc.",
    ),
    ("cli", "CLI reference", "pyinfra command-line usage for ad-hoc and scripted runs."),
    ("faq", "FAQ", "Answers to frequently asked questions."),
]
DEPLOY_REF_PAGES = [
    ("operations", "Operations index", "Browse all built-in operations by tag."),
    ("facts", "Facts index", "Browse all built-in facts by tag."),
    ("connectors", "Connectors", "Built-in connectors: @ssh, @docker, @local, @terraform, ..."),
]
HOW_IT_WORKS_PAGES = [
    ("deploy-process", "Deploy process", "How pyinfra orders, diffs, and executes operations."),
    ("api/deploys", "API: deploys", "Package and share deploys as Python packages."),
    ("api/operations", "API: operations", "Write your own operations."),
    ("api/facts", "API: facts", "Write your own facts."),
    ("api/connectors", "API: connectors", "Write your own connectors."),
    ("api/index", "API overview", "Use pyinfra as a Python library."),
]
META_PAGES = [
    ("install", "Installation", "Install pyinfra on your system."),
    ("support", "Support", "Where to get help."),
    ("contributing", "Contributing", "How to contribute to pyinfra."),
    ("compatibility", "Compatibility", "Supported Python and platform versions."),
    ("performance", "Performance", "Performance tuning tips."),
    (
        "llms",
        "LLM-friendly docs",
        "How to consume llms.txt and llms-full.txt from AI tools and agents.",
    ),
    ("changes", "Changelog", "Release notes."),
]

# Pages whose raw contents are concatenated into llms-full.txt.
FULL_PAGE_SLUGS = (
    ["install"]
    + [slug for slug, _, _ in USING_PAGES]
    + ["deploy-process"]
    + [slug for slug, _, _ in HOW_IT_WORKS_PAGES if slug.startswith("api/")]
    + ["compatibility", "performance", "llms", "contributing", "support"]
)

REPO_ROOT = Path(__file__).resolve().parent.parent
DOCS_DIR = REPO_ROOT / "docs"
OUT_DIR = DOCS_DIR
METADATA_FILE = REPO_ROOT / "pyinfra-metadata.toml"


def page_url(slug: str) -> str:
    return f"{URL_PREFIX}/{slug}.html"


def find_source_file(slug: str) -> Path | None:
    for ext in (".md", ".rst"):
        candidate = DOCS_DIR / f"{slug}{ext}"
        if candidate.exists():
            return candidate
    return None


def _collapse(text: str) -> str:
    return " ".join(text.split())


def first_paragraph(doc: str | None) -> str:
    if not doc:
        return ""
    first = doc.strip().split("\n\n", 1)[0]
    return _collapse(first)


def truncate(text: str, limit: int = 180) -> str:
    if len(text) <= limit:
        return text
    return text[: limit - 3].rstrip() + "..."


def _safe_import(module_path: str) -> ModuleType | None:
    try:
        return import_module(module_path)
    except Exception as exc:  # broad: importing plugin code can trigger extras, env checks
        print(f"--> skip import {module_path}: {exc}")
        return None


def plugin_summary(plugin: metadata.Plugin) -> str:
    module = _safe_import(f"pyinfra.{plugin.type}s.{plugin.name}")
    summary = truncate(first_paragraph(module.__doc__)) if module else ""
    if summary:
        return summary
    if plugin.tags:
        return ", ".join(t.title_case for t in plugin.tags)
    return plugin.name


# ---- llms.txt ----------------------------------------------------------------


def build_index(plugins: list[metadata.Plugin]) -> str:
    ops = sorted([p for p in plugins if p.type == "operation"], key=lambda p: p.name)
    facts = sorted([p for p in plugins if p.type == "fact"], key=lambda p: p.name)
    connectors = sorted(get_all_connectors().items(), key=lambda item: item[0])

    out: list[str] = []
    out.append("# pyinfra")
    out.append("")
    out.append(f"> {TAGLINE}")
    out.append("")

    def section(title: str, pages: list[tuple[str, str, str]]) -> None:
        out.append(f"## {title}")
        out.append("")
        for slug, label, summary in pages:
            out.append(f"- [{label}]({page_url(slug)}): {summary}")
        out.append("")

    section("Using pyinfra", USING_PAGES)
    section("Deploy reference", DEPLOY_REF_PAGES)

    out.append("## Operations")
    out.append("")
    for plugin in ops:
        out.append(
            f"- [{plugin.name}]({page_url(f'operations/{plugin.name}')}): {plugin_summary(plugin)}"
        )
    out.append("")

    out.append("## Facts")
    out.append("")
    for plugin in facts:
        out.append(
            f"- [{plugin.name}]({page_url(f'facts/{plugin.name}')}): {plugin_summary(plugin)}"
        )
    out.append("")

    out.append("## Connectors")
    out.append("")
    for name, connector in connectors:
        doc = truncate(first_paragraph(getdoc(connector)))
        out.append(f"- [@{name}]({page_url(f'connectors/{name}')}): {doc or name}")
    out.append("")

    section("How pyinfra works", HOW_IT_WORKS_PAGES)
    section("Optional", META_PAGES)

    return "\n".join(out).rstrip() + "\n"


# ---- llms-full.txt -----------------------------------------------------------


def _extract_operation_funcs(module: ModuleType) -> list[tuple[str, FunctionType]]:
    funcs = [
        (
            f"{m.__name__.split('.')[-1]}.{key}" if m != module else key,
            getattr(value, "_inner"),
        )
        for m in including_sub_modules(module)
        for key, value in getmembers(m)
        if (
            isinstance(value, FunctionType)
            and value.__module__.startswith(m.__name__)
            and getattr(value, "_inner", False)
            and not value.__name__.startswith("_")
            and not key.startswith("_")
        )
    ]
    return remove_dups(funcs)


def _extract_fact_classes(module: ModuleType) -> list[tuple[str, type]]:
    classes = [
        (key, value)
        for m in including_sub_modules(module)
        for key, value in getmembers(m)
        if (
            isclass(value)
            and (issubclass(value, FactBase) or issubclass(value, ShortFactBase))
            and value.__module__.startswith(m.__name__)
            and value is not FactBase
            and value is not ShortFactBase
            and not value.__name__.endswith("Base")
        )
    ]
    return remove_dups(classes)


def render_operation_section(module_name: str) -> list[str]:
    module = _safe_import(f"pyinfra.operations.{module_name}")
    if module is None:
        return []

    lines: list[str] = []
    lines.append(f"## Operations: {module_name}")
    lines.append("")
    lines.append(f"Source: {page_url(f'operations/{module_name}')}")
    lines.append("")
    if module.__doc__:
        lines.append(prepare_docstring(module.__doc__))
        lines.append("")

    for name, func in _extract_operation_funcs(module):
        decorated = getattr(func, "_inner", None)
        while decorated:
            func = decorated  # type: ignore[assignment]
            decorated = getattr(func, "_inner", None)

        try:
            sig = str(signature(func))
        except (TypeError, ValueError):
            sig = "(...)"

        lines.append(f"### `{module_name}.{name}{sig}`")
        lines.append("")
        if getattr(func, "is_idempotent", None) is False:
            notice = (
                getattr(func, "idempotent_notice", None)
                or "This operation always executes commands and is not idempotent."
            )
            lines.append(f"_Stateless:_ {notice}")
            lines.append("")
        if func.__doc__:
            lines.append(prepare_docstring(func.__doc__))
            lines.append("")

    return lines


def render_fact_section(module_name: str) -> list[str]:
    module = _safe_import(f"pyinfra.facts.{module_name}")
    if module is None:
        return []

    lines: list[str] = []
    lines.append(f"## Facts: {module_name}")
    lines.append("")
    lines.append(f"Source: {page_url(f'facts/{module_name}')}")
    lines.append("")
    if module.__doc__:
        lines.append(prepare_docstring(module.__doc__))
        lines.append("")

    for fact_name, cls in _extract_fact_classes(module):
        args_repr = ""
        command_attr = getattr(cls, "command", None)
        if isinstance(command_attr, (FunctionType, MethodType)):
            argspec = getfullargspec(command_attr)
            args = [a for a in argspec.args if a != "self"]
            if args:
                args_repr = ", " + ", ".join(args)

        lines.append(f"### `{module_name}.{fact_name}`")
        lines.append("")
        lines.append(f"    host.get_fact({fact_name}{args_repr})")
        lines.append("")
        if cls.__doc__:
            lines.append(prepare_docstring(cls.__doc__))
            lines.append("")

    return lines


def render_connector_section(name: str, connector: type) -> list[str]:
    lines: list[str] = []
    lines.append(f"## Connector: @{name}")
    lines.append("")
    lines.append(f"Source: {page_url(f'connectors/{name}')}")
    lines.append("")
    doc = getdoc(connector)
    if doc:
        lines.append(prepare_docstring(doc))
        lines.append("")
    return lines


def build_full(plugins: list[metadata.Plugin]) -> str:
    ops = sorted([p for p in plugins if p.type == "operation"], key=lambda p: p.name)
    facts = sorted([p for p in plugins if p.type == "fact"], key=lambda p: p.name)
    connectors = sorted(get_all_connectors().items(), key=lambda item: item[0])

    out: list[str] = []
    out.append("# pyinfra — full documentation")
    out.append("")
    out.append(f"> {TAGLINE}")
    out.append("")
    out.append(
        f"Auto-generated from the pyinfra source tree at version `{VERSION}`. "
        "For the rendered HTML site, see "
        f"{BASE_URL}/{VERSION}/."
    )
    out.append("")

    for slug in FULL_PAGE_SLUGS:
        src = find_source_file(slug)
        if not src:
            print(f"--> skip page {slug}: file not found")
            continue
        content = src.read_text(encoding="utf-8").rstrip()
        out.append(f"# {slug}")
        out.append("")
        out.append(f"Source: {page_url(slug)}")
        out.append("")
        out.append(content)
        out.append("")
        out.append("---")
        out.append("")

    for plugin in ops:
        section = render_operation_section(plugin.name)
        if section:
            out.extend(section)
            out.append("---")
            out.append("")

    for plugin in facts:
        section = render_fact_section(plugin.name)
        if section:
            out.extend(section)
            out.append("---")
            out.append("")

    for name, connector in connectors:
        out.extend(render_connector_section(name, connector))
        out.append("---")
        out.append("")

    return "\n".join(out).rstrip() + "\n"


# ---- entrypoint --------------------------------------------------------------


def build_llms_docs() -> None:
    makedirs(OUT_DIR, exist_ok=True)
    plugins = metadata.parse_plugins(METADATA_FILE.read_text(encoding="utf-8"))

    index = build_index(plugins)
    full = build_full(plugins)

    index_path = OUT_DIR / "llms.txt"
    full_path = OUT_DIR / "llms-full.txt"
    index_path.write_text(index, encoding="utf-8")
    full_path.write_text(full, encoding="utf-8")
    print(f"--> wrote {index_path} ({len(index)} bytes)")
    print(f"--> wrote {full_path} ({len(full)} bytes)")


if __name__ == "__main__":
    print("### Building llms.txt")
    build_llms_docs()
