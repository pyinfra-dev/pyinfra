from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

import pytest


@pytest.fixture(scope="session")
def ssh_ca_keypair(tmp_path_factory) -> dict[str, Path]:
    if shutil.which("ssh-keygen") is None:
        pytest.skip("ssh-keygen not available on PATH")

    ssh_dir = tmp_path_factory.mktemp("ssh")
    ca_key = ssh_dir / "ca"
    user_key = ssh_dir / "user_ed25519"
    user_cert = ssh_dir / "user_ed25519-cert.pub"

    subprocess.run(
        ["ssh-keygen", "-t", "ed25519", "-N", "", "-f", str(ca_key), "-C", "test-ca"],
        check=True,
        capture_output=True,
    )
    subprocess.run(
        ["ssh-keygen", "-t", "ed25519", "-N", "", "-f", str(user_key), "-C", "test-user"],
        check=True,
        capture_output=True,
    )
    subprocess.run(
        [
            "ssh-keygen",
            "-s",
            str(ca_key),
            "-I",
            "test-user",
            "-n",
            "testuser",
            "-V",
            "+1h",
            str(user_key) + ".pub",
        ],
        check=True,
        capture_output=True,
    )

    assert user_cert.is_file(), "ssh-keygen did not produce the expected certificate"

    return {
        "ca_key": ca_key,
        "user_key": user_key,
        "user_cert": user_cert,
        "ssh_dir": ssh_dir,
    }
