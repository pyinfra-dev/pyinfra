Vzctl
-----

:code:`openvz_containers`
~~~~~~~~~~~~~~~~~~~~~~~~~

.. code:: python

    host.fact.openvz_containers


Returns a dict of running OpenVZ containers by CTID:

.. code:: python

    {
        666: {
            'ip': [],
            'ostemplate': 'ubuntu...',
            ...
        },
        ...
    }


