## pyinfra.modules.server

The server module attempts to take care of os-level state. Targets POSIX compatability, tested on Linux/BSD.

Uses POSIX commands:

+ `echo`, `cat`
+ `hostname`, `uname`
+ `touch`, `mkdir`, `chown`, `chmod`
+ `useradd`, `userdel`, `usermod`

##### function: script

Upload and execute a local script on the remote host.

```py
script(
    filename
)
```


##### function: shell

Run raw shell code.

```py
shell()
```


##### function: user

Manage Linux users & their ssh `authorized_keys`.

```py
user(
    name,
    present=True,
    home=None,
    shell=None,
    public_keys=None # list of public keys to attach to this user
)
```
