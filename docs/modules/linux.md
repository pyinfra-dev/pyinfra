# Linux


## linux.directory(name, present=True, user=None, group=None, permissions=None, recursive=False)

Manage the state of directories.


## linux.file(name, present=True, user=None, group=None, permissions=None, touch=False)

Manage the state of files.


## linux.init(name, running=True, restarted=False)

Manage the state of init.d services.


## linux.user(name, present=True, home=None, shell=None, public_keys=None, delete_keys=False)

Manage Linux users & their ssh `authorized_keys`.
