# Apt

#### apt deb

Install/remove .deb packages with dpkg

```py
apt.deb(
    deb_file,
    present=True
)
```

#### apt packages

Install/remove/upgrade packages & update apt.

```py
apt.packages(
    packages,
    present=True,
    update=False,
    upgrade=False
)
```

#### apt repo

Manage apt sources.

```py
apt.repo(
    name,
    present=True
)
```
