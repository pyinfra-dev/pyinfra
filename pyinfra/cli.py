# pyinfra
# File: pyinfra/cli.py
# Desc: pyinfra CLI helpers

from os import path
from imp import load_source
from fnmatch import fnmatch
from datetime import datetime
from types import FunctionType

from termcolor import colored

from pyinfra import state, logger
from pyinfra.api import Config, Inventory
from pyinfra.api.exceptions import PyinfraException


class CliException(PyinfraException):
    pass


def make_inventory(
    inventory_filename, limit=None,
    ssh_user=None, ssh_key=None, ssh_key_password=None, ssh_port=None
):
    '''Builds a pyinfra.api.Inventory from the filesystem (normally!).'''
    if ssh_port is not None:
        ssh_port = int(ssh_port)

    file_groupname = None

    try:
        module = load_source('', inventory_filename)

        groups = {
            attr: getattr(module, attr)
            for attr in dir(module)
            if attr.isupper()
        }

        # Used to set all the hosts to an additional group - that of the filename
        # ie inventories/dev.py means all the hosts are in the dev group, if not present
        file_groupname = path.basename(inventory_filename).split('.')[0].upper()

    except IOError:
        # If a /, definitely not a hostname
        if '/' in inventory_filename:
            raise CliException('Invalid inventory file: {0}'.format(inventory_filename))

        # Otherwise we assume the inventory file is a single hostname
        groups = {
            'ALL': [inventory_filename]
        }

    if 'ALL' in groups:
        all_hosts = groups.pop('ALL')

    # Build ALL out of the existing hosts if not defined
    else:
        all_hosts = []
        for hosts in groups.values():
            for host in hosts:
                hostname = host[0] if isinstance(host, tuple) else host

                if hostname not in all_hosts:
                    all_hosts.append(host)

    # Apply any limit to all_hosts
    if limit:
        all_hosts = [
            host for host in all_hosts
            if (isinstance(host, tuple) and fnmatch(host[0], limit))
            or (isinstance(host, basestring) and fnmatch(host, limit))
        ]

    groups['ALL'] = all_hosts

    # Apply the filename group if not already defined
    if file_groupname and file_groupname not in groups:
        groups[file_groupname] = all_hosts

    # For each group load up any data
    for name, hosts in groups.iteritems():
        data = {}
        data_filename = path.join(
            state.deploy_dir, 'group_data', '{0}.py'.format(name.lower())
        )

        if path.exists(data_filename):
            module = load_source('', data_filename)
            data = {
                attr: getattr(module, attr)
                for attr in dir(module)
                if attr.islower() and not attr.startswith('_')
            }

        # Attach to group object
        groups[name] = (hosts, data)

    return Inventory(
        groups.pop('ALL'),
        ssh_user=ssh_user,
        ssh_key=ssh_key,
        ssh_key_password=ssh_key_password,
        ssh_port=ssh_port,
        **groups
    )


def load_config():
    '''Loads any local config.py file.'''
    config = Config()

    if path.exists('config.py'):
        module = load_source('', 'config.py')

        for attr in dir(module):
            if attr.isupper():
                setattr(config, attr, getattr(module, attr))

    return config


def json_encode(obj):
    if isinstance(obj, FunctionType):
        return obj.__name__

    elif isinstance(obj, datetime):
        return obj.isoformat()

    elif isinstance(obj, file):
        return str(obj.name)

    else:
        raise TypeError('Cannot serialize: {0}'.format(obj))


def print_meta():
    for hostname, meta in state.meta.iteritems():
        logger.info(
            '{0}\tOperations: {1}\t    Commands: {2}'.format(
                hostname, meta['ops'], meta['commands']
            )
        )


def print_results():
    for hostname, results in state.results.iteritems():
        if hostname not in state.inventory.connected_hosts:
            logger.info('{0}\tNo connection'.format(colored(hostname, 'red', attrs=['bold'])))

        else:
            meta = state.meta[hostname]
            success_ops = results['success_ops']
            error_ops = results['error_ops']

            # If all ops got complete (even with ignored_errors)
            if results['ops'] == meta['ops']:
                # Yellow if ignored any errors, else green
                color = 'green' if error_ops == 0 else 'yellow'
                host_string = colored(hostname, color)

            # Ops did not complete!
            else:
                host_string = colored(hostname, 'red', attrs=['bold'])

            logger.info('{0}\tSuccessful: {1}\t    Errors: {2}\t    Commands: {3}/{4}'.format(
                host_string,
                colored(success_ops, attrs=['bold']),
                error_ops if error_ops == 0 else colored(error_ops, 'red', attrs=['bold']),
                results['commands'], meta['commands']
            ))
