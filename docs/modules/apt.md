## pyinfra.modules.apt


##### pyinfra.modules.apt.deb

[Not implemented] Install/remove .deb packages with dpkg

```py
deb(
    deb_file,
    present=True
)
```


##### pyinfra.modules.apt.packages

Install/remove/upgrade packages & update apt.

```py
packages(
    packages,
    present=True,
    update=False,
    upgrade=False
)
```


##### pyinfra.modules.apt.ppa

[Not implemented] Shortcut for managing ppa apt sources.

```py
ppa(
    name
    **kwargs
)
```


##### pyinfra.modules.apt.repo

[Not implemented] Manage apt sources.

```py
repo(
    name,
    present=True
)
```
