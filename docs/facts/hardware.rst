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



:code:`ipv4_addresses`
~~~~~~~~~~~~~~~~~~~~~~

.. code:: python

    host.fact.ipv4_addresses


Gets & returns a dictionary of network interface -> IPv4 address.

.. code:: python

    'eth0': '127.0.0.1',
    ...



:code:`ipv6_addresses`
~~~~~~~~~~~~~~~~~~~~~~

.. code:: python

    host.fact.ipv6_addresses


Gets & returns a dictionary of network interface -> IPv6 address.

.. code:: python

    'eth0': 'fe80::a00:27ff::2',
    ...



:code:`memory`
~~~~~~~~~~~~~~

.. code:: python

    host.fact.memory


Returns the memory installed in this server, in MB.



:code:`network_devices`
~~~~~~~~~~~~~~~~~~~~~~~

.. code:: python

    host.fact.network_devices


Gets & returns a dict of network devices. See the ``ipv4_addresses`` and
``ipv6_addresses`` facts for easier-to-use shortcuts to get device addresses.

.. code:: python

    'eth0': {
        'ipv4': {
            'address': '127.0.0.1',
            'broadcast': '127.0.0.13',
            # Only one of these will exist:
            'netmask': '255.255.255.255',
            'mask_bits': '32'
        },
        'ipv6': {
            'address': 'fe80::a00:27ff:fec3:36f0',
            'mask_bits': '64'
        }
    },
    ...


