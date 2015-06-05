## pyinfra.api.facts

A list of classes for collecting state date on remote hosts. Each contains a
command to run on the remote host, plus a method to handle parsing this data
into a dict/list/whatever.

### class: BlockDevices

##### method: BlockDevices.process

```py
BlockDevices.process(
    self,
    output
)
```


### class: DebPackages

##### method: DebPackages.process

```py
DebPackages.process(
    self,
    output
)
```


### class: Distribution

##### method: Distribution.process

```py
Distribution.process(
    self,
    output
)
```


### class: FactMeta

##### method: FactMeta.__init__

```py
FactMeta.__init__(
    cls,
    name,
    bases,
    attrs
)
```


### class: Hostname

##### method: Hostname.process

```py
Hostname.process(
    self,
    output
)
```


### class: NetworkDevices

##### method: NetworkDevices.process

```py
NetworkDevices.process(
    self,
    output
)
```


### class: PipPackages

##### method: PipPackages.process

```py
PipPackages.process(
    self,
    output
)
```


### class: RPMPackages

##### method: RPMPackages.process

```py
RPMPackages.process(
    self,
    output
)
```


### class: Users

##### method: Users.process

```py
Users.process(
    self,
    output
)
```
