# pyinfra
# File: docs/conf.py
# Desc: minimal Sphinx config

extensions = [
    # Official
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
