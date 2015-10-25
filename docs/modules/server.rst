Server
------


The server module takes care of os-level state. Targets POSIX compatability, tested on Linux/BSD.

:code:`server.script`
~~~~~~~~~~~~~~~~~~~~~
.. code:: python

    server.script(filename)

Upload and execute a local script on the remote host.


:code:`server.shell`
~~~~~~~~~~~~~~~~~~~~
.. code:: python

    server.shell()

Run raw shell code.


:code:`server.user`
~~~~~~~~~~~~~~~~~~~
.. code:: python

    server.user(name, present=True, home=None, shell=None, public_keys=None)

Manage Linux users & their ssh `authorized_keys`. Options:

+ **public_keys**: list of public keys to attach to this user


:code:`server.wait`
~~~~~~~~~~~~~~~~~~~
.. code:: python

    server.wait(port=None)

Waits for a port to come active on the target machine. Requires netstat, checks every 1s.

