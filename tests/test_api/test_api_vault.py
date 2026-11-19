import os
from json import dumps
from tempfile import TemporaryDirectory
from unittest import TestCase
from unittest.mock import patch

from cryptography.exceptions import InvalidTag

from pyinfra.api.vault import decrypt_str, encrypt_str, get_password, load


class TestVaultEncryptDecrypt(TestCase):
    def test_round_trip(self):
        plaintext = "\n".join(["hello world"] * 32)

        encrypted = encrypt_str(plaintext, "secret")

        assert encrypted.startswith("$PYINFRA_VAULT;1.0;AES256_GCM\n")
        assert decrypt_str(encrypted, "secret") == plaintext

    def test_decrypt_wrong_password(self):
        encrypted = encrypt_str("hello world", "secret")

        with self.assertRaises(InvalidTag):
            decrypt_str(encrypted, "wrong")

    def test_decrypt_invalid_vault(self):
        with self.assertRaises(ValueError) as context:
            decrypt_str("not a vault", "secret")

        assert context.exception.args[0] == "Invalid or unsupported vault"

    def test_decrypt_invalid_salt_or_nonce(self):
        vault = "$PYINFRA_VAULT;1.0;AES256_GCM\nabcd\n00\n00"

        with self.assertRaises(ValueError) as context:
            decrypt_str(vault, "secret")

        assert context.exception.args[0] == "Invalid salt or nonce"


class TestVaultLoad(TestCase):
    def test_load_json(self):
        sensitive = {"root_pass": "qwerty"}

        with TemporaryDirectory() as tmpdir:
            vault_path = os.path.join(tmpdir, "vault.txt")
            with open(vault_path, "w") as f:
                f.write(encrypt_str(dumps(sensitive), "secret"))

            assert load(vault_path, password="secret", json=True) == sensitive

    def test_load_plain(self):
        with TemporaryDirectory() as tmpdir:
            vault_path = os.path.join(tmpdir, "vault.txt")
            with open(vault_path, "w") as f:
                f.write(encrypt_str("hello world", "secret"))

            assert load(vault_path, password="secret") == "hello world"


class TestVaultGetPassword(TestCase):
    def test_from_environment(self):
        with patch.dict(os.environ, {"PYINFRA_VAULT_PASSWORD": "from-env"}):
            assert get_password() == "from-env"

    def test_prompt_fallback(self):
        env = dict(os.environ)
        env.pop("PYINFRA_VAULT_PASSWORD", None)

        with patch.dict(os.environ, env, clear=True):
            with patch("pyinfra.api.vault.getpass.getpass", return_value="from-prompt"):
                assert get_password() == "from-prompt"
