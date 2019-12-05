Apt
---

:code:`apt_sources`
~~~~~~~~~~~~~~~~~~~

.. code:: python

    host.fact.apt_sources


Returns a list of installed apt sources:

.. code:: python

    {
        'type': 'deb',
        'url': 'http://archive.ubuntu.org',
        'distribution': 'trusty',
        'components', ['main', 'multiverse']
    },
    ...



:code:`deb_package`
~~~~~~~~~~~~~~~~~~~

.. code:: python

    host.fact.deb_package(name)


Returns information on a .deb file.



:code:`deb_packages`
~~~~~~~~~~~~~~~~~~~~

.. code:: python

    host.fact.deb_packages


Returns a dict of installed dpkg packages:

.. code:: python

    'package_name': ['version'],
    ...


