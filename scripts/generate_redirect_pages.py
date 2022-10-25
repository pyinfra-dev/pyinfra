#!/usr/bin/env python

from glob import glob
from os import environ, path

DOCS_LANGUAGE = "en"
DOCS_VERSION = environ["DOCS_VERSION"]
TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8" />
    <meta name="robots" content="noindex">
    <title>Redirecting to: {0}</title>
    <link rel="canonical" href="{0}"/>
    <meta http-equiv="refresh" content="0; url={0}" />
</head>
</html>
""".lstrip()


def generate_redirect_pages():
    this_dir = path.dirname(path.realpath(__file__))
    docs_dir = path.abspath(path.join(this_dir, "..", "docs"))
    public_dir = path.join(docs_dir, "public")

    target_docs = path.join(public_dir, DOCS_LANGUAGE, DOCS_VERSION)
    files = glob(path.join(target_docs, "*.html"))

    for file in files:
        file = path.basename(file)
        filename = path.join(public_dir, "page", file)

        with open(filename, "w", encoding="utf-8") as f:
            f.write(TEMPLATE.format(f"/{DOCS_LANGUAGE}/{DOCS_VERSION}/{file}"))

        print(f"Written: {filename}")


if __name__ == "__main__":
    print("### Building operations docs")
    generate_redirect_pages()
