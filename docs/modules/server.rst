Server
------


The server module takes care of os-level state. Targets POSIX compatability, tested on Linux/BSD.

:code:`server.script`
~~~~~~~~~~~~~~~~~~~~~

Upload and execute a local script on the remote host.

.. code:: python

    server.script(filename)


:code:`server.shell`
~~~~~~~~~~~~~~~~~~~~

Run raw shell code.

.. code:: python

    server.shell()


:code:`server.user`
~~~~~~~~~~~~~~~~~~~

Manage Linux users & their ssh `authorized_keys`. Options:

.. code:: python

    server.user(name, present=True, home=None, shell=None, public_keys=None)

+ **public_keys**: list of public keys to attach to this user


:code:`server.wait`
~~~~~~~~~~~~~~~~~~~

Waits for a port to come active on the target machine. Requires netstat, checks every 1s.

.. code:: python

    server.wait(port=None)

