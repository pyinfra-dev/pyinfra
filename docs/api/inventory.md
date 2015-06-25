## pyinfra.api.inventory


### class: Inventory

##### method: Inventory.__init__

```py
Inventory.__init__(
    self,
    hostnames_data,
    **kwargs
)
```

##### method: Inventory.get_data

```py
Inventory.get_data(
    self
)
```

##### method: Inventory.get_default_data

```py
Inventory.get_default_data(
    self
)
```

##### method: Inventory.get_group_data

```py
Inventory.get_group_data(
    self,
    group
)
```

##### method: Inventory.get_groups_data

Gets aggregated data from a list of groups. Vars are collected in order so, for any groups
which define the same var twice, the last group's value will hold.

```py
Inventory.get_groups_data(
    self,
    groups
)
```

##### method: Inventory.get_host_data

```py
Inventory.get_host_data(
    self,
    hostname
)
```
