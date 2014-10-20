# pyinfra
# File: setup.py
# Desc: needed

from setuptools import setup

from pyinfra import config


if __name__ == '__main__':
    setup(
        version=config.VERSION,
        name='pyinfra',
        description='Stateful deploy with Python.',
        author='Nick @ Oxygem',
        author_email='nick@oxygem.com',
        url='http://github.com/Fizzadar/pyinfra',
        package_dir={ 'pyinfra': 'pyinfra' },
        scripts=[
            'bin/pyinfra'
        ]
    )
