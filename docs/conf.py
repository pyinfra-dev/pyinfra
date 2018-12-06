# pyinfra
# File: docs/conf.py
# Desc: minimal Sphinx config

from datetime import date, datetime

from better import better_theme_path

from pyinfra import __version__


_today = date.today()
copyright = '{0}, Nick Barrett'.format(datetime.strftime(_today, '%Y'))

extensions = [
    # Official
    'sphinx.ext.autodoc',
    'sphinx.ext.napoleon',
]

source_suffix = '.rst'
master_doc = 'index'
project = 'pyinfra'
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
