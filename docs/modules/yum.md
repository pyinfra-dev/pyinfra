## pyinfra.modules.yum


##### pyinfra.modules.yum.packages

Manage yum packages & updates.

```py
packages(
    packages,
    present=True,
    upgrade=False,
    clean=False
)
```


##### pyinfra.modules.yum.repo

[Not implemented] Manage yum sources.

```py
repo(
    name,
    present=True
)
```


##### pyinfra.modules.yum.rpm

[Not implemented] Install/remove .rpm packages with rpm

```py
rpm(
    rpm_file,
    present=True
)
```
