#!/bin/sh

# Autodoc the API reference
sphinx-apidoc -e -M -f -o docs/api/ pyinfra/api/

# Remove useless files
rm -f docs/api/api.rst docs/api/modules.rst

# Fiddle with the module titles/etc
for MODULE_FILE in `ls docs/api/api.*.rst`; do
    NEW_FILE=`echo "$MODULE_FILE" | sed -e "s/api\/api\./api\//"`
    echo "--> Parsing $MODULE_FILE -> $NEW_FILE"

    # Make automodule work
    sed -e 's/\.\. automodule:: api/\.\. automodule:: pyinfra\.api/' \
    $MODULE_FILE > .docstmp

    # Update the title
    sed -e 's/api\.\([a-z]*\) api/\1 api/' \
    .docstmp > $NEW_FILE

    echo "--> Removing $MODULE_FILE"
    rm -f $MODULE_FILE
done

# Build the modules/*.rst docs
rm -f docs/modules/*.rst
python scripts/generate_modules_docs.py

# Build the facts.rst doc
python scripts/generate_facts_doc.py

# Build the HTML docs
sphinx-build -a docs/ docs/build/
