## pyinfra.modules.yum

Manage yum packages and repositories. Note that yum package names are case-sensitive.

Uses:

+ `yum`

##### function: packages

Manage yum packages & updates.

```py
packages(
    packages=None,
    present=True,
    upgrade=False,
    clean=False
)
```


##### function: repo

[Not implemented] Manage yum repositories.

```py
repo(
    name,
    present=True
)
```
