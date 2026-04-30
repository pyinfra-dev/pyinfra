#!/usr/bin/env python

import sys
from importlib import import_module
from inspect import getfullargspec, getmembers, isclass
from os import makedirs, path
from pathlib import Path
from types import FunctionType, MethodType

from pyinfra.api.facts import FactBase, ShortFactBase
from pyinfra.api.metadata import ALLOWED_TAGS, parse_plugins

sys.path.append(path.dirname(path.realpath(__file__)))
from docs_utils import (
    format_doc_line,
    get_module_names,
    including_sub_modules,
    prepare_docstring,
    remove_dups,
)  # noqa: E402

CARD_SCRIPT = """\
<script>
(function () {
  var run = function () {
    var select = document.getElementById('pyinfra-facts-tag');
    var container = document.querySelector('[data-cards-container="facts"]');
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
    """Generate the fact card grid HTML snippet."""
    fact_plugins = sorted(
        [p for p in plugins if p.type == "fact"],
        key=lambda p: p.name,
    )

    tag_options = sorted({tag.title_case for tag in ALLOWED_TAGS})

    lines = []
    lines.append('<div class="pyinfra-cards-filter">')
    lines.append('  <label for="pyinfra-facts-tag">Filter by tag:</label>')
    lines.append('  <select id="pyinfra-facts-tag" data-cards-filter="facts">')
    lines.append('    <option value="all">All</option>')
    for title in tag_options:
        lines.append(f'    <option value="{title}">{title}</option>')
    lines.append("  </select>")
    lines.append("</div>")
    lines.append("")
    lines.append('<div class="pyinfra-cards-grid" data-cards-container="facts">')

    for plugin in fact_plugins:
        tag_titles = [tag.title_case for tag in plugin.tags]
        data_tags = ",".join(tag_titles)
        lines.append(f'  <div class="pyinfra-card" data-tags="{data_tags}">')
        lines.append(f'    <h3><a href="facts/{plugin.name}.html">{plugin.name}</a></h3>')
        lines.append('    <div class="pyinfra-card-tags">')
        for title in tag_titles:
            lines.append(f'      <span class="pyinfra-tag">{title}</span>')
        lines.append("    </div>")
        lines.append("  </div>")

    lines.append("</div>")
    lines.append("")
    lines.append(CARD_SCRIPT)
    return "\n".join(lines)


def build_facts_docs():
    this_dir = path.dirname(path.realpath(__file__))
    project_dir = path.abspath(path.join(this_dir, ".."))
    docs_dir = path.join(project_dir, "docs")
    pyinfra_dir = Path(project_dir) / "src" / "pyinfra"

    snippets_dir = path.join(project_dir, "snippets")
    makedirs(path.join(docs_dir, "facts"), exist_ok=True)
    makedirs(snippets_dir, exist_ok=True)

    for module_name in sorted(get_module_names(pyinfra_dir / "facts")):
        lines = [
            "---",
            "template: fact.html",
            "---",
            "",
        ]
        print(f"--> Doing fact module: {module_name}")
        module = import_module(f"pyinfra.facts.{module_name}")

        lines.append(f"# {module_name} Facts")
        lines.append("")

        module_doc = prepare_docstring(module.__doc__)
        if module_doc:
            lines.append(module_doc)
            lines.append("")

        ops_paths = {
            pyinfra_dir / "operations" / name for name in [module_name, f"{module_name}.py"]
        }
        if any(p.exists() for p in ops_paths):
            lines.append(f"See also: [operations/{module_name}](../operations/{module_name}.md).")
            lines.append("")

        all_fact_classes = [
            (key, value)
            for m in including_sub_modules(module)
            for key, value in getmembers(m)
            if (
                isclass(value)
                and (issubclass(value, FactBase) or issubclass(value, ShortFactBase))
                and value.__module__.startswith(m.__name__)
                and value is not FactBase
                and not value.__name__.endswith("Base")  # hacky!
            )
        ]

        fact_classes = remove_dups(all_fact_classes)
        for fact, cls in fact_classes:
            name = fact
            args_string_and_brackets = ""

            command_attr = getattr(cls, "command", None)
            if isinstance(command_attr, (FunctionType, MethodType)):
                argspec = getfullargspec(command_attr)

                arg_defaults = (
                    [f"'{arg}'" if isinstance(arg, str) else arg for arg in argspec.defaults]
                    if argspec.defaults
                    else None
                )

                defaults = (
                    dict(
                        zip(
                            argspec.args[-len(arg_defaults) :],
                            arg_defaults,
                        ),
                    )
                    if arg_defaults
                    else {}
                )

                if len(argspec.args) and (argspec.args != ["self"]):
                    args_string_and_brackets = ", {}".format(
                        ", ".join(
                            (f"{arg}={defaults.get(arg)}" if arg in defaults else arg)
                            for arg in argspec.args
                            if arg != "self"
                        ),
                    )

            anchor = f"{module_name}-{name}"
            # Modules that re-export classes under an alias (e.g. facts/zfs.py
            # exposes both ZfsDatasets and Datasets pointing at the same class)
            # end up keyed by whichever name getmembers sees first. Emit the
            # canonical class name as an extra anchor so cross-refs resolve
            # regardless of import style.
            if cls.__name__ != name:
                lines.append(f'<a id="{module_name}-{cls.__name__}"></a>')
            lines.append(f"## `{module_name}.{name}` {{ #{anchor} }}")
            lines.append("")

            lines.append("```python")
            lines.append(f"host.get_fact({name}{args_string_and_brackets})")
            lines.append("```")
            lines.append("")

            doc = prepare_docstring(cls.__doc__)
            if doc:
                formatted = "\n".join(format_doc_line(line) for line in doc.split("\n")).strip()
                if formatted:
                    lines.append(formatted)
                    lines.append("")

        module_filename = path.join(docs_dir, "facts", f"{module_name}.md")
        print(f"--> Writing {module_filename}")

        with open(module_filename, "w", encoding="utf-8") as outfile:
            outfile.write("\n".join(lines).rstrip() + "\n")

    metadata_path = Path(project_dir) / "pyinfra-metadata.toml"
    plugins = parse_plugins(metadata_path.read_text(encoding="utf-8"))
    cards_path = path.join(snippets_dir, "facts-cards.html")
    print(f"--> Writing {cards_path}")
    with open(cards_path, "w", encoding="utf-8") as outfile:
        outfile.write(_build_cards_html(plugins))


if __name__ == "__main__":
    print("### Building fact docs")
    build_facts_docs()
