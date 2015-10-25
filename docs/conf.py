# pyinfra
# File: docs/conf.py
# Desc: minimal Sphinx config

from inspect import getmembers
from importlib import import_module
from types import FunctionType

from pyinfra import modules


extensions = [
    'sphinx.ext.autodoc',
    'sphinx.ext.napoleon'
]

source_suffix = '.rst'
master_doc = 'index'
project = u'pyinfra'
copyright = u'2015, Nick Barrett (Fizzadar)'
author = u'Fizzadar'
version = 'develop'
exclude_patterns = ['_html']
pygments_style = 'sphinx'
html_theme = 'sphinx_rtd_theme'
htmlhelp_basename = 'pyinfradoc'


# Here we change the footprint of the modules in pyinfra so their args appear in apidoc,
# they are all wrapped with @operation so get (*args, **kwargs) by default.

for module_name in modules.module_names:
    module = import_module('pyinfra.modules.{0}'.format(module_name))

    for key, value in getmembers(module):
        if (
            isinstance(value, FunctionType)
            and hasattr(value, '__decorated__')
            and value.__module__ == module.__name__
        ):
            real_func = getattr(module, key).__decorated__
            setattr(module, key, real_func)
