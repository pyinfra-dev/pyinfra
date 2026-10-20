from __future__ import annotations

from unittest import mock

import pytest

from pyinfra.connectors.ssh_util import get_private_key, load_key_with_certificate

CERT_KEY_TYPE = "ssh-ed25519-cert-v01@openssh.com"


def test_load_key_with_certificate_attaches_adjacent_cert(ssh_ca_keypair):
    key = load_key_with_certificate(str(ssh_ca_keypair["user_key"]))

    assert key.public_blob is not None
    assert key.public_blob.key_type == CERT_KEY_TYPE


def test_load_key_with_certificate_honours_explicit_cert(ssh_ca_keypair, tmp_path):
    other_cert = tmp_path / "elsewhere-cert.pub"
    other_cert.write_bytes(ssh_ca_keypair["user_cert"].read_bytes())

    key = load_key_with_certificate(
        str(ssh_ca_keypair["user_key"]),
        certificate_filename=str(other_cert),
    )

    assert key.public_blob is not None
    assert key.public_blob.key_type == CERT_KEY_TYPE


def test_load_key_with_certificate_no_cert_returns_bare_key(ssh_ca_keypair, tmp_path):
    # Same private key copied to a directory without an adjacent -cert.pub.
    bare = tmp_path / "bare_ed25519"
    bare.write_bytes(ssh_ca_keypair["user_key"].read_bytes())

    key = load_key_with_certificate(str(bare))

    assert key.public_blob is None


def test_get_private_key_expands_tilde_for_cert(ssh_ca_keypair, monkeypatch):
    # Regression: get_private_key used the unexpanded key_filename when looking
    # for the adjacent cert, silently dropping certs for ~-prefixed paths.
    home = str(ssh_ca_keypair["ssh_dir"])
    monkeypatch.setenv("HOME", home)
    # On Windows os.path.expanduser reads USERPROFILE, not HOME.
    monkeypatch.setenv("USERPROFILE", home)

    state = mock.MagicMock(cwd=None, private_keys={})

    key = get_private_key(
        state,
        key_filename="~/" + ssh_ca_keypair["user_key"].name,
        key_password="",
    )

    assert key.public_blob is not None
    assert key.public_blob.key_type == CERT_KEY_TYPE


def test_load_key_with_certificate_missing_key_raises(tmp_path):
    with pytest.raises(Exception):
        load_key_with_certificate(str(tmp_path / "nope"))
