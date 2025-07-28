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
    "paramiko>=2.7,<4",  # 2.7 (2019) adds OpenSSH key format + Match SSH config
    "click>2",
    "jinja2>2,<4",
    "python-dateutil>2,<3",
    "pywinrm",
    "typeguard",
    "distro>=1.6,<2",
    "packaging>=16.1",
    # Backport of graphlib used for DAG operation ordering
    'graphlib_backport ; python_version < "3.9"',
    # Backport of typing for Unpack (added 3.11)
    'typing-extensions ; python_version < "3.11"',
    # Backport of importlib.metadata for entry_points(group=...) (added 3.10)
    'importlib_metadata>=3.6 ; python_version < "3.10"',
)

TEST_REQUIRES = (
    # Must have click 8.2 since they changed CliRunner for tests
    "click>=8.2",
    # Unit testing
    "pytest==8.3.5",
    "coverage==7.7.1",
    "pytest-cov==6.0.0",
    "pytest-testinfra==10.2.2",
    # Formatting & linting
    "black==25.1.0",
    "isort==6.0.1",
    "flake8==7.1.2",
    "flake8-black==0.3.6",
    "flake8-isort==6.1.2",
    "pyyaml==6.0.2",
    # Typing
    "mypy",
    "types-cryptography",
    "types-paramiko",
    "types-python-dateutil",
    "types-PyYAML",
)

DOCS_REQUIRES = (
    "pyinfra-guzzle_sphinx_theme==0.17",
    "myst-parser==4.0.1",
    "sphinx==8.2.3",
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
        "flake8-spellcheck==0.28.0",
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
                "chroot = pyinfra.connectors.chroot:ChrootConnector",
                "docker = pyinfra.connectors.docker:DockerConnector",
                "podman = pyinfra.connectors.docker:PodmanConnector",
                "local = pyinfra.connectors.local:LocalConnector",
                "ssh = pyinfra.connectors.ssh:SSHConnector",
                "dockerssh = pyinfra.connectors.dockerssh:DockerSSHConnector",
                # Inventory only connectors
                "terraform = pyinfra.connectors.terraform:TerraformInventoryConnector",
                "vagrant = pyinfra.connectors.vagrant:VagrantInventoryConnector",
            ],
        },
        python_requires=">=3.9",
        install_requires=INSTALL_REQUIRES,
        extras_require={
            "test": TEST_REQUIRES,
            "docs": DOCS_REQUIRES,
            "dev": DEV_REQUIRES,
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
            "Programming Language :: Python :: 3.9",
            "Programming Language :: Python :: 3.10",
            "Programming Language :: Python :: 3.11",
            "Programming Language :: Python :: 3.12",
            "Topic :: System :: Systems Administration",
            "Topic :: System :: Installation/Setup",
            "Topic :: Utilities",
        ],
    )
