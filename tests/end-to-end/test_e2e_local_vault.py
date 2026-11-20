"""
Local integration tests for the vault operations: encrypt then decrypt round-trip.
"""

import pytest


@pytest.mark.end_to_end
@pytest.mark.end_to_end_local
def test_int_local_vault_encrypt_decrypt_round_trip(helpers, tmp_path):
    plaintext = "\n".join(["hello world"] * 32)
    (tmp_path / "plain.txt").write_text(plaintext)

    helpers.run_check_output(
        "PYINFRA_VAULT_PASSWORD=secret pyinfra -y -v @local vault.encrypt plain.txt cipher.txt",
        expected_lines=["@local] Success"],
        cwd=tmp_path,
    )

    assert (tmp_path / "cipher.txt").read_text().startswith("$PYINFRA_VAULT")

    helpers.run_check_output(
        "PYINFRA_VAULT_PASSWORD=secret pyinfra -y -v @local vault.decrypt cipher.txt plain2.txt",
        expected_lines=["@local] Success"],
        cwd=tmp_path,
    )

    assert (tmp_path / "plain2.txt").read_text() == plaintext
