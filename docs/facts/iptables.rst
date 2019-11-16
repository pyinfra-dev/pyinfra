Iptables
--------

:code:`ip6tables_chains`
~~~~~~~~~~~~~~~~~~~~~~~~

.. code:: python

    host.fact.ip6tables_chains(table='filter')


Returns a dict of ip6tables chains & policies:

.. code:: python

    'NAME': 'POLICY',
    ...



:code:`ip6tables_rules`
~~~~~~~~~~~~~~~~~~~~~~~

.. code:: python

    host.fact.ip6tables_rules(table='filter')


Returns a list of ip6tables rules for a specific table:

.. code:: python

    {
        'chain': 'PREROUTING',
        'jump': 'DNAT'
    },
    ...



:code:`iptables_chains`
~~~~~~~~~~~~~~~~~~~~~~~

.. code:: python

    host.fact.iptables_chains(table='filter')


Returns a dict of iptables chains & policies:

.. code:: python

    'NAME': 'POLICY',
    ...



:code:`iptables_rules`
~~~~~~~~~~~~~~~~~~~~~~

.. code:: python

    host.fact.iptables_rules(table='filter')


Returns a list of iptables rules for a specific table:

.. code:: python

    {
        'chain': 'PREROUTING',
        'jump': 'DNAT'
    },
    ...


