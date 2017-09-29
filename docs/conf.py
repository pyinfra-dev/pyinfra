# pyinfra
# File: docs/conf.py
# Desc: minimal Sphinx config

from better import better_theme_path

from pyinfra import __version__


extensions = [
    # Official
    'sphinx.ext.autodoc',
    'sphinx.ext.napoleon',
]

source_suffix = '.rst'
master_doc = 'index'
project = 'pyinfra'
copyright = '2017, Nick Barrett'
author = 'Fizzadar'
version = 'develop'
pygments_style = 'sphinx'

# Theme style override
html_title = 'pyinfra {0}'.format(__version__)
html_short_title = 'Home'
html_theme = 'better'
html_theme_path = [better_theme_path]
html_static_path = ['static']

templates_path = ['templates']

html_sidebars = {
    '**': ['pyinfra_sidebar.html'],
}

html_theme_options = {
    'cssfiles': ['_static/pyinfra.css'],
    'scriptfiles': ['_static/sidebar.js'],
}
