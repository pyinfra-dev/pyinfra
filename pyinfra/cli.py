# pyinfra
# File: pyinfra/cli.py
# Desc: pyinfra CLI helpers

import json
from os import path
from imp import load_source
from fnmatch import fnmatch
from datetime import datetime
from types import FunctionType
from importlib import import_module

from termcolor import colored

from pyinfra import logger

from pyinfra.api import Config, Inventory
from pyinfra.api.facts import facts
from pyinfra.api.exceptions import PyinfraException

from .hook import HOOKS, HOOK_NAMES


class CliException(PyinfraException):
    pass


class FakeData(object):
    def __getattr__(self, key):
        return None

    def __iter__(self):
        yield None

    def __call__(self, *args, **kwargs):
        return self

class FakeHost(object):
    @property
    def data(self):
        return FakeData()

    @property
    def host_data(self):
        return FakeData()

    def __getattr__(self, key):
        return FakeData()


def print_facts_list():
    print json.dumps(facts.keys(), indent=4)


def print_fact(fact_data):
    print json.dumps(fact_data, indent=4, default=json_encode)


def dump_state(state):
    print
    logger.info('Proposed operations:')
    print json.dumps(state.ops, indent=4, default=json_encode)
    print
    logger.info('Operation meta:')
    print json.dumps(state.op_meta, indent=4, default=json_encode)
    print
    logger.info('Operation order:')
    print json.dumps(state.op_order, indent=4, default=json_encode)


def run_hook(state, hook_name, hook_data):
    hooks = HOOKS[hook_name]

    if hooks:
        for hook in hooks:
            logger.info('Running hook: {0}/{1}'.format(
                hook_name,
                colored(hook.__name__, attrs=['bold'])
            ))
            hook(hook_data, state)

        print


def json_encode(obj):
    if isinstance(obj, FunctionType):
        return obj.__name__

    elif isinstance(obj, datetime):
        return obj.isoformat()

    elif isinstance(obj, file):
        return str(obj.name)

    else:
        raise TypeError('Cannot serialize: {0}'.format(obj))


def print_meta(state):
    for hostname, meta in state.meta.iteritems():
        logger.info(
            '{0}\tOperations: {1}\t    Commands: {2}'.format(
                hostname, meta['ops'], meta['commands']
            )
        )


def print_results(state):
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


def setup_arguments(arguments):
    # Prep --run OP ARGS
    op, args = arguments['--run'], arguments['ARGS']

    # Replace op name with the module
    if op:
        op_module, op_name = op.split('.')
        op_module = import_module('pyinfra.modules.{0}'.format(op_module))

        op_func = getattr(op_module, op_name, None)
        if not op_func:
            raise PyinfraException('No such operation: {0}'.format(op))

        arguments['--run'] = op_func

    # Replace the args string with kwargs
    if args:
        args = args.split(',')

        # Setup kwargs
        kwargs = [arg.split('=') for arg in args if '=' in arg]
        op_kwargs = {
            key: value
            for key, value in kwargs
        }

        # Get the remaining args
        args = [arg for arg in args if '=' not in arg]

        arguments['ARGS'] = (args, op_kwargs)

    # Setup the rest
    return {
        # Deploy options
        'inventory': arguments['-i'],
        'deploy': arguments['DEPLOY'],
        'verbose': arguments['-v'],
        'dry': arguments['--dry'],
        'serial': arguments['--serial'],
        'nowait': arguments['--nowait'],
        'debug': arguments['--debug'],
        'fact': arguments['--fact'],
        'limit': arguments['--limit'],
        'op': arguments['--run'],
        'op_args': arguments['ARGS'],

        # Config options
        'user': arguments['--user'],
        'key': arguments['--key'],
        'key_password': arguments['--key-password'],
        'password': arguments['--password'],
        'port': arguments['--port'],
        'sudo': arguments['--sudo'],
        'sudo_user': arguments['--sudo-user'],

        # Misc
        'list_facts': arguments['--facts']
    }


def load_config(deploy_dir):
    '''Loads any local config.py file.'''
    config = Config()
    config_filename = path.join(deploy_dir, 'config.py')

    if path.exists(config_filename):
        module = load_source('', config_filename)

        for attr in dir(module):
            if hasattr(config, attr) or attr in HOOK_NAMES:
                setattr(config, attr, getattr(module, attr))

    return config


def load_deploy_config(deploy_filename, config):
    '''Loads any local config overrides in the deploy file.'''

    if not deploy_filename:
        return

    if path.exists(deploy_filename):
        module = load_source('', deploy_filename)

        for attr in dir(module):
            if hasattr(config, attr) or attr in HOOK_NAMES:
                setattr(config, attr, getattr(module, attr))

    return config


def make_inventory(
    inventory_filename, deploy_dir=None, limit=None,
    ssh_user=None, ssh_key=None, ssh_key_password=None, ssh_port=None, ssh_password=None
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
            # Groups can be a list of hosts or tuple of (hosts, data)
            hosts = hosts[0] if isinstance(hosts, tuple) else hosts

            for host in hosts:
                # Hosts can be a hostname or tuple of (hostname, data)
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

        if isinstance(hosts, tuple):
            hosts, data = hosts

        data_filename = path.join(
            deploy_dir, 'group_data', '{0}.py'.format(name.lower())
        )

        if path.exists(data_filename):
            module = load_source('', data_filename)
            data.update({
                attr: getattr(module, attr)
                for attr in dir(module)
                if attr.islower() and not attr.startswith('_')
            })

        # Attach to group object
        groups[name] = (hosts, data)

    return Inventory(
        groups.pop('ALL'),
        ssh_user=ssh_user,
        ssh_key=ssh_key,
        ssh_key_password=ssh_key_password,
        ssh_port=ssh_port,
        ssh_password=ssh_password,
        **groups
    ), file_groupname and file_groupname.lower()
