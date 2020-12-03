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
    'gevent>=1.5',
    'paramiko>=2.2,<3',  # 2.2 (2017) adds Ed25519Key
    'click>2',
    'colorama<1',  # Windows color support for click
    'jinja2>2,<3',
    'python-dateutil>2,<3',
    'six>1,<2',
    'setuptools',
    'configparser',
    'pywinrm',
    'distro==1.5.0',
)

ANSIBLE_REQUIRES = (  # extras for parsing Ansible inventory
    'pyyaml',
)

TEST_REQUIRES = ANSIBLE_REQUIRES + (
    # Unit testing
    'pytest==4.6.6',
    'pytest-cov==2.8.1',
    'coverage==4.5.4',
    'mock==3.0.5',
    'codecov==2.1.8',

    # Linting
    'flake8==3.8.3',
    'flake8-commas==2.0.0',
    'flake8-quotes==3.2.0',
    'flake8-import-order==0.18.1',
)

DOCS_REQUIRES = (
    'pyinfra-guzzle_sphinx_theme==0.10',
    'recommonmark==0.5.0',
    'sphinx==2.2.1 ; python_version >= "3"',
)

DEV_REQUIRES = TEST_REQUIRES + DOCS_REQUIRES + (
    # Releasing
    'wheel',
    'twine',

    # Dev debugging
    'ipython',
    'ipdb==0.10.3',
    'ipdbplugin==1.4.5',

    # Lint spellchecking, dev only (don't fail CI)
    'flake8-spellcheck==0.12.1 ; python_version >= "3"',
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
        url='https://pyinfra.com',
        project_urls={
            'Documentation': 'https://docs.pyinfra.com',
            'GitHub': 'https://github.com/Fizzadar/pyinfra',
        },
        packages=find_packages(exclude=['tests']),
        entry_points={
            'console_scripts': (
                'pyinfra=pyinfra_cli.__main__:execute_pyinfra',
            ),
            'pyinfra.connectors': [
                'ansible = pyinfra.api.connectors.ansible',
                'chroot = pyinfra.api.connectors.chroot',
                'docker = pyinfra.api.connectors.docker',
                'local = pyinfra.api.connectors.local',
                'mech = pyinfra.api.connectors.mech',
                'ssh = pyinfra.api.connectors.ssh',
                'dockerssh = pyinfra.api.connectors.dockerssh',
                'vagrant = pyinfra.api.connectors.vagrant',
                'winrm = pyinfra.api.connectors.winrm',
            ],
        },
        install_requires=INSTALL_REQUIRES,
        extras_require={
            'test': TEST_REQUIRES,
            'docs': DOCS_REQUIRES,
            'dev': DEV_REQUIRES,
            'ansible': ANSIBLE_REQUIRES,
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
            'Programming Language :: Python :: 2.7',
            'Programming Language :: Python :: 3',
            'Programming Language :: Python :: 3.5',
            'Programming Language :: Python :: 3.6',
            'Programming Language :: Python :: 3.7',
            'Programming Language :: Python :: 3.8',
            'Programming Language :: Python :: 3.9',
            'Topic :: System :: Systems Administration',
            'Topic :: System :: Installation/Setup',
            'Topic :: Utilities',
        ],
    )
