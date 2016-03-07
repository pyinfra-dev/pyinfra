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
html_style = 'theme.css'

# Readthedocs appears to ignore html_style
if os.environ.get('READTHEDOCS') == 'True':
    html_context = {
        'css_files': [
            'https://media.readthedocs.org/css/sphinx_rtd_theme.css',
            'https://media.readthedocs.org/css/readthedocs-doc-embed.css',
            '_static/theme.css',
        ]
    }
