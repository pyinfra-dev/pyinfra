Iptables
--------


The iptables modules handles iptables rules

:code:`iptables.chain`
~~~~~~~~~~~~~~~~~~~~~~

Manage iptables chains.

.. code:: python

    iptables.chain(name, present=True, table='filter', policy=None, version=4)

+ **name**: the name of the chain
+ **present**: whether the chain should exist
+ **table**: the iptables table this chain should belong to
+ **policy**: the policy this table should have
+ **version**: whether to target iptables or ip6tables

Policy:
    These can only be applied to system chains (FORWARD, INPUT, OUTPUT, etc).


:code:`iptables.rule`
~~~~~~~~~~~~~~~~~~~~~

Manage iptables rules.

.. code:: python

    iptables.rule(
        chain, jump, present=True, table='filter', append=True, version=4, protocol=None,
        not_protocol=None, source=None, not_source=None, destination=None, not_destination=None,
        in_interface=None, not_in_interface=None, out_interface=None, not_out_interface=None,
        to_destination=None, to_source=None, to_ports=None, log_prefix=None,
        destination_port=None, source_port=None, extras=''
    )

+ **chain**: the chain this rule should live in
+ **jump**: the target of the rule
+ **table**: the iptables table this rule should belong to
+ **append**: whether to append or insert the rule (if not present)
+ **version**: whether to target iptables or ip6tables

Iptables args:

+ **protocol/not_protocol**: filter by protocol (tcp or udp)
+ **source/not_source**: filter by source IPs
+ **destination/not_destination**: filter by destination IPs
+ **in_interface/not_in_interface**: filter by incoming interface
+ **out_interface/not_out_interface**: filter by outgoing interface
+ **to_destination**: where to route to when jump=DNAT
+ **to_source**: where to route to when jump=SNAT
+ **to_ports**: where to route to when jump=REDIRECT
+ **log_prefix**: prefix for the log of this rule when jump=LOG

Extras:

+ **extras**: a place to define iptables extension arguments (eg --limit, --physdev)
+ **destination_port**: destination port (requires protocol)
+ **source_port**: source port (requires protocol)

Examples:

.. code:: python

    # Block SSH traffic

    iptables.rule(
        'INPUT', 'DROP',
        destination_port=22
    )


    # NAT traffic on from 8.8.8.8:53 to 8.8.4.4:8080

    iptables.rule(
        'PREROUTING', 'DNAT', table='nat',
        source='8.8.8.8', destination_port=53,
        to_destination='8.8.4.4:8080'
    )

