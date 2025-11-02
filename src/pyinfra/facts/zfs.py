"""
Gather information about ZFS filesystems.
"""

from typing_extensions import override

from pyinfra.api import FactBase, ShortFactBase


def _process_zfs_props_table(output):
    datasets: dict = {}
    for line in output:
        dataset, property, value, source = tuple(line.split("\t"))
        if dataset not in datasets:
            datasets[dataset] = {}
        datasets[dataset][property] = value
    return datasets


class ZfsPools(FactBase):
    @override
    def command(self) -> str:
        return "zpool get -H all"

    @override
    def requires_command(self) -> str:
        return "zpool"

    @override
    def process(self, output):
        return _process_zfs_props_table(output)


class ZfsDatasets(FactBase):
    @override
    def command(self) -> str:
        return "zfs get -H all"

    @override
    def requires_command(self) -> str:
        return "zfs"

    @override
    def process(self, output):
        return _process_zfs_props_table(output)


class ZfsFilesystems(ShortFactBase):
    fact = ZfsDatasets

    @override
    def process_data(self, data):
        return {name: props for name, props in data.items() if props.get("type") == "filesystem"}


class ZfsSnapshots(ShortFactBase):
    fact = ZfsDatasets

    @override
    def process_data(self, data):
        return {name: props for name, props in data.items() if props.get("type") == "snapshot"}


class ZfsVolumes(ShortFactBase):
    fact = ZfsDatasets

    @override
    def process_data(self, data):
        return {name: props for name, props in data.items() if props.get("type") == "volume"}


# TODO: remove these in v4! Or flip the convention and remove all the other fact prefixes!
Pools = ZfsPools
Datasets = ZfsDatasets
Filesystems = ZfsFilesystems
Snapshots = ZfsSnapshots
Volumes = ZfsVolumes
