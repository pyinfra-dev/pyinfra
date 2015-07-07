## pyinfra.modules.apt

Manage apt packages and repositories.

Uses:

+ `apt-get`
+ `apt-add-repository`

##### function: packages

Install/remove/upgrade packages & update apt.

```py
packages()
```


##### function: ppa

[Not complete] Shortcut for managing ppa apt sources.

```py
ppa(
    name,
    **kwargs
)
```


##### function: repo

[Not complete] Manage apt sources.

```py
repo(
    name,
    present=True
)
```
