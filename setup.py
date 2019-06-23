# pyinfra
# File: setup.py
# Desc: pyinfra package setup

import sys

try:
    from setuptools import setup, find_packages

except ImportError:
    print('''
Error: pyinfra needs setuptools in order to install:

using pip: pip install setuptools
using a package manager (apt, yum, etc), normally named: python-setuptools
    '''.strip())

    sys.exit(1)


INSTALL_REQUIRES = (
    'gevent>1,<2,!=1.5a1',
    'paramiko>1,<3',
    'click>2',
    'colorama<1',  # Windows color support for click
    'docopt<1',  # legacy
    'jinja2>2,<3',
    'python-dateutil>2,<3',
    'six>1,<2',
    'setuptools',
    'configparser',
)

TEST_REQUIRES = (
    'nose==1.3.7',
    'jsontest==1.4',
    'coverage==4.4.1',
    'mock==1.3.0',
)

DEV_REQUIRES = TEST_REQUIRES + (
    # Releasing
    'wheel',
    'twine==1.9.1',

    # Dev debugging
    'ipdb==0.10.3',
    'ipdbplugin==1.4.5',

    # Dev docs requirements
    'sphinx==1.7.7',
    'sphinx-autobuild==0.7.1',
    'sphinx-better-theme==0.1.5',
    'recommonmark==0.5.0',

    # Linting
    'flake8',
    'flake8-commas',
    'flake8-quotes',
    'flake8-import-order',
)


# Extract version info without importing entire pyinfra package
version_data = {}
with open('pyinfra/version.py') as f:
    exec(f.read(), version_data)


if __name__ == '__main__':
    setup(
        version=version_data['__version__'],
        name='pyinfra',
        description='Deploy stuff by diff-ing the state you want against the remote server.',
        author='Nick / Fizzadar',
        author_email='pointlessrambler@gmail.com',
        license='MIT',
        url='http://github.com/Fizzadar/pyinfra',
        packages=find_packages(exclude=['tests']),
        entry_points={
            'console_scripts': (
                'pyinfra=pyinfra_cli.__main__:execute_pyinfra',
            ),
        },
        install_requires=INSTALL_REQUIRES,
        extras_require={
            'dev': DEV_REQUIRES,
            'test': TEST_REQUIRES,
        },
        classifiers=[
            'Development Status :: 4 - Beta',
            'Intended Audience :: Developers',
            'Intended Audience :: System Administrators',
            'License :: OSI Approved :: MIT License',
            'Operating System :: OS Independent',
            'Programming Language :: Python :: 2',
            'Programming Language :: Python :: 3',
            'Topic :: System :: Systems Administration',
        ],
    )
