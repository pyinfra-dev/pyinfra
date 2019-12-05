Brew
----

:code:`brew_casks`
~~~~~~~~~~~~~~~~~~

.. code:: python

    host.fact.brew_casks


Returns a dict of installed brew casks:

.. code:: python

    'package_name': ['version'],
    ...



:code:`brew_packages`
~~~~~~~~~~~~~~~~~~~~~

.. code:: python

    host.fact.brew_packages


Returns a dict of installed brew packages:

.. code:: python

    'package_name': ['version'],
    ...



:code:`brew_taps`
~~~~~~~~~~~~~~~~~

.. code:: python

    host.fact.brew_taps


Returns a list of brew taps.


