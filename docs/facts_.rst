pyinfra uses facts to determine the existing state of a remote server. Operations use this
information to generate commands which alter the state. Facts can be easily tested like so:

.. code:: shell

    $ pyinfra -i myhost.com --fact date
    ...
    "myhost.com": "2016-01-01T16:20:00+00:00"

Facts are namespaced similarly to modules, use the sidebar to browse those available.
