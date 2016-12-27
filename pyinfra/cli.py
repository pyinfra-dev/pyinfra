# pyinfra
# File: pyinfra/cli.py
# Desc: pyinfra CLI helpers

from __future__ import division, unicode_literals, print_function

import re
import sys
import json
import shlex
import logging
import traceback

from os import path
from fnmatch import fnmatch
from datetime import datetime
from types import FunctionType, GeneratorType
from importlib import import_module

# py2/3 switcheroo
try:
    from StringIO import StringIO
    from cStringIO import OutputType, InputType
    io_bases = (file, OutputType, InputType, StringIO)

except ImportError:
    from io import IOBase
    io_bases = IOBase

import six

from termcolor import colored

from pyinfra import logger, pseudo_inventory
from pyinfra.api import Config, Inventory
from pyinfra.api.facts import get_fact_names, is_fact
from pyinfra.api.exceptions import PyinfraError
from pyinfra.api.util import exec_file

from .hook import HOOKS

STDOUT_LOG_LEVELS = (logging.DEBUG, logging.INFO)
STDERR_LOG_LEVELS = (logging.WARNING, logging.ERROR, logging.CRITICAL)

# Hosts in an inventory can be just the hostname or a tuple (hostname, data)
ALLOWED_HOST_TYPES = tuple(
    list(six.string_types) + [tuple]
)

# Group data can be any "core" Python type
ALLOWED_DATA_TYPES = tuple(
    list(six.string_types) + list(six.integer_types)
    + [bool, dict, list, set, tuple, float, complex]
)


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
        return FakeData()

    def __str__(self):
        return 'FakeData'

    def __add__(self, other):
        return FakeData()

    def __len__(self):
        return 0

    def iteritems(self):
        return iter([(FakeData(), FakeData())])


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


class FakeState(object):
    active = False
    deploy_dir = ''

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
            if re.match(r'.*Starting[ a-zA-Z,]*operation.*', message):
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
    print('--> Gathered facts:')
    print(json.dumps(state.facts, indent=4, default=json_encode))
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

    elif isinstance(obj, io_bases):
        if hasattr(obj, 'name'):
            return 'File: {0}'.format(obj.name)

        elif hasattr(obj, 'template'):
            return 'Template: {0}'.format(obj.template)

        obj.seek(0)
        return 'In-memory file: {0}'.format(obj.read())

    elif isinstance(obj, set):
        return list(obj)

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
        if hostname not in state.connected_hosts:
            logger.info('[{0}]\tNo connection'.format(
                colored(hostname, 'red', attrs=['bold'])
            ))

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
                error_ops
                if error_ops == 0
                else colored(error_ops, 'red', attrs=['bold']),
                results['commands'], meta['commands']
            ))


def _parse_arg(arg):
    if arg.lower() == 'false':
        return False

    if arg.lower() == 'true':
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
                args.append(''.join(arg_buff))
                arg_buff = []

            continue

        # Restore any broken up ,[]s
        bit = bit.replace(' , ', ',')
        bit = bit.replace(' [ ', '[')
        bit = bit.replace(' ] ', ']')

        if in_list:
            list_buff.append(bit)
        else:
            arg_buff.append(bit)

    if arg_buff:
        args.append(' '.join(arg_buff))

    return args


def setup_op_and_args(op_string, args_string):
    op_bits = op_string.split('.')

    # If the op isn't <module>.<operation>
    if (
        len(op_bits) != 2
        # Modules/operations can only be lowercase alphabet
        or any(
            not bit.isalpha() or not bit.islower()
            for bit in op_bits
        )
    ):
        # Either default to server.shell w/op as command if no args are passed
        if not args_string:
            args_string = op_string
            op_bits = ['server', 'shell']

        # Or fail as it's an invalid op
        else:
            raise CliError('Invalid operation: {0}'.format(op_string))

    # Get the module & operation name
    op_module, op_name = op_bits

    try:
        op_module = import_module('pyinfra.modules.{0}'.format(op_module))
    except ImportError:
        raise CliError('No such module: {0}'.format(op_module))

    op = getattr(op_module, op_name, None)
    if not op:
        raise CliError('No such operation: {0}'.format(op_string))

    # Replace the args string with kwargs
    args = None

    if args_string:
        args = parse_argstring(args_string)

        # Setup kwargs
        kwargs = [arg.split('=') for arg in args if '=' in arg]
        op_kwargs = {
            key: _parse_arg(value)
            for key, value in kwargs
        }

        # Get the remaining args
        args = [_parse_arg(arg) for arg in args if '=' not in arg]

        args = (args, op_kwargs)

    return op, args


def setup_arguments(arguments):
    '''
    Prepares argumnents output by docopt.
    '''

    # Ensure parallel/port are numbers
    for key in ('--parallel', '--port', '--fail-percent'):
        if arguments[key]:
            try:
                arguments[key] = int(arguments[key])
            except ValueError:
                raise CliError('{0} is not a valid integer for {1}'.format(
                    arguments[key], key
                ))

    # Prep --run OP ARGS
    if arguments['--run']:
        op, args = setup_op_and_args(arguments['--run'], arguments['ARGS'])
    else:
        op = args = None

    # Always assign empty args
    fact_args = []
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
        if not path.exists(arguments['DEPLOY']):
            raise CliError('Deploy file not found: {0}'.format(arguments['DEPLOY']))

    # Check our key file exists
    if arguments['--key']:
        if not path.exists(arguments['--key']):
            raise CliError('Private key file not found: {0}'.format(arguments['--key']))

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
        'debug_state': arguments['--debug-state'],

        'fact': arguments['--fact'],
        'fact_args': fact_args,

        'limit': arguments['--limit'],
        'op': op,
        'op_args': args,

        # Config options
        'user': arguments['--user'],
        'key': arguments['--key'],
        'key_password': arguments['--key-password'],
        'password': arguments['--password'],
        'port': arguments['--port'],
        'sudo': arguments['--sudo'],
        'sudo_user': arguments['--sudo-user'],
        'su_user': arguments['--su-user'],
        'parallel': arguments['--parallel'],
        'fail_percent': arguments['--fail-percent'],

        # Misc
        'list_facts': arguments['--facts'],

        # Experimental
        'pipelining': arguments['--enable-pipelining'],
    }


def load_config(deploy_dir):
    '''
    Loads any local config.py file.
    '''

    config = Config()
    config_filename = path.join(deploy_dir, 'config.py')

    if path.exists(config_filename):
        attrs = exec_file(config_filename, return_locals=True)

        for key, value in six.iteritems(attrs):
            if hasattr(config, key):
                setattr(config, key, value)

    return config


def load_deploy_config(deploy_filename, config):
    '''
    Loads any local config overrides in the deploy file.
    '''

    if not deploy_filename:
        return

    if path.exists(deploy_filename):
        attrs = exec_file(deploy_filename, return_locals=True)

        for key, value in six.iteritems(attrs):
            if hasattr(config, key):
                setattr(config, key, value)

    return config


def is_inventory_group(key, value):
    '''
    Verify that a module-level variable (key = value) is a valid inventory group.
    '''

    if (
        key.startswith('_')
        or not isinstance(value, (list, tuple, GeneratorType))
    ):
        return False

    # If the group is a tuple of (hosts, data), check the hosts
    if isinstance(value, tuple):
        value = value[0]

    # Expand any generators of hosts
    if isinstance(value, GeneratorType):
        value = list(value)

    return all(
        isinstance(item, ALLOWED_HOST_TYPES)
        for item in value
    )


def is_group_data(key, value):
    '''
    Verify that a module-level variable (key = value) is a valid bit of group data.
    '''

    return (
        isinstance(value, ALLOWED_DATA_TYPES)
        and not key.startswith('_')
    )


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
        attrs = exec_file(inventory_filename, return_locals=True)

        groups = {
            key: value
            for key, value in six.iteritems(attrs)
            if is_inventory_group(key, value)
        }

        # TODO: remove at some point
        # COMPAT: 0.2 switched to supporting lowercase group names, instead of
        # all uppercase - but old deploys may have uppercase names and lowercase
        # vars (now should be wrapped in a function). So here we check for mixed
        # case group names, and default to upper if so, with a warning.
        all_groups_lowercase = all(key.islower() for key in groups)

        # Not all the groups are lowercased
        if not all_groups_lowercase:
            # Filter to only use uppercase groups (0.1)
            groups = {
                key: value
                for key, value in six.iteritems(groups)
                if key.isupper()
            }

            logger.warning(
                'Mixed-case group names detected - defaulting to upperacse only. '
                '0.2 supports lowercase names, so any non-group related variables '
                'in the inventory file need to be "hidden" inside a function. 0.3 '
                'will remove this check and accept mixed group names. See: '
                'http://pyinfra.readthedocs.io/en/latest/patterns/dynamic_inventories_data.html'
            )

        # Used to set all the hosts to an additional group - that of the filename
        # ie inventories/dev.py means all the hosts are in the dev group, if not present
        file_groupname = path.basename(inventory_filename).split('.')[0]

    except IOError as e:
        # If a /, definitely not a hostname
        if '/' in inventory_filename:
            raise CliError('{0}: {1}'.format(e.strerror, inventory_filename))

        # Otherwise we assume the inventory is actually a hostname or list of hostnames
        groups = {
            'all': inventory_filename.split(',')
        }

    all_data = {}

    if 'all' in groups:
        all_hosts = groups.pop('all')

        if isinstance(all_hosts, tuple):
            all_hosts, all_data = all_hosts

    # Build all out of the existing hosts if not defined
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

    groups['all'] = (all_hosts, all_data)

    # Apply the filename group if not already defined
    if file_groupname and file_groupname not in groups:
        groups[file_groupname] = all_hosts

    # In pyinfra an inventory is a combination of (hostnames + data). However, in CLI
    # mode we want to be define this in separate files (inventory / group data). The
    # issue is we want inventory access within the group data files - but at this point
    # we're not ready to make an Inventory. So here we just create a fake one, and
    # attach it to pseudo_inventory while we import the data files.
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
            attrs = exec_file(data_filename, return_locals=True)

            data.update({
                key: value
                for key, value in six.iteritems(attrs)
                if is_group_data(key, value)
            })

        # Attach to group object
        groups[name] = (hosts, data)

    # Reset the pseudo inventory
    pseudo_inventory.reset()

    # Apply any limit to all_hosts
    if limit:
        # Limits can be groups
        limit_groupname = limit
        if limit_groupname in groups:
            all_hosts = [
                host[0] if isinstance(host, tuple) else host
                for host in groups[limit_groupname][0]
            ]

        # Or hostnames w/*wildcards
        else:
            limits = limit.split(',')

            all_hosts = [
                host for host in all_hosts
                if (
                    isinstance(host, tuple)
                    and any(fnmatch(host[0], limit) for limit in limits)
                )
                or (
                    isinstance(host, six.string_types)
                    and any(fnmatch(host, limit) for limit in limits)
                )
            ]

        # Reassign the all group w/limit
        groups['all'] = (all_hosts, all_data)

    return Inventory(
        groups.pop('all'),
        ssh_user=ssh_user,
        ssh_key=ssh_key,
        ssh_key_password=ssh_key_password,
        ssh_port=ssh_port,
        ssh_password=ssh_password,
        **groups
    ), file_groupname and file_groupname.lower()
