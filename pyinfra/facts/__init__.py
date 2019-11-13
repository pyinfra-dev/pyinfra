from glob import glob
from os import path


module_filenames = glob(path.join(path.dirname(__file__), '*.py'))
module_names = [path.basename(name)[:-3] for name in module_filenames]
__all__ = [name for name in module_names if name != '__init__']


# Actually triggers __all__ imports to builds facts index
from . import * # noqa
