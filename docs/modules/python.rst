Python
------


The Python module allows you to execute Python code within the context of a deploy.

:code:`python.call`
~~~~~~~~~~~~~~~~~~~

Execute a Python function within a deploy.

.. code:: python

    python.call(func)

+ **func**: the function to execute
+ **args**: additional arguments to pass to the function
+ **kwargs**: additional keyword arguments to pass to the function

Callback functions arge passed the state, host, and any args/kwargs passed
into the operation directly, eg:

.. code:: python

    def my_callback(state, host, hello=None):
        ...

    python.call(my_callback, hello='world')


:code:`python.raise_exception`
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
.. code:: python

    python.raise_exception(exception_class)

