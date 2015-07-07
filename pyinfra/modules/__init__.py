# pyinfra
# File: pyinfa/modules/__init__.py
# Desc: Define __all__ for pydocs

from os import path
from glob import glob


module_filenames = glob(path.join(path.dirname(__file__), '*.py'))
module_names = [path.basename(name)[:-3] for name in module_filenames]
__all__ = [name for name in module_names if name != '__init__']
