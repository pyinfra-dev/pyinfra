Server
------


The server module takes care of os-level state. Targets POSIX compatibility, tested on
Linux/BSD.

:code:`server.crontab`
~~~~~~~~~~~~~~~~~~~~~~

Add/remove/update crontab entries.

.. code:: python

    server.crontab(
        command, present=True, user=None, minute='*', hour='*', month='*', day_of_week='*',
        day_of_month='*'
    )

+ **command**: the command for the cron
+ **present**: whether this cron command should exist
+ **user**: the user whose crontab to manage
+ **minute**: which minutes to execute the cron
+ **hour**: which hours to execute the cron
+ **month**: which months to execute the cron
+ **day_of_week**: which day of the week to execute the cron
+ **day_of_month**: which day of the month to execute the cron

Cron commands:
    The command is used to identify crontab entries - this means commands
    must be unique within a given users crontab. If you require multiple
    identical commands, prefix each with a nonce environment variable.


:code:`server.group`
~~~~~~~~~~~~~~~~~~~~

Add/remove system groups.

.. code:: python

    server.group(name, present=True, system=False, gid=None)

+ **name**: name of the group to ensure
+ **present**: whether the group should be present or not
+ **system**: whether to create a system group

System users:
    System users don't exist on BSD, so the argument is ignored for BSD targets.


:code:`server.hostname`
~~~~~~~~~~~~~~~~~~~~~~~

Set the system hostname.

.. code:: python

    server.hostname(hostname, hostname_file=None)

+ **hostname**: the hostname that should be set
+ **hostname_file**: the file that permanently sets the hostname

Hostname file:
    By default pyinfra will auto detect this by targetting ``/etc/hostname``
    on Linux and ``/etc/myname`` on OpenBSD.


:code:`server.modprobe`
~~~~~~~~~~~~~~~~~~~~~~~

Load/unload kernel modules.

.. code:: python

    server.modprobe(name, present=True, force=False)

+ **name**: name of the module to manage
+ **present**: whether the module should be loaded or not
+ **force**: whether to force any add/remove modules


:code:`server.script`
~~~~~~~~~~~~~~~~~~~~~

Upload and execute a local script on the remote host.

.. code:: python

    server.script(filename, chdir=None)

+ **filename**: local script filename to upload & execute
+ **chdir**: directory to cd into before executing the script


:code:`server.script_template`
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Generate, upload and execute a local script template on the remote host.

.. code:: python

    server.script_template(template_filename, chdir=None)

+ **template_filename**: local script template filename
+ **chdir**: directory to cd into before executing the script


:code:`server.shell`
~~~~~~~~~~~~~~~~~~~~

Run raw shell code.

.. code:: python

    server.shell(commands, chdir=None)

+ **commands**: command or list of commands to execute on the remote server
+ **chdir**: directory to cd into before executing commands


:code:`server.sysctl`
~~~~~~~~~~~~~~~~~~~~~

Edit sysctl configuration.

.. code:: python

    server.sysctl(name, value, persist=False, persist_file='/etc/sysctl.conf')

+ **name**: name of the sysctl setting to ensure
+ **value**: the value or list of values the sysctl should be
+ **persist**: whether to write this sysctl to the config
+ **persist_file**: file to write the sysctl to persist on reboot


:code:`server.user`
~~~~~~~~~~~~~~~~~~~

Add/remove/update system users & their ssh `authorized_keys`.

.. code:: python

    server.user(
        name, present=True, home=None, shell=None, group=None, groups=None, public_keys=None,
        delete_keys=False, ensure_home=True, system=False, uid=None
    )

+ **name**: name of the user to ensure
+ **present**: whether this user should exist
+ **home**: the users home directory
+ **shell**: the users shell
+ **group**: the users primary group
+ **groups**: the users secondary groups
+ **public_keys**: list of public keys to attach to this user, ``home`` must be specified
+ **delete_keys**: whether to remove any keys not specified in ``public_keys``
+ **ensure_home**: whether to ensure the ``home`` directory exists
+ **system**: whether to create a system account

Home directory:
    When ``ensure_home`` or ``public_keys`` are provided, ``home`` defaults to
    ``/home/{name}``.


:code:`server.wait`
~~~~~~~~~~~~~~~~~~~

Waits for a port to come active on the target machine. Requires netstat, checks every
1s.

.. code:: python

    server.wait(port=None)

+ **port**: port number to wait for

