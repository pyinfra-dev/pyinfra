#!/bin/sh

# pyinfra
# File: scripts/generate_api_docs.sh
# Desc: use sphinx-apidoc + sed to autogenerate pyinfra API docs

# Fiddle with the module titles/etc
parse_files() {
    local FILEMATCH
    local PREFIX
    local MODULE_PREFIX
    local MODULE_FILE
    local NEW_FILE

    FILEMATCH=$1
    PREFIX=$2
    MODULE_PREFIX=`echo "${PREFIX}" | sed -e "s/_/./"`

    for MODULE_FILE in `ls docs/api/${FILEMATCH}.*.rst`; do
        NEW_FILE=`echo "${MODULE_FILE}" | sed -e "s/api\/${FILEMATCH}\./api\/${PREFIX}_/"`
        echo "--> Parsing $MODULE_FILE -> $NEW_FILE"

        # Make automodule work
        sed -e "s/\.\. automodule:: ${FILEMATCH}/\.\. automodule:: pyinfra.${MODULE_PREFIX}/" \
        $MODULE_FILE > $NEW_FILE

        # Update the title
        sed -i.bak -e "s/${FILEMATCH}\.\([a-z]*\) module/pyinfra.${MODULE_PREFIX}\.\1/" $NEW_FILE

        echo "--> Removing ${MODULE_FILE} & ${NEW_FILE}.bak"
        rm -f $MODULE_FILE $NEW_FILE.bak
    done
}

# Autodoc the API reference
sphinx-apidoc -e -M -f -o docs/api/ pyinfra/api/
parse_files "api" "api"

# Autodoc the modules utils reference
sphinx-apidoc -e -M -f -o docs/api/ pyinfra/modules/util/
parse_files "util" "modules_util"

# Autodoc the facts utils reference
sphinx-apidoc -e -M -f -o docs/api/ pyinfra/facts/util/
parse_files "util" "facts_util"

# Remove fluff
rm -f docs/api/util.rst docs/api/modules.rst docs/api/api.rst
