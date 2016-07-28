Server
------


The server module takes care of os-level state. Targets POSIX compatability, tested on
Linux/BSD.

:code:`server.group`
~~~~~~~~~~~~~~~~~~~~

Manage system groups.

.. code:: python

    server.group(name, present=True, system=False)

+ **name**: name of the group to ensure
+ **present**: whether the group should be present or not
+ **system**: whether to create a system group

System users:
    System users don't exist on BSD, so the argument is ignored for BSD targets.


:code:`server.script`
~~~~~~~~~~~~~~~~~~~~~

Upload and execute a local script on the remote host.

.. code:: python

    server.script(filename, chdir=None)

+ **filename**: local script filename to upload & execute
+ **chdir**: directory to cd into before executing the script


:code:`server.shell`
~~~~~~~~~~~~~~~~~~~~

Run raw shell code.

.. code:: python

    server.shell(commands, chdir=None)

+ **commands**: command or list of commands to execute on the remote server
+ **chdir**: directory to cd into before executing commands


:code:`server.user`
~~~~~~~~~~~~~~~~~~~

Manage system users & their ssh `authorized_keys`. Options:

.. code:: python

    server.user(
        name, present=True, home=None, shell=None,
        group=None, groups=None, public_keys=None, ensure_home=True, system=False
    )

+ **name**: name of the user to ensure
+ **present**: whether this user should exist
+ **home**: the users home directory
+ **shell**: the users shell
+ **group**: the users primary group
+ **groups**: the users secondary groups
+ **public_keys**: list of public keys to attach to this user, ``home`` must be specified
+ **ensure_home**: whether to ensure the ``home`` directory exists
+ **system**: whether to create a system account

Home directory:
    When ``ensure_home`` or ``public_keys`` are provided, ``home`` defaults to
    ``/home/{name}``


:code:`server.wait`
~~~~~~~~~~~~~~~~~~~

Waits for a port to come active on the target machine. Requires netstat, checks every
1s.

.. code:: python

    server.wait(port=None)

+ **port**: port number to wait for

