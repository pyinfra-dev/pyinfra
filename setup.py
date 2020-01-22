import sys

from io import open

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
    # Unit testing
    'pytest==4.6.6',
    'pytest-cov==2.8.1',
    'jsontest==1.4',
    'coverage==4.5.4',
    'mock==3.0.5',
    'codecov==2.0.15',

    # Linting
    'flake8',
    'flake8-commas',
    'flake8-quotes',
    'flake8-spellcheck==0.12.1 ; python_version >= "3"',
    'flake8-import-order',
)

DOCS_REQUIRES = (
    'sphinx-autobuild==0.7.1',
    'guzzle_sphinx_theme==0.7.11',
    'recommonmark==0.5.0',
    'sphinx==2.2.1 ; python_version >= "3"',
    'sphinx==1.8.5 ; python_version < "3"',
)

DEV_REQUIRES = TEST_REQUIRES + DOCS_REQUIRES + (
    # Releasing
    'wheel',
    'twine',

    # Dev debugging
    'ipdb==0.10.3',
    'ipdbplugin==1.4.5',
)


# Extract version info without importing entire pyinfra package
version_data = {}
with open('pyinfra/version.py') as f:
    exec(f.read(), version_data)

with open('README.md', 'r', encoding='utf-8') as f:
    readme = f.read()


if __name__ == '__main__':
    setup(
        version=version_data['__version__'],
        name='pyinfra',
        description='pyinfra automates/provisions/manages/deploys infrastructure.',
        long_description=readme,
        long_description_content_type='text/markdown',
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
            'test': TEST_REQUIRES,
            'docs': DOCS_REQUIRES,
            'dev': DEV_REQUIRES,
        },
        include_package_data=True,
        classifiers=[
            'Development Status :: 5 - Production/Stable',
            'Environment :: Console',
            'Intended Audience :: Developers',
            'Intended Audience :: System Administrators',
            'Intended Audience :: Information Technology',
            'License :: OSI Approved :: MIT License',
            'Operating System :: OS Independent',
            'Programming Language :: Python :: 2',
            'Programming Language :: Python :: 3',
            'Topic :: System :: Systems Administration',
            'Topic :: System :: Installation/Setup',
            'Topic :: Utilities',
        ],
    )
