"""
Manage ZFS filesystems.
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


class Pools(FactBase):
    @override
    def command(self) -> str:
        return "zpool get -H all"

    @override
    def process(self, output):
        return _process_zfs_props_table(output)


class Datasets(FactBase):
    @override
    def command(self) -> str:
        return "zfs get -H all"

    @override
    def process(self, output):
        return _process_zfs_props_table(output)


class Filesystems(ShortFactBase):
    fact = Datasets

    @override
    def process_data(self, data):
        return {name: props for name, props in data.items() if props.get("type") == "filesystem"}


class Snapshots(ShortFactBase):
    fact = Datasets

    @override
    def process_data(self, data):
        return {name: props for name, props in data.items() if props.get("type") == "snapshot"}


class Volumes(ShortFactBase):
    fact = Datasets

    @override
    def process_data(self, data):
        return {name: props for name, props in data.items() if props.get("type") == "volume"}
