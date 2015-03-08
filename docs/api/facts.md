## pyinfra.api.facts

A list of classes for collecting state date on remote hosts. Each contains a
command to run on the remote host, plus a method to handle parsing this data
into a dict/list/whatever.

##### pyinfra.api.facts.BlockDevices.process

```py
BlockDevices.process(
    self,
    output,
    *None,
    **None
)
```


##### pyinfra.api.facts.DebPackages.process

```py
DebPackages.process(
    self,
    output,
    *None,
    **None
)
```


##### pyinfra.api.facts.Distribution.process

```py
Distribution.process(
    self,
    output,
    *None,
    **None
)
```


##### pyinfra.api.facts.NetworkDevices.process

```py
NetworkDevices.process(
    self,
    output,
    *None,
    **None
)
```


##### pyinfra.api.facts.RPMPackages.process

```py
RPMPackages.process(
    self,
    output,
    *None,
    **None
)
```


##### pyinfra.api.facts.Users.process

```py
Users.process(
    self,
    output,
    *None,
    **None
)
```
