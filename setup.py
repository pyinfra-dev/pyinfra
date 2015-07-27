# pyinfra
# File: setup.py
# Desc: needed

from setuptools import setup


if __name__ == '__main__':
    setup(
        version='0.1.dev1',
        name='pyinfra',
        description='Stateful deploy with Python.',
        author='Nick @ Oxygem',
        author_email='nick@oxygem.com',
        url='http://github.com/Fizzadar/pyinfra',
        package_dir={
            'pyinfra': 'pyinfra'
        },
        scripts=[
            'bin/pyinfra'
        ],
        install_requires=[
            'gevent',
            'paramiko',
            'inflection',
            'docopt',
            'coloredlogs',
            'termcolor',
            'jinja2'
        ]
    )
