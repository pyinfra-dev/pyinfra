## pyinfra.api.host

This file provides a class representing the current Linux server & it's state. When accessing
methods or properties, remote checks are run on all remote hosts simultaneously & cached.

##### pyinfra.api.host.Host.directory

Like a fact, but for directory information.

```py
Host.directory(
    self,
    name,
    *None,
    **None
)
```


##### pyinfra.api.host.Host.file

Like a fact, but for file information.

```py
Host.file(
    self,
    name,
    *None,
    **None
)
```
