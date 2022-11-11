"""
.. warning::
    This connector is in alpha and may change in future releases.

Generate one or more SSH hosts from a Terraform output variable. The variable
must be a list of hostnames or IP addresses that ``pyinfra`` can connect to
over SSH. Currently there is no support for specifying SSH user/pass/port/key
from Terraform, these must be provided via ``pyinfra`` group data or ``--data``
CLI flags.

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

.. code:: python

    pyinfra @terraform/server_group.value.server_group_node_ips ...
"""

import json

from pyinfra import local, logger
from pyinfra.api.exceptions import InventoryError
from pyinfra.api.util import memoize
from pyinfra.progress import progress_spinner


@memoize
def show_warning():
    logger.warning("The @terraform connector is in alpha!")


def _flatten_dict_gen(d, parent_key, sep):
    for k, v in d.items():
        new_key = parent_key + sep + k if parent_key else k
        if isinstance(v, dict):
            yield from _flatten_dict(v, new_key, sep=sep).items()
        else:
            yield new_key, v


def _flatten_dict(d: dict, parent_key: str = "", sep: str = "."):
    return dict(_flatten_dict_gen(d, parent_key, sep))


def make_names_data(output_key=None):
    show_warning()

    if not output_key:
        raise InventoryError("No Terraform output key!")

    with progress_spinner({"fetch terraform output"}):
        tf_output_raw = local.shell("terraform output -json")

    tf_output = json.loads(tf_output_raw)
    tf_output = _flatten_dict(tf_output)

    tf_output_value = tf_output.get(output_key)
    if tf_output_value is None:
        raise InventoryError(f"No Terraform output with key: `{output_key}`")

    if not isinstance(tf_output_value, list):
        raise InventoryError(
            "Invalid Terraform output type, should be `list`, got "
            f"`{type(tf_output_value).__name__}`",
        )

    for ssh_target in tf_output_value:
        if isinstance(ssh_target, dict):
            name = ssh_target.pop("name", ssh_target.get("ssh_hostname"))
            if name is None:
                raise InventoryError(
                    "Invalid Terraform list item, missing `name` or `ssh_hostname` keys",
                )
            yield f"@terraform/{name}", ssh_target, ["@terraform"]

        elif isinstance(ssh_target, str):
            data = {"ssh_hostname": ssh_target}
            yield f"@terraform/{ssh_target}", data, ["@terraform"]

        else:
            raise InventoryError(
                "Invalid Terraform list item, should be `dict` or `str` got "
                f"`{type(ssh_target).__name__}`",
            )
