Hardware
--------

:code:`block_devices`
~~~~~~~~~~~~~~~~~~~~~

.. code:: python

    host.fact.block_devices


Returns a dict of (mounted) block devices:

.. code:: python

    '/dev/sda1': {
        'available': '39489508',
        'used_percent': '3',
        'mount': '/',
        'used': '836392',
        'blocks': '40325900'
    },
    ...



:code:`cpus`
~~~~~~~~~~~~

.. code:: python

    host.fact.cpus


Returns the number of CPUs on this server.



:code:`memory`
~~~~~~~~~~~~~~

.. code:: python

    host.fact.memory


Returns the memory installed in this server, in MB.



:code:`network_devices`
~~~~~~~~~~~~~~~~~~~~~~~

.. code:: python

    host.fact.network_devices


Gets & returns a dict of network devices:

.. code:: python

    'eth0': {
        'ipv4': {
            'address': '127.0.0.1',
            'netmask': '255.255.255.255',
            'broadcast': '127.0.0.13'
        },
        'ipv6': {
            'size': '64',
            'address': 'fe80::a00:27ff:fec3:36f0'
        }
    },
    ...


