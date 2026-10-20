#!/usr/bin/env python

import sys
from importlib import import_module
from inspect import getmembers, isclass, signature
from os import makedirs, path
from pathlib import Path
from types import FunctionType

from pyinfra.api.facts import FactBase
from pyinfra.api.metadata import ALLOWED_TAGS, parse_plugins

sys.path.append(path.dirname(path.realpath(__file__)))
from docs_utils import (
    format_doc_line,
    get_module_names,
    including_sub_modules,
    prepare_docstring,
    remove_dups,
)  # noqa: E402

MODULE_DEF_LINE_MAX = 90


CARD_SCRIPT = """\
<script>
(function () {
  var run = function () {
    var select = document.getElementById('pyinfra-operations-tag');
    var container = document.querySelector('[data-cards-container="operations"]');
    if (!select || !container) return;
    if (select.dataset.pyinfraInit === '1') return;
    select.dataset.pyinfraInit = '1';
    select.addEventListener('change', function () {
      var value = select.value;
      container.querySelectorAll('.pyinfra-card').forEach(function (card) {
        var tags = (card.dataset.tags || '').split(',');
        card.style.display = (value === 'all' || tags.indexOf(value) !== -1) ? '' : 'none';
      });
    });
  };
  if (typeof document$ !== 'undefined' && document$.subscribe) {
    document$.subscribe(run);
  } else {
    document.addEventListener('DOMContentLoaded', run);
  }
})();
</script>
"""


def _build_cards_html(plugins):
    """Generate the operation card grid HTML snippet."""
    operation_plugins = sorted(
        [p for p in plugins if p.type == "operation"],
        key=lambda p: p.name,
    )

    # Tag options: use ALLOWED_TAGS sorted alphabetically by title_case for
    # determinism. Include every tag even if unused; the filter still works.
    tag_options = sorted({tag.title_case for tag in ALLOWED_TAGS})

    lines = []
    lines.append('<div class="pyinfra-cards-filter">')
    lines.append('  <label for="pyinfra-operations-tag">Filter by tag:</label>')
    lines.append('  <select id="pyinfra-operations-tag" data-cards-filter="operations">')
    lines.append('    <option value="all">All</option>')
    for title in tag_options:
        lines.append(f'    <option value="{title}">{title}</option>')
    lines.append("  </select>")
    lines.append("</div>")
    lines.append("")
    lines.append('<div class="pyinfra-cards-grid" data-cards-container="operations">')

    for plugin in operation_plugins:
        tag_titles = [tag.title_case for tag in plugin.tags]
        data_tags = ",".join(tag_titles)
        lines.append(f'  <div class="pyinfra-card" data-tags="{data_tags}">')
        lines.append(f'    <h3><a href="operations/{plugin.name}.html">{plugin.name}</a></h3>')
        lines.append('    <div class="pyinfra-card-tags">')
        for title in tag_titles:
            lines.append(f'      <span class="pyinfra-tag">{title}</span>')
        lines.append("    </div>")
        lines.append("  </div>")

    lines.append("</div>")
    lines.append("")
    lines.append(CARD_SCRIPT)
    return "\n".join(lines)


def build_operations_docs():
    this_dir = path.dirname(path.realpath(__file__))
    project_dir = path.abspath(path.join(this_dir, ".."))
    docs_dir = path.join(project_dir, "docs")
    pyinfra_dir = Path(project_dir) / "src" / "pyinfra"

    snippets_dir = path.join(project_dir, "snippets")
    makedirs(path.join(docs_dir, "operations"), exist_ok=True)
    makedirs(snippets_dir, exist_ok=True)

    for module_name in get_module_names(pyinfra_dir / "operations"):
        lines = [
            "---",
            "template: operation.html",
            "---",
            "",
        ]

        print(f"--> Doing module: {module_name}")
        module = import_module(f"pyinfra.operations.{module_name}")

        lines.append(f"# {module_name} Operations")
        lines.append("")

        module_doc = prepare_docstring(module.__doc__)
        if module_doc:
            lines.append(module_doc)
            lines.append("")

        operation_facts = [
            (key, value)
            for m in including_sub_modules(module)
            for key, value in getmembers(m)
            if (isclass(value) and issubclass(value, FactBase))
        ]

        unique_facts = remove_dups(operation_facts)
        if unique_facts:
            items = []
            for key, value in unique_facts:
                fact_module = value.__module__.replace("pyinfra.facts.", "")
                items.append(
                    f"[`{fact_module}.{key}`](../facts/{fact_module}.md#{fact_module}-{key})"
                )
            lines.append("Facts used in these operations: {}.".format(", ".join(items)))
            lines.append("")

        all_operation_functions = [
            (f"{m.__name__.split('.')[-1]}.{key}" if m != module else key, value._inner)
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
        operation_functions = remove_dups(all_operation_functions)

        for name, func in operation_functions:
            decorated_func = getattr(func, "_inner", None)
            while decorated_func:
                func = decorated_func
                decorated_func = getattr(func, "_inner", None)

            anchor = f"{module_name}-{name}"
            lines.append(f"## `{module_name}.{name}` {{ #{anchor} }}")
            lines.append("")

            if getattr(func, "is_idempotent", None) is False:
                text = (
                    getattr(func, "idempotent_notice", None)
                    or "This operation will always execute commands and is not idempotent."
                )
                lines.append('!!! important "Stateless operation"')
                lines.append(f"    {text}")
                lines.append("")

            doc = prepare_docstring(func.__doc__)
            description = ""
            if doc:
                docbits = doc.split("\n")
                description_lines: list[str] = []
                for line in docbits:
                    if line:
                        description_lines.append(line)
                    else:
                        break
                if description_lines:
                    description = " ".join(description_lines).strip()
                    doc = "\n".join(docbits[len(description_lines) :]).lstrip("\n")

            if description:
                lines.append(description)
                lines.append("")

            # Get signature; format with bounded width; append **kwargs.
            sig = signature(func)
            if hasattr(sig, "format"):
                args_string = sig.format(max_width=MODULE_DEF_LINE_MAX)
            else:
                args_string = str(sig)
            if args_string == "()":
                args_string = "(**kwargs)"
            else:
                args_string = f"{args_string[:-1].rstrip()},\n    **kwargs,\n"
                args_string = f"{args_string.replace('   ', '        ')}    )"

            lines.append("```python")
            lines.append(f"{module_name}.{name}{args_string}")
            lines.append("```")
            lines.append("")

            if doc.strip():
                formatted = "\n".join(format_doc_line(line) for line in doc.split("\n")).strip()
                lines.append(formatted)
                lines.append("")

            lines.append('!!! note "Global arguments"')
            lines.append(
                "    This operation also inherits all [global arguments](../arguments.md)."
            )
            lines.append("")

        module_filename = path.join(docs_dir, "operations", f"{module_name}.md")
        print(f"--> Writing {module_filename}")

        with open(module_filename, "w", encoding="utf-8") as outfile:
            outfile.write("\n".join(lines).rstrip() + "\n")

    # Cards snippet
    metadata_path = Path(project_dir) / "pyinfra-metadata.toml"
    plugins = parse_plugins(metadata_path.read_text(encoding="utf-8"))
    cards_path = path.join(snippets_dir, "operations-cards.html")
    print(f"--> Writing {cards_path}")
    with open(cards_path, "w", encoding="utf-8") as outfile:
        outfile.write(_build_cards_html(plugins))


if __name__ == "__main__":
    print("### Building operations docs")
    build_operations_docs()
