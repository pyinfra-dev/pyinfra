from pyinfra.api import Inventory


def make_inventory(hosts=("somehost", "anotherhost"), **kwargs):
    override_data = kwargs.pop("override_data", {})
    if "ssh_user" not in override_data:
        override_data["ssh_user"] = "vagrant"

    return Inventory(
        (hosts, {}),
        override_data=override_data,
        test_group=(
            [
                "somehost",
            ],
            {
                "group_data": "hello world",
            },
        ),
        **kwargs,
    )
