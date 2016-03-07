# pyinfra
# File: docs/conf.py
# Desc: minimal Sphinx config

import os


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

# Because RTD decided to add their CSS *below* the template header, in dev we have to
# put the theme CSS after the custom CSS (so dev == rtd). But for actual RTD we want to
# put our styles as the only CSS file, which will be included before RTDs silly overrides.
if os.environ.get('READTHEDOCS') == 'True':
    style_file = '_static/theme.css'
else:
    html_style = 'theme.css'
    style_file = '_static/css/theme.css'

html_context = {
    'css_files': [style_file]
}
