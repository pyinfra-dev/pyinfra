Dnf
---

:code:`rpm_packages`
~~~~~~~~~~~~~~~~~~~~

.. code:: python

    host.fact.rpm_packages


Returns a dict of installed rpm packages:

.. code:: python

    'package_name': ['version'],
    ...



:code:`rpm_package`
~~~~~~~~~~~~~~~~~~~

.. code:: python

    host.fact.rpm_package(name)


Returns information on a .rpm file:

.. code:: python

    {
        'name': 'my_package',
        'version': '1.0.0'
    }


