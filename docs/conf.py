from datetime import date
from os import environ, mkdir, path
from shutil import rmtree

import guzzle_sphinx_theme

from pyinfra import __version__, local
from pyinfra.api import metadata

copyright = "Nick Barrett {0} — pyinfra v{1}".format(
    date.today().year,
    __version__,
)

extensions = [
    "sphinx.ext.autodoc",
    "sphinx.ext.napoleon",
    "sphinx.ext.autosectionlabel",
    "guzzle_sphinx_theme",
    "myst_parser",
]
autosectionlabel_prefix_document = True

source_suffix = [".rst", ".md"]

master_doc = "index"
project = "pyinfra"
author = "Fizzadar"

version = environ.get("DOCS_VERSION", "latest")
language = "en"

pygments_style = "monokai"

# Theme style override
html_short_title = "Home"
html_theme = "guzzle_sphinx_theme"
html_theme_path = guzzle_sphinx_theme.html_theme_path()
html_static_path = ["static"]
html_theme_options = {
    "docsearch_api_key": "25a25b5f5310f306641f9ce07dcb06eb",
    "docsearch_app_id": "XXGX6EX4KA",
    "docsearch_index_name": "pyinfra",
    "plausible_domain": "docs.pyinfra.com",
    "plausible_stats_domain": "stats.oxygem.com",
    "doc_versions": ["3.x", "2.x", "1.x", "0.x", "latest"],
    "primary_doc_version": "3.x",
}

myst_heading_anchors = 3

templates_path = ["templates"]

html_favicon = "static/logo_small.png"

exclude_patterns = [
    "_deploy_globals.rst",
]


def rstjinja(app, docname, source):
    """
    Render certain pages as a jinja templates.
    """
    # this should only be run when building html
    if app.builder.format != "html":
        return
    # We currently only render docs/operations.rst
    # and docs/facts.rst as jinja2 templates
    if docname in ["operations", "facts"]:
        src = source[0]
        rendered = app.builder.templates.render_string(src, app.config.html_context)
        source[0] = rendered


def setup(app):
    app.connect("source-read", rstjinja)
    this_dir = path.dirname(path.realpath(__file__))
    scripts_dir = path.abspath(path.join(this_dir, "..", "scripts"))
    metadata_file = path.abspath(path.join(this_dir, "..", "pyinfra-metadata.toml"))
    if not path.exists(metadata_file):
        raise ValueError("No pyinfra-metadata.toml in project root")
    with open(metadata_file, "r") as file:
        metadata_text = file.read()
    plugins = metadata.parse_plugins(metadata_text)

    operation_plugins = sorted([p for p in plugins if p.type == "operation"], key=lambda p: p.name)
    fact_plugins = sorted([p for p in plugins if p.type == "fact"], key=lambda p: p.name)
    html_context = {
        "operation_plugins": operation_plugins,
        "fact_plugins": fact_plugins,
        "tags": metadata.ALLOWED_TAGS,
        "docs_language": language,
        "docs_version": version,
    }
    app.config.html_context = html_context

    for auto_docs_name in ("operations", "facts", "apidoc", "connectors"):
        auto_docs_path = path.join(this_dir, auto_docs_name)
        if path.exists(auto_docs_path):
            rmtree(auto_docs_path)
        mkdir(auto_docs_path)

    local.shell(
        (
            "python {0}/generate_api_docs.py".format(scripts_dir),
            "python {0}/generate_arguments_doc.py".format(scripts_dir),
            "python {0}/generate_connectors_docs.py".format(scripts_dir),
            "python {0}/generate_facts_docs.py".format(scripts_dir),
            "python {0}/generate_operations_docs.py".format(scripts_dir),
        ),
        print_input=True,
    )
