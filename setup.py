# pyinfra
# File: setup.py
# Desc: needed

from setuptools import setup


if __name__ == '__main__':
    setup(
        version='0.1.dev7',
        name='pyinfra',
        description='Deploy stuff by diff-ing the state you want against the remote server.',
        author='Nick / Fizzadar',
        author_email='pointlessrambler@gmail.com',
        url='http://github.com/Fizzadar/pyinfra',
        packages=[
            'pyinfra',
            'pyinfra.api',
            'pyinfra.facts',
            'pyinfra.facts.util',
            'pyinfra.modules',
            'pyinfra.modules.util'
        ],
        package_dir={
            'pyinfra': 'pyinfra'
        },
        scripts=[
            'bin/pyinfra'
        ],
        install_requires=[
            'gevent',
            'paramiko',
            'docopt',
            'colorama',
            'termcolor',
            'jinja2',
            'python-dateutil'
        ]
    )
