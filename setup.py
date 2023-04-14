import re
import sys
from io import open

try:
    from setuptools import find_packages, setup

except ImportError:
    print(
        """
Error: pyinfra needs setuptools in order to install:

using pip: pip install setuptools
using a package manager (apt, yum, etc), normally named: python-setuptools
    """.strip(),
    )

    sys.exit(1)


INSTALL_REQUIRES = (
    "gevent>=1.5",
    "paramiko>=2.7,<3",  # 2.7 (2019) adds OpenSSH key format + Match SSH config
    "click>2",
    "colorama<1",  # Windows color support for click
    "jinja2>2,<4",
    "python-dateutil>2,<3",
    "setuptools",
    "configparser",
    "pywinrm",
    "distro>=1.6,<2",
    # Backport of graphlib used for DAG operation ordering
    'graphlib_backport ; python_version < "3.9"',
)

ANSIBLE_REQUIRES = ("pyyaml",)  # extras for parsing Ansible inventory

TEST_REQUIRES = ANSIBLE_REQUIRES + (
    # Unit testing
    # TODO: drop Python 3.6 support
    'pytest==7.0.1 ; python_version <= "3.6"',
    'coverage==6.2 ; python_version <= "3.6"',
    'pytest==7.2.0 ; python_version > "3.6"',
    'coverage==6.5 ; python_version > "3.6"',
    "pytest-cov==4.0.0",
    # Formatting & linting
    "black==22.3.0",
    "isort==5.10.1",
    "flake8==4.0.1",
    "flake8-black==0.3.0",
    "flake8-isort==4.1.1",
    # Typing
    "mypy==0.971",
    "types-cryptography",
    "types-paramiko",
    "types-python-dateutil",
    "types-PyYAML",
    "types-setuptools",
)

DOCS_REQUIRES = (
    "pyinfra-guzzle_sphinx_theme==0.14",
    "recommonmark==0.5.0",
    "sphinx==2.2.1",
    # Pinned to fix: https://github.com/sphinx-doc/sphinx/issues/9727
    "docutils==0.17.1",
)

DEV_REQUIRES = (
    TEST_REQUIRES
    + DOCS_REQUIRES
    + (
        # Releasing
        "wheel",
        "twine",
        # Dev debugging
        "ipython",
        "ipdb",
        "ipdbplugin",
        # Lint spellchecking, dev only (don't fail CI)
        "flake8-spellcheck==0.12.1",
        "redbaron",  # for generating type stubs
    )
)


def get_version_from_changelog():
    # Regex matching pattern followed by 3 numerical values separated by '.'
    pattern = re.compile(r"^# v(?P<version>[0-9]+\.[0-9]+(\.[0-9]+)?(\.?[a-z0-9]+)?)$")

    with open("CHANGELOG.md", "r", encoding="utf-8") as fn:
        for line in fn.readlines():
            match = pattern.match(line.strip())
            if match:
                return "".join(match.group("version"))
    raise RuntimeError("No version found in CHANGELOG.md")


def get_readme_contents():
    with open("README.md", "r", encoding="utf-8") as f:
        return f.read()


if __name__ == "__main__":
    setup(
        version=get_version_from_changelog(),
        name="pyinfra",
        description="pyinfra automates/provisions/manages/deploys infrastructure.",
        long_description=get_readme_contents(),
        long_description_content_type="text/markdown",
        author="Nick / Fizzadar",
        author_email="pointlessrambler@gmail.com",
        license="MIT",
        url="https://pyinfra.com",
        project_urls={
            "Documentation": "https://docs.pyinfra.com",
            "GitHub": "https://github.com/Fizzadar/pyinfra",
        },
        packages=find_packages(exclude=["tests", "docs"]),
        entry_points={
            "console_scripts": ("pyinfra=pyinfra_cli.__main__:execute_pyinfra",),
            "pyinfra.connectors": [
                "ansible = pyinfra.connectors.ansible",
                "chroot = pyinfra.connectors.chroot",
                "docker = pyinfra.connectors.docker",
                "local = pyinfra.connectors.local",
                "mech = pyinfra.connectors.mech",
                "ssh = pyinfra.connectors.ssh",
                "dockerssh = pyinfra.connectors.dockerssh",
                "vagrant = pyinfra.connectors.vagrant",
                "winrm = pyinfra.connectors.winrm",
                "terraform = pyinfra.connectors.terraform",
            ],
        },
        install_requires=INSTALL_REQUIRES,
        extras_require={
            "test": TEST_REQUIRES,
            "docs": DOCS_REQUIRES,
            "dev": DEV_REQUIRES,
            "ansible": ANSIBLE_REQUIRES,
        },
        include_package_data=True,
        classifiers=[
            "Development Status :: 5 - Production/Stable",
            "Environment :: Console",
            "Intended Audience :: Developers",
            "Intended Audience :: System Administrators",
            "Intended Audience :: Information Technology",
            "License :: OSI Approved :: MIT License",
            "Operating System :: OS Independent",
            "Programming Language :: Python :: 3",
            "Programming Language :: Python :: 3.6",
            "Programming Language :: Python :: 3.7",
            "Programming Language :: Python :: 3.8",
            "Programming Language :: Python :: 3.9",
            "Programming Language :: Python :: 3.10",
            "Topic :: System :: Systems Administration",
            "Topic :: System :: Installation/Setup",
            "Topic :: Utilities",
        ],
    )
