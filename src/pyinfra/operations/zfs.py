"""
Manage ZFS filesystems.
"""

from pyinfra import host
from pyinfra.api import QuoteString, StringCommand, operation
from pyinfra.facts.zfs import ZfsDatasets, ZfsSnapshots


@operation()
def dataset(
    dataset_name,
    present=True,
    recursive=False,
    sparse=None,
    volume_size=None,
    properties=None,
    **extra_props,
):
    """
    Create, destroy or set properties on a  ZFS dataset (e.g. filesystem,
    volume, snapshot).

    + dataset_name: name of the filesystem to operate on
    + present: whether the named filesystem should exist
    + recursive: whether to create parent datasets, or destroy child datasets
    + sparse: for volumes, whether to create a sparse volume with no allocation
    + volume_size: the size of the volume
    + properties: the ZFS properties that should be set on the dataset.
    + **extra_props: additional props; merged with `properties` for convenience

    **Examples:**

    .. code:: python

        from pyinfra.operations import zfs
        zfs.dataset(
            "tank/srv",
            mountpoint="/srv",
            compression="lz4",
            properties={"com.sun:auto_snapshot": "true"}
        )
        zfs.dataset("tank/vm-disks/db_srv_04", volume_size="32G") # creates a volume
        zfs.dataset("tank/home@old_version", present=False)

    """

    noop_msg = f"{dataset_name} is already {'present' if present else 'absent'}"

    properties = {**(properties or {}), **extra_props}

    datasets = host.get_fact(ZfsDatasets)

    existing_dataset = datasets.get(dataset_name)

    if present and not existing_dataset:
        bits: list[str | QuoteString] = ["zfs create"]
        for prop, value in properties.items():
            bits += ["-o", QuoteString(f"{prop}={value}")]
        if recursive:
            bits.append("-p")
        if sparse:
            bits.append("-s")
        if volume_size:
            bits += ["-V", QuoteString(str(volume_size))]
        bits.append(QuoteString(dataset_name))
        yield StringCommand(*bits)

    elif present and existing_dataset:
        prop_args = [
            f"{prop}={value}"
            for prop, value in properties.items()
            if existing_dataset.get(prop) != value
        ]
        if prop_args:
            yield StringCommand(
                "zfs set",
                *[QuoteString(prop_arg) for prop_arg in prop_args],
                QuoteString(dataset_name),
            )
        else:
            host.noop(noop_msg)

    elif existing_dataset and not present:
        destroy_bits: list[str | QuoteString] = ["zfs destroy"]
        if recursive:
            destroy_bits.append("-r")
        destroy_bits.append(QuoteString(dataset_name))
        yield StringCommand(*destroy_bits)

    else:
        host.noop(noop_msg)


@operation()
def snapshot(snapshot_name, present=True, recursive=False, properties=None, **extra_props):
    """
    Create or destroy a ZFS snapshot, or modify its properties.

    + dataset_name: name of the filesystem to operate on
    + present: whether the named filesystem should exist
    + recursive: whether to snapshot child datasets
    + properties: the ZFS properties that should be set on the snapshot.
    + **extra_props: additional props; merged with `properties` for convenience

    **Examples:**

    .. code:: python

        zfs.snapshot("tank/home@weekly_backup")

    """
    properties = {**(properties or {}), **extra_props}
    snapshots = host.get_fact(ZfsSnapshots)

    if snapshot_name in snapshots or not present:
        yield from dataset._inner(snapshot_name, present=present, properties=properties)

    else:
        bits: list[str | QuoteString] = ["zfs snap"]
        for prop, value in properties.items():
            bits += ["-o", QuoteString(f"{prop}={value}")]
        if recursive:
            bits.append("-r")
        bits.append(QuoteString(snapshot_name))
        yield StringCommand(*bits)


@operation()
def volume(
    volume_name, size, sparse=False, present=True, recursive=False, properties=None, **extra_props
):
    """
    Create or destroy a ZFS volume, or modify its properties.

    + volume_name: name of the volume to operate on
    + size: the size of the volume
    + sparse: create a sparse volume
    + present: whether the named volume should exist
    + recursive: whether to create parent datasets or destroy child datasets
    + properties: the ZFS properties that should be set on the snapshot.
    + **extra_props: additional props; merged with `properties` for convenience

    **Examples:**

    .. code:: python

        zfs.volume("tank/vm-disks/db_srv_04", "32G")

    """
    properties = {**(properties or {}), **extra_props}
    yield from dataset._inner(
        volume_name,
        volume_size=size,
        present=present,
        sparse=sparse,
        recursive=recursive,
        properties=properties,
    )


@operation()
def filesystem(fs_name, present=True, recursive=False, properties=None, **extra_props):
    """
    Create or destroy a ZFS filesystem, or modify its properties.

    + fs_name: name of the volume to operate on
    + present: whether the named volume should exist
    + recursive: whether to create parent datasets or destroy child datasets
    + properties: the ZFS properties that should be set on the snapshot.
    + **extra_props: additional props; merged with `properties` for convenience

    **Examples:**

    .. code:: python

        zfs.filesystem("tank/vm-disks/db_srv_04", "32G")

    """
    properties = {**(properties or {}), **extra_props}
    yield from dataset._inner(
        fs_name,
        present=present,
        recursive=recursive,
        properties=properties,
    )
