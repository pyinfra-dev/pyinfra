# pyinfra
# File: pyinfra/cli.py
# Desc: pyinfra CLI helpers

from __future__ import division, unicode_literals, print_function

import sys
import json
import shlex
import logging
import traceback
from os import path
from imp import load_source
from fnmatch import fnmatch
from datetime import datetime
from types import FunctionType
from importlib import import_module

# py2/3 switcheroo
try:
    from cStringIO import OutputType, InputType
    io_bases = (OutputType, InputType)
except ImportError:
    from io import IOBase
    io_bases = IOBase

import six
from termcolor import colored

from pyinfra import logger, pseudo_inventory
from pyinfra.pseudo_modules import PseudoModule

from pyinfra.api import Config, Inventory
from pyinfra.api.facts import get_fact_names, is_fact
from pyinfra.api.exceptions import PyinfraError
from pyinfra.api.util import import_locals

from .hook import HOOKS, HOOK_NAMES

STDOUT_LOG_LEVELS = (logging.DEBUG, logging.INFO)
STDERR_LOG_LEVELS = (logging.WARNING, logging.ERROR, logging.CRITICAL)


class CliError(PyinfraError):
    pass


class FakeData(object):
    def __getattr__(self, key):
        return FakeData()

    def __getitem__(self, key):
        return FakeData()

    def __iter__(self):
        yield FakeData()

    def __call__(self, *args, **kwargs):
        return self

    def __str__(self):
        return ''


class FakeHost(object):
    @property
    def data(self):
        return FakeData()

    @property
    def host_data(self):
        return FakeData()

    @property
    def fact(self):
        return FakeData()

    def __getattr__(self, key):
        return FakeData()


class LogFilter(logging.Filter):
    def __init__(self, *levels):
        self.levels = levels

    def filter(self, record):
        return record.levelno in self.levels


class LogFormatter(logging.Formatter):
    level_to_format = {
        logging.DEBUG: lambda s: colored(s, 'green'),
        logging.WARNING: lambda s: colored(s, 'yellow'),
        logging.ERROR: lambda s: colored(s, 'red'),
        logging.CRITICAL: lambda s: colored(s, 'red', attrs=['bold'])
    }

    def format(self, record):
        message = record.msg

        # We only handle strings here
        if isinstance(message, six.string_types):
            # Horrible string matching hack
            if message.find('Starting operation') > 0:
                message = '--> {0}'.format(message)
            else:
                message = '    {0}'.format(message)

            if record.levelno in self.level_to_format:
                message = self.level_to_format[record.levelno](message)

            return message

        # If not a string, pass to standard Formatter
        else:
            return super(LogFormatter, self).format(record)


def setup_logging(log_level):
    # Set the log level
    logger.setLevel(log_level)

    # Setup a new handler for stdout & stderr
    stdout_handler = logging.StreamHandler(sys.stdout)
    stderr_handler = logging.StreamHandler(sys.stderr)

    # Setup filters to push different levels to different streams
    stdout_filter = LogFilter(*STDOUT_LOG_LEVELS)
    stdout_handler.addFilter(stdout_filter)

    stderr_filter = LogFilter(*STDERR_LOG_LEVELS)
    stderr_handler.addFilter(stderr_filter)

    # Setup a formatter
    formatter = LogFormatter()
    stdout_handler.setFormatter(formatter)
    stderr_handler.setFormatter(formatter)

    # Add the handlers
    logger.addHandler(stdout_handler)
    logger.addHandler(stderr_handler)


def print_facts_list():
    print(json.dumps(list(get_fact_names()), indent=4, default=json_encode))


def print_fact(fact_data):
    print(json.dumps(fact_data, indent=4, default=json_encode))


def dump_trace(exc_info):
    # Dev mode, so lets dump as much data as we have
    error_type, value, trace = exc_info
    print('----------------------')
    traceback.print_tb(trace)
    logger.critical('{0}: {1}'.format(error_type.__name__, value))
    print('----------------------')


def dump_state(state):
    print()
    print('--> Proposed operations:')
    print(json.dumps(state.ops, indent=4, default=json_encode))
    print()
    print('--> Operation meta:')
    print(json.dumps(state.op_meta, indent=4, default=json_encode))
    print()
    print('--> Operation order:')
    print(json.dumps(state.op_order, indent=4, default=json_encode))


def run_hook(state, hook_name, hook_data):
    hooks = HOOKS[hook_name]

    if hooks:
        for hook in hooks:
            print('--> Running hook: {0}/{1}'.format(
                hook_name,
                colored(hook.__name__, attrs=['bold'])
            ))
            hook(hook_data, state)

        print()


def json_encode(obj):
    if isinstance(obj, FunctionType):
        return obj.__name__

    elif isinstance(obj, datetime):
        return obj.isoformat()

    elif isinstance(obj, file):
        return str(obj.name)

    elif isinstance(obj, io_bases):
        return 'In-memory file: {0}'.format(obj.read())

    else:
        raise TypeError('Cannot serialize: {0}'.format(obj))


def print_meta(state):
    for hostname, meta in six.iteritems(state.meta):
        logger.info(
            '[{0}]\tOperations: {1}\t    Commands: {2}'.format(
                colored(hostname, attrs=['bold']),
                meta['ops'], meta['commands']
            )
        )


def print_data(inventory):
    for host in inventory:
        print('[{0}]'.format(colored(host.name, attrs=['bold'])))
        print(json.dumps(host.data.dict(), indent=4, default=json_encode))
        print()


def print_results(state):
    for hostname, results in six.iteritems(state.results):
        if hostname not in state.inventory.connected_hosts:
            logger.info('[{0}]\tNo connection'.format(colored(hostname, 'red', attrs=['bold'])))

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

            logger.info('[{0}]\tSuccessful: {1}\t    Errors: {2}\t    Commands: {3}/{4}'.format(
                host_string,
                colored(success_ops, attrs=['bold']),
                error_ops if error_ops == 0 else colored(error_ops, 'red', attrs=['bold']),
                results['commands'], meta['commands']
            ))


def _parse_arg(arg):
    if arg == 'False':
        return False

    if arg == 'True':
        return True

    return arg


def parse_argstring(argstring):
    '''
    Preparses CLI input:

    ``arg1,arg2`` => ``['arg1', 'arg2']``
    ``[item1, item2],arg2`` => ``[['item1', 'item2'], arg2]``
    '''

    argstring = argstring.replace(',', ' , ')
    argstring = argstring.replace('[', ' [ ')
    argstring = argstring.replace(']', ' ] ')

    argbits = shlex.split(argstring)
    args = []
    arg_buff = []
    list_buff = []
    in_list = False

    for bit in argbits:
        if bit == '[' and not in_list:
            in_list = True
            continue

        elif bit == ']' and in_list:
            in_list = False
            args.append(list_buff)
            list_buff = []
            continue

        elif bit == ',':
            if not in_list and arg_buff:
                args.append(' '.join(arg_buff))
                arg_buff = []

            continue

        if in_list:
            list_buff.append(bit)
        else:
            arg_buff.append(bit)

    if arg_buff:
        args.append(' '.join(arg_buff))

    return args


def setup_arguments(arguments):
    '''
    Prepares argumnents output by docopt.
    '''

    # Prep --run OP ARGS
    op, args = arguments['--run'], arguments['ARGS']

    # Replace op name with the module
    if op:
        op_module, op_name = op.split('.')
        op_module = import_module('pyinfra.modules.{0}'.format(op_module))

        op_func = getattr(op_module, op_name, None)
        if not op_func:
            raise CliError('No such operation: {0}'.format(op))

        arguments['--run'] = op_func

    # Replace the args string with kwargs
    if args:
        args = parse_argstring(args)

        # Setup kwargs
        kwargs = [arg.split('=') for arg in args if '=' in arg]
        op_kwargs = {
            key: _parse_arg(value)
            for key, value in kwargs
        }

        # Get the remaining args
        args = [_parse_arg(arg) for arg in args if '=' not in arg]

        arguments['ARGS'] = (args, op_kwargs)

    # Ensure parallel is a number
    if arguments['--parallel']:
        arguments['--parallel'] = int(arguments['--parallel'])

    # Always assign empty args
    fact_args = {}
    if arguments['--fact']:
        if ':' in arguments['--fact']:
            fact, fact_args = arguments['--fact'].split(':')
            fact_args = fact_args.split(',')
            arguments['--fact'] = fact

        # Ensure the fact exists
        if not is_fact(arguments['--fact']):
            raise CliError('Invalid fact: {0}'.format(arguments['--fact']))

    # Check deploy file exists
    if arguments['DEPLOY']:
        try:
            open(arguments['DEPLOY']).close()
        except IOError as e:
            raise CliError('{0}: {1}'.format(e.strerror, arguments['DEPLOY']))

    # Setup the rest
    return {
        # Deploy options
        'inventory': arguments['-i'],
        'deploy': arguments['DEPLOY'],
        'verbose': arguments['-v'],
        'dry': arguments['--dry'],
        'serial': arguments['--serial'],
        'no_wait': arguments['--no-wait'],
        'debug': arguments['--debug'],

        'debug_data': arguments['--debug-data'],

        'fact': arguments['--fact'],
        'fact_args': fact_args,

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
        'parallel': arguments['--parallel'],

        # Misc
        'list_facts': arguments['--facts'],

        # Experimental
        'pipelining': arguments['--enable-pipelining']
    }


def load_config(deploy_dir):
    '''
    Loads any local config.py file.
    '''

    config = Config()
    config_filename = path.join(deploy_dir, 'config.py')

    if path.exists(config_filename):
        module = load_source('', config_filename)

        for attr in dir(module):
            if hasattr(config, attr) or attr in HOOK_NAMES:
                setattr(config, attr, getattr(module, attr))

    return config


def load_deploy_config(deploy_filename, config):
    '''
    Loads any local config overrides in the deploy file.
    '''

    if not deploy_filename:
        return

    if path.exists(deploy_filename):
        module = load_source('', deploy_filename)

        for attr in dir(module):
            if hasattr(config, attr):
                setattr(config, attr, getattr(module, attr))

    return config


def make_inventory(
    inventory_filename, deploy_dir=None, limit=None,
    ssh_user=None, ssh_key=None, ssh_key_password=None, ssh_port=None, ssh_password=None
):
    '''
    Builds a ``pyinfra.api.Inventory`` from the filesystem. If the file does not exist
    and doesn't contain a / attempts to use that as the only hostname.
    '''

    if ssh_port is not None:
        ssh_port = int(ssh_port)

    file_groupname = None

    try:
        attrs = import_locals(inventory_filename)

        groups = {
            key: value
            for key, value in six.iteritems(attrs)
            if key.isupper()
        }

        # Used to set all the hosts to an additional group - that of the filename
        # ie inventories/dev.py means all the hosts are in the dev group, if not present
        file_groupname = path.basename(inventory_filename).split('.')[0].upper()

    except IOError as e:
        # If a /, definitely not a hostname
        if '/' in inventory_filename:
            raise CliError('{0}: {1}'.format(e.strerror, inventory_filename))

        # Otherwise we assume the inventory file is a single hostname
        groups = {
            'ALL': [inventory_filename]
        }

    all_data = {}

    if 'ALL' in groups:
        all_hosts = groups.pop('ALL')

        if isinstance(all_hosts, tuple):
            all_hosts, all_data = all_hosts

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
                    all_hosts.append(hostname)

    groups['ALL'] = (all_hosts, all_data)

    # Apply the filename group if not already defined
    if file_groupname and file_groupname not in groups:
        groups[file_groupname] = all_hosts

    # In pyinfra an inventory is a combination of (hostnames + data). However, in CLI
    # mode we want to be define this in separate files (inventory / group data). The
    # issue is we want inventory access within the group data files - but at this point
    # we're not ready to make an Inventory. So here we just create a fake one, and attach
    # it to pseudo_inventory while we import the data files.
    fake_groups = {
        # In API mode groups *must* be tuples of (hostnames, data)
        name: group if isinstance(group, tuple) else (group, {})
        for name, group in six.iteritems(groups)
    }
    fake_inventory = Inventory((all_hosts, all_data), **fake_groups)
    pseudo_inventory.set(fake_inventory)

    # For each group load up any data
    for name, hosts in six.iteritems(groups):
        data = {}

        if isinstance(hosts, tuple):
            hosts, data = hosts

        data_filename = path.join(
            deploy_dir, 'group_data', '{0}.py'.format(name.lower())
        )
        logger.debug('Looking for group data: {0}'.format(data_filename))

        if path.exists(data_filename):
            # Read the files locals into a dict
            file_data = import_locals(data_filename)

            # Strip out any pseudo module imports and _prefixed variables
            data.update({
                key: value
                for key, value in six.iteritems(file_data)
                if not isinstance(value, PseudoModule)
                and not key.startswith('_')
                and key.islower()
            })

        # Attach to group object
        groups[name] = (hosts, data)

    # Reset the pseudo inventory
    pseudo_inventory.reset()

    # Apply any limit to all_hosts
    if limit:
        # Limits can be groups
        limit_groupname = limit.upper()
        if limit_groupname in groups:
            all_hosts = [
                host[0] if isinstance(host, tuple) else host
                for host in groups[limit_groupname]
            ]

        # Or hostnames w/*wildcards
        else:
            all_hosts = [
                host for host in all_hosts
                if (isinstance(host, tuple) and fnmatch(host[0], limit))
                or (isinstance(host, six.string_types) and fnmatch(host, limit))

            ]

        # Reassign the ALL group w/limit
        groups['ALL'] = (all_hosts, all_data)

    return Inventory(
        groups.pop('ALL'),
        ssh_user=ssh_user,
        ssh_key=ssh_key,
        ssh_key_password=ssh_key_password,
        ssh_port=ssh_port,
        ssh_password=ssh_password,
        **groups
    ), file_groupname and file_groupname.lower()
