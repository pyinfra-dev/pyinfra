"""
The ``@vagrant`` connector reads the current Vagrant status and generates an
inventory for any running VMs.

.. code:: shell

    # Run on all hosts
    pyinfra @vagrant ...

    # Run on a specific VM
    pyinfra @vagrant/my-vm-name ...

    # Run on multiple named VMs
    pyinfra @vagrant/my-vm-name,@vagrant/another-vm-name ...
"""

import json
from os import path
from queue import Queue
from threading import Thread

from pyinfra import local, logger
from pyinfra.api.exceptions import InventoryError
from pyinfra.api.util import memoize
from pyinfra.progress import progress_spinner


def _get_vagrant_ssh_config(queue, progress, target):
    logger.debug("Loading SSH config for %s", target)

    queue.put(
        local.shell(
            "vagrant ssh-config {0}".format(target),
            splitlines=True,
        ),
    )

    progress(target)


@memoize
def get_vagrant_config(limit=None):
    logger.info("Getting Vagrant config...")

    if limit and not isinstance(limit, (list, tuple)):
        limit = [limit]

    with progress_spinner({"vagrant status"}) as progress:
        output = local.shell(
            "vagrant status --machine-readable",
            splitlines=True,
        )
        progress("vagrant status")

    targets = []

    for line in output:
        line = line.strip()
        _, target, type_, data = line.split(",", 3)

        # Skip anything not in the limit
        if limit is not None and target not in limit:
            continue

        # For each running container - fetch it's SSH config in a thread - this
        # is because Vagrant *really* slow to run each command.
        if type_ == "state" and data == "running":
            targets.append(target)

    threads = []
    config_queue = Queue()

    with progress_spinner(targets) as progress:
        for target in targets:
            thread = Thread(
                target=_get_vagrant_ssh_config,
                args=(config_queue, progress, target),
            )
            threads.append(thread)
            thread.start()

    for thread in threads:
        thread.join()

    queue_items = list(config_queue.queue)

    lines = []
    for output in queue_items:
        lines.extend([ln.strip() for ln in output])

    return lines


@memoize
def get_vagrant_options():
    if path.exists("@vagrant.json"):
        with open("@vagrant.json", "r", encoding="utf-8") as f:
            return json.loads(f.read())
    return {}


def _make_name_data(host):
    vagrant_options = get_vagrant_options()
    vagrant_host = host["Host"]

    data = {
        "ssh_hostname": host["HostName"],
    }

    for config_key, data_key in (
        ("Port", "ssh_port"),
        ("User", "ssh_user"),
        ("IdentityFile", "ssh_key"),
    ):
        if config_key in host:
            data[data_key] = host[config_key]

    # Update any configured JSON data
    if vagrant_host in vagrant_options.get("data", {}):
        data.update(vagrant_options["data"][vagrant_host])

    # Work out groups
    groups = vagrant_options.get("groups", {}).get(vagrant_host, [])

    if "@vagrant" not in groups:
        groups.append("@vagrant")

    return "@vagrant/{0}".format(host["Host"]), data, groups


def make_names_data(limit=None):
    vagrant_ssh_info = get_vagrant_config(limit)

    logger.debug("Got Vagrant SSH info: \n%s", vagrant_ssh_info)

    hosts = []
    current_host = None

    for line in vagrant_ssh_info:
        # Vagrant outputs an empty line between each host
        if not line:
            if current_host:
                hosts.append(_make_name_data(current_host))

            current_host = None
            continue

        key, value = line.split(" ", 1)

        if key == "Host":
            if current_host:
                hosts.append(_make_name_data(current_host))

            # Set the new host
            current_host = {
                key: value,
            }

        elif current_host:
            current_host[key] = value

        else:
            logger.debug("Extra Vagrant SSH key/value (%s=%s)", key, value)

    if current_host:
        hosts.append(_make_name_data(current_host))

    if not hosts:
        if limit:
            raise InventoryError("No running Vagrant instances matching `{0}` found!".format(limit))
        raise InventoryError("No running Vagrant instances found!")

    return hosts
