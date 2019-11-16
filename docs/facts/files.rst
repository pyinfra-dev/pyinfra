Files
-----

:code:`directory`
~~~~~~~~~~~~~~~~~

.. code:: python

    host.fact.directory(name)


:code:`file`
~~~~~~~~~~~~

.. code:: python

    host.fact.file(name)


:code:`find_directories`
~~~~~~~~~~~~~~~~~~~~~~~~

.. code:: python

    host.fact.find_directories(name)


Returns a list of directories from a start point, recursively using find.



:code:`find_files`
~~~~~~~~~~~~~~~~~~

.. code:: python

    host.fact.find_files(name)


Returns a list of files from a start point, recursively using find.



:code:`find_in_file`
~~~~~~~~~~~~~~~~~~~~

.. code:: python

    host.fact.find_in_file(name, pattern)


Checks for the existence of text in a file using grep. Returns a list of matching
lines if the file exists, and ``None`` if the file does not.



:code:`find_links`
~~~~~~~~~~~~~~~~~~

.. code:: python

    host.fact.find_links(name)


Returns a list of links from a start point, recursively using find.



:code:`link`
~~~~~~~~~~~~

.. code:: python

    host.fact.link(name)


:code:`sha1_file`
~~~~~~~~~~~~~~~~~

.. code:: python

    host.fact.sha1_file(name)


Returns a SHA1 hash of a file. Works with both sha1sum and sha1.



:code:`socket`
~~~~~~~~~~~~~~

.. code:: python

    host.fact.socket(name)

