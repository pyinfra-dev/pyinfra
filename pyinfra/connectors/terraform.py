import json

from typing_extensions import override

from pyinfra import local, logger
from pyinfra.api.exceptions import InventoryError
from pyinfra.api.util import memoize
from pyinfra.progress import progress_spinner

from .base import BaseConnector


@memoize
def show_warning() -> None:
    logger.warning("The @terraform connector is in beta!")


def _flatten_dict_gen(d, parent_key, sep):
    for k, v in d.items():
        new_key = parent_key + sep + k if parent_key else k
        yield new_key, v
        if isinstance(v, dict):
            yield from _flatten_dict(v, new_key, sep=sep).items()


def _flatten_dict(d: dict, parent_key: str = "", sep: str = "."):
    return dict(_flatten_dict_gen(d, parent_key, sep))


class TerraformInventoryConnector(BaseConnector):
    """
    Generate one or more SSH hosts from a Terraform output variable. The variable
    must be a list of hostnames or dictionaries.

    Output is fetched from a flattened JSON dictionary output from ``terraform output
    -json``. For example the following object:

    .. code:: json

        {
          "server_group": {
            "value": {
              "server_group_node_ips": [
                "1.2.3.4",
                "1.2.3.5",
                "1.2.3.6"
              ]
            }
          }
        }

    The IP list ``server_group_node_ips`` would be used like so:

    .. code:: sh

        pyinfra @terraform/server_group.value.server_group_node_ips ...

    You can also specify dictionaries to include extra data with hosts:

    .. code:: json

        {
          "server_group": {
            "value": {
              "server_group_node_ips": [
                {
                    "ssh_hostname": "1.2.3.4",
                    "ssh_user": "ssh-user"
                },
                {
                    "ssh_hostname": "1.2.3.5",
                    "ssh_user": "ssh-user"
                }
              ]
            }
          }
        }

    """

    @override
    @staticmethod
    def make_names_data(name=None):
        show_warning()

        if not name:
            # This is the default which allows one to create a Terraform output
            # "pyinfra" and directly call: pyinfra @terraform ...
            name = "pyinfra_inventory.value"

        with progress_spinner({"fetch terraform output"}):
            tf_output_raw = local.shell("terraform output -json")

        assert isinstance(tf_output_raw, str)
        tf_output = json.loads(tf_output_raw)
        tf_output = _flatten_dict(tf_output)

        tf_output_value = tf_output.get(name)
        if tf_output_value is None:
            keys = "\n".join(f"   - {k}" for k in tf_output.keys())
            raise InventoryError(f"No Terraform output with key: `{name}`, valid keys:\n{keys}")

        if not isinstance(tf_output_value, (list, dict)):
            raise InventoryError(
                "Invalid Terraform output type, should be `list`, got "
                f"`{type(tf_output_value).__name__}`",
            )

        if isinstance(tf_output_value, list):
            tf_output_value = {
                "all": tf_output_value,
            }

        for group_name, hosts in tf_output_value.items():
            if not isinstance(hosts, list):
                raise InventoryError(
                    "Invalid Terraform map value type, all values should be `list`, got "
                    f"`{type(hosts).__name__}`",
                )
            for host in hosts:
                if isinstance(host, dict):
                    name = host.pop("name", host.get("ssh_hostname"))
                    if name is None:
                        raise InventoryError(
                            "Invalid Terraform list item, missing `name` or `ssh_hostname` keys",
                        )
                    yield f"@terraform/{name}", host, ["@terraform", group_name]
                elif isinstance(host, str):
                    data = {"ssh_hostname": host}
                    yield f"@terraform/{host}", data, ["@terraform", group_name]
                else:
                    raise InventoryError(
                        "Invalid Terraform list item, should be `dict` or `str` got "
                        f"`{type(host).__name__}`",
                    )
