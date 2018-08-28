Ssh
---


Execute commands and up/download files *from* the remote host.

Eg: ``pyinfra -> inventory-host.net <-> another-host.net``

:code:`ssh.command`
~~~~~~~~~~~~~~~~~~~

Execute commands on other servers over SSH.

.. code:: python

    ssh.command(hostname, command, ssh_user=None)

+ **hostname**: the hostname to connect to
+ **command**: the command to execute
+ **ssh_user**: connect with this user


:code:`ssh.download`
~~~~~~~~~~~~~~~~~~~~

Download files from other servers using ``scp``.

.. code:: python

    ssh.download(hostname, filename, local_filename=None, force=False, ssh_keyscan=False, ssh_user=None)

+ **hostname**: hostname to upload to
+ **filename**: file to download
+ **local_filename**: where to download the file to (defaults to ``filename``)
+ **force**: always download the file, even if present locally
+ **ssh_keyscan**: execute ``ssh.keyscan`` before uploading the file
+ **ssh_user**: connect with this user


:code:`ssh.keyscan`
~~~~~~~~~~~~~~~~~~~

Check/add hosts to the ``~/.ssh/known_hosts`` file.

.. code:: python

    ssh.keyscan(hostname, force=False)

+ **hostname**: hostname that should have a key in ``known_hosts``
+ **force**: if the key already exists, remove and rescan


:code:`ssh.upload`
~~~~~~~~~~~~~~~~~~

Upload files to other servers using ``scp``.

.. code:: python

    ssh.upload(
        hostname, filename, remote_filename=None, use_remote_sudo=False, ssh_keyscan=False,
        ssh_user=None
    )

+ **hostname**: hostname to upload to
+ **filename**: file to upload
+ **remote_filename**: where to upload the file to (defaults to ``filename``)
+ **use_remote_sudo**: upload to a temporary location and move using sudo
+ **ssh_keyscan**: execute ``ssh.keyscan`` before uploading the file
+ **ssh_user**: connect with this user

