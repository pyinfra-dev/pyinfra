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
project = 'pyinfra'
copyright = '2015, Nick Barrett (Fizzadar)'
author = 'Fizzadar'
version = 'develop'
pygments_style = 'sphinx'

# Theme style override
html_theme = 'sphinx_rtd_theme'
html_static_path = ['static']
html_style = 'css/theme.css'
