'''
The iptables modules handles iptables rules
'''

from pyinfra.api import operation
from pyinfra.api.exceptions import OperationError


@operation
def chain(
    state, host, name, present=True,
    table='filter', policy=None, version=4,
):
    '''
    Add/remove/update iptables chains.

    + name: the name of the chain
    + present: whether the chain should exist
    + table: the iptables table this chain should belong to
    + policy: the policy this table should have
    + version: whether to target iptables or ip6tables

    Policy:
        These can only be applied to system chains (FORWARD, INPUT, OUTPUT, etc).
    '''

    chains = (
        host.fact.iptables_chains(table)
        if version == 4
        else host.fact.ip6tables_chains(table)
    )

    command = 'iptables' if version == 4 else 'ip6tables'
    command = '{0} -t {1}'.format(command, table)

    # Doesn't exist but we want it?
    if present and name not in chains:
        yield '{0} -N {1}'.format(command, name)

        if policy:
            yield '{0} -P {1} {2}'.format(command, name, policy)

    # Exists and we don't want it?
    if not present and name in chains:
        yield '{0} -X {1}'.format(command, name)

    # Exists, we want it, but the policies don't match?
    if present and name in chains and policy and chains[name] != policy:
        yield '{0} -P {1} {2}'.format(command, name, policy)


@operation
def rule(
    state, host, chain, jump, present=True,
    table='filter', append=True, version=4,
    # Core iptables filter arguments
    protocol=None, not_protocol=None,
    source=None, not_source=None,
    destination=None, not_destination=None,
    in_interface=None, not_in_interface=None,
    out_interface=None, not_out_interface=None,
    # After-rule arguments
    to_destination=None, to_source=None, to_ports=None, log_prefix=None,
    # Extras and extra shortcuts
    destination_port=None, source_port=None, extras='',
):
    '''
    Add/remove iptables rules.

    + chain: the chain this rule should live in
    + jump: the target of the rule
    + table: the iptables table this rule should belong to
    + append: whether to append or insert the rule (if not present)
    + version: whether to target iptables or ip6tables

    Iptables args:

    + protocol/not_protocol: filter by protocol (tcp or udp)
    + source/not_source: filter by source IPs
    + destination/not_destination: filter by destination IPs
    + in_interface/not_in_interface: filter by incoming interface
    + out_interface/not_out_interface: filter by outgoing interface
    + to_destination: where to route to when jump=DNAT
    + to_source: where to route to when jump=SNAT
    + to_ports: where to route to when jump=REDIRECT
    + log_prefix: prefix for the log of this rule when jump=LOG

    Extras:

    + extras: a place to define iptables extension arguments (eg --limit, --physdev)
    + destination_port: destination port (requires protocol)
    + source_port: source port (requires protocol)

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
    '''

    # These are only shortcuts for extras
    if destination_port:
        extras = '{0} --dport {1}'.format(extras, destination_port)

    if source_port:
        extras = '{0} --sport {1}'.format(extras, source_port)

    # Convert the extras string into a set to enable comparison with the fact
    extras_set = set(extras.split())

    # When protocol is set, the extension is automagically added by iptables (which shows
    # in iptables-save): http://ipset.netfilter.org/iptables-extensions.man.html
    if protocol:
        extras_set.add('-m')
        extras_set.add(protocol)

    # --dport and --sport do not work without a protocol (because they need -m [tcp|udp]
    elif destination_port or source_port:
        raise OperationError(
            'iptables cannot filter by destination_port/source_port without a protocol',
        )

    # Verify NAT arguments, --to-destination only w/table=nat, jump=DNAT
    if to_destination and (table != 'nat' or jump != 'DNAT'):
        raise OperationError(
            'iptables only supports to_destination on the nat table and the DNAT jump '
            '(table={0}, jump={1})'.format(table, jump),
        )

    # As above, --to-source only w/table=nat, jump=SNAT
    if to_source and (table != 'nat' or jump != 'SNAT'):
        raise OperationError(
            'iptables only supports to_source on the nat table and the SNAT jump '
            '(table={0}, jump={1})'.format(table, jump),
        )

    # As above, --to-ports only w/table=nat, jump=REDIRECT
    if to_ports and (table != 'nat' or jump != 'REDIRECT'):
        raise OperationError(
            'iptables only supports to_ports on the nat table and the REDIRECT jump '
            '(table={0}, jump={1})'.format(table, jump),
        )

    # --log-prefix is only supported with jump=LOG
    if log_prefix and jump != 'LOG':
        raise OperationError(
            'iptables only supports log_prefix with the LOG jump '
            '(jump={0})'.format(jump),
        )

    definition = {
        'chain': chain,
        'jump': jump,

        'protocol': protocol,
        'source': source,
        'destination': destination,
        'in_interface': in_interface,
        'out_interface': out_interface,

        'not_protocol': not_protocol,
        'not_source': not_source,
        'not_destination': not_destination,
        'not_in_interface': not_in_interface,
        'not_out_interface': not_out_interface,

        # These go *after* the jump argument
        'log_prefix': log_prefix,
        'to_destination': to_destination,
        'to_source': to_source,
        'to_ports': to_ports,
        'extras': extras_set,
    }

    definition = {
        key: (
            '{0}/32'.format(value)
            if (
                '/' not in value
                and key in ('source', 'not_source', 'destination', 'not_destination')
            )
            else value
        )
        for key, value in definition.items()
        if value
    }

    rules = (
        host.fact.iptables_rules(table)
        if version == 4
        else host.fact.ip6tables_rules(table)
    )

    action = None

    # Definition doesn't exist and we want it
    if present and definition not in rules:
        action = '-A' if append else '-I'

    # Definition exists and we don't want it
    if not present and definition in rules:
        action = '-D'

    # Are we adding/removing a rule? Lets build it
    if action:
        args = [
            'iptables' if version == 4 else 'ip6tables',
            # Add the table
            '-t', table,
            # Add the action and target chain
            action, chain,
        ]

        if protocol:
            args.extend(('-p', protocol))

        if source:
            args.extend(('-s', source))

        if in_interface:
            args.extend(('-i', in_interface))

        if out_interface:
            args.extend(('-o', out_interface))

        if not_protocol:
            args.extend(('!', '-p', not_protocol))

        if not_source:
            args.extend(('!', '-s', not_source))

        if not_in_interface:
            args.extend(('!', '-i', not_in_interface))

        if not_out_interface:
            args.extend(('!', '-o', not_out_interface))

        if extras:
            args.append(extras.strip())

        # Add the jump
        args.extend(('-j', jump))

        if log_prefix:
            args.extend(('--log-prefix', log_prefix))

        if to_destination:
            args.extend(('--to-destination', to_destination))

        if to_source:
            args.extend(('--to-source', to_source))

        if to_ports:
            args.extend(('--to-ports', to_ports))

        # Build the final iptables command
        yield ' '.join(args)
