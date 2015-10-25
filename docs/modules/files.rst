Files
-----

:code:`files.directory`
~~~~~~~~~~~~~~~~~~~~~~~
.. code:: python

    files.directory(name, present=True, user=None, group=None, mode=None, recursive=False)

Manage the state of directories.


:code:`files.file`
~~~~~~~~~~~~~~~~~~
.. code:: python

    files.file(name, present=True, user=None, group=None, mode=None, touch=False)

Manage the state of files.


:code:`files.put`
~~~~~~~~~~~~~~~~~
.. code:: python

    files.put(local_filename, remote_filename, user=None, group=None, mode=None, add_deploy_dir=True)

Copy a local file to the remote system.


:code:`files.sync`
~~~~~~~~~~~~~~~~~~
.. code:: python

    files.sync(source, destination, user=None, group=None, mode=None, delete=False)

Syncs a local directory with a remote one, with delete support. Note that delete will
remove extra files on the remote side, but not extra directories.


:code:`files.template`
~~~~~~~~~~~~~~~~~~~~~~
.. code:: python

    files.template(template_filename, remote_filename)

Generate a template and write it to the remote system.

