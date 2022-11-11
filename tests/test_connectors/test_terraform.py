import json
from unittest import TestCase
from unittest.mock import patch

from pyinfra.api.exceptions import InventoryError
from pyinfra.connectors.terraform import make_names_data


class TestVagrantConnector(TestCase):
    def test_make_names_data_no_output_key(self):
        with self.assertRaises(InventoryError) as context:
            list(make_names_data())

        assert context.exception.args[0] == "No Terraform output key!"

    @patch("pyinfra.connectors.terraform.local.shell")
    def test_make_names_data_no_output(self, fake_shell):
        fake_shell.return_value = json.dumps({})

        with self.assertRaises(InventoryError) as context:
            list(make_names_data("output_key"))

        assert context.exception.args[0] == "No Terraform output with key: `output_key`"

    @patch("pyinfra.connectors.terraform.local.shell")
    def test_make_names_data_invalid_output(self, fake_shell):
        fake_shell.return_value = json.dumps({"output_key": "wrongvalue"})

        with self.assertRaises(InventoryError) as context:
            list(make_names_data("output_key"))

        assert (
            context.exception.args[0]
            == "Invalid Terraform output type, should be `list`, got `str`"
        )

    @patch("pyinfra.connectors.terraform.local.shell")
    def test_make_names_data_dict_invalid_item(self, fake_shell):
        fake_shell.return_value = json.dumps({"output_key": [None]})

        with self.assertRaises(InventoryError) as context:
            list(make_names_data("output_key"))

        assert (
            context.exception.args[0]
            == "Invalid Terraform list item, should be `dict` or `str` got `NoneType`"
        )

    @patch("pyinfra.connectors.terraform.local.shell")
    def test_make_names_data(self, fake_shell):
        fake_shell.return_value = json.dumps({"output_key": ["somehost"]})
        data = list(make_names_data("output_key"))

        assert data == [
            (
                "@terraform/somehost",
                {"ssh_hostname": "somehost"},
                ["@terraform"],
            ),
        ]

    @patch("pyinfra.connectors.terraform.local.shell")
    def test_make_names_data_nested(self, fake_shell):
        fake_shell.return_value = json.dumps({"output_key": {"nested_key": ["somehost"]}})
        data = list(make_names_data("output_key.nested_key"))

        assert data == [
            (
                "@terraform/somehost",
                {"ssh_hostname": "somehost"},
                ["@terraform"],
            ),
        ]

    @patch("pyinfra.connectors.terraform.local.shell")
    def test_make_names_data_dict(self, fake_shell):
        host = {
            "name": "a name",
            "ssh_hostname": "hostname",
        }
        fake_shell.return_value = json.dumps({"output_key": [host]})
        data = list(make_names_data("output_key"))

        assert data == [
            (
                "@terraform/a name",
                {"ssh_hostname": "hostname"},
                ["@terraform"],
            ),
        ]

    @patch("pyinfra.connectors.terraform.local.shell")
    def test_make_names_data_dict_no_name(self, fake_shell):
        host = {
            "not_a_name": "hostname",
        }
        fake_shell.return_value = json.dumps({"output_key": [host]})

        with self.assertRaises(InventoryError) as context:
            list(make_names_data("output_key"))

        assert (
            context.exception.args[0]
            == "Invalid Terraform list item, missing `name` or `ssh_hostname` keys"
        )
