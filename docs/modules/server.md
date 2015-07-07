## pyinfra.modules.server

The server module takes care of os-level state. Targets POSIX compatability, tested on Linux/BSD.

Uses POSIX commands:

+ `echo`, `cat`
+ `hostname`, `uname`
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
user()
```
