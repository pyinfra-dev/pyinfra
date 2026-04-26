# ruff: noqa: F401
# Intentional unused imports: this fixture verifies that imports in a group
# data file do not leak into inventory.group_data (issue #1297).
import os
from os.path import join as path_join

from pyinfra import inventory

exported_value = "this_should_be_included"

_underscore = os.name  # ignored regardless (leading underscore filter)
