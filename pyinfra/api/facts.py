# pyinfra
# File: pyinfra/api/facts.py
# Desc: the facts API

'''
The pyinfra facts API. Facts enable pyinfra to collect remote server state which is used
to "diff" with the desired state, producing the final commands required for a deploy.
'''

from __future__ import division, unicode_literals

from socket import timeout as timeout_error

import six
from gevent.lock import Semaphore
from termcolor import colored
from paramiko import SSHException

from pyinfra import logger

from .ssh import run_shell_command
from .util import underscore, make_hash


# Index of snake_case facts -> CamelCase classes
FACTS = {}


def is_fact(name):
    return name in FACTS


def get_fact_names():
    '''
    Returns a list of available facts in camel_case format.
    '''

    return FACTS.keys()


class FactMeta(type):
    '''
    Metaclass to dynamically build the facts index.
    '''

    def __init__(cls, name, bases, attrs):
        global FACTS

        # Get the an instance of the fact, attach to facts
        FACTS[underscore(name)] = cls


@six.add_metaclass(FactMeta)
class FactBase(object):
    default = None

    def process(self, output):
        return output[0]

    def process_pipeline(self, args, output):
        return {
            arg: self.process([output[i]])
            for i, arg in enumerate(args)
        }


def get_pipeline_facts(state, name, args, sudo, sudo_user):
    pass


def get_facts(
    state, name,
    args=None, sudo=False, sudo_user=None
):
    '''
    Get a single fact for all hosts in the state.
    '''

    sudo = sudo or state.config.SUDO
    sudo_user = sudo_user or state.config.SUDO_USER
    ignore_errors = state.config.IGNORE_ERRORS

    if state.current_op_meta:
        sudo, sudo_user, ignore_errors = state.current_op_meta

    # Create an instance of the fact
    fact = FACTS[name]()

    # If we're inactive or  (pipelining & inside an op): just return the defaults
    if not state.active or (state.pipelining and state.in_op):
        return {
            host.name: fact.default
            for host in state.inventory
        }

    command = fact.command

    if args:
        command = command(*args)

    # Make a hash which keeps facts unique - but usable cross-deploy/threads. Locks are
    # used to maintain order.
    fact_hash = make_hash((name, command, sudo, sudo_user))

    # Lock!
    state.fact_locks.setdefault(fact_hash, Semaphore()).acquire()

    # Already got this fact? Unlock and return 'em
    if state.facts.get(fact_hash):
        state.fact_locks[fact_hash].release()
        return state.facts[fact_hash]

    # Execute the command for each state inventory in a greenlet
    greenlets = {
        host.name: state.pool.spawn(
            run_shell_command, state, host.name, command,
            sudo=sudo, sudo_user=sudo_user,
            print_output=state.print_fact_output
        )
        for host in state.inventory
    }

    hostname_facts = {}
    failed_hosts = set()

    # Collect the facts and any failures
    for hostname, greenlet in six.iteritems(greenlets):
        try:
            channel, stdout, stderr = greenlet.get()

            if stdout:
                data = fact.process(stdout)
            else:
                data = fact.default

            hostname_facts[hostname] = data

        except (timeout_error, SSHException):

            if ignore_errors:
                logger.warning('[{0}] {1}'.format(
                    hostname,
                    colored('Fact error (ignored)', 'yellow')
                ))
            else:
                failed_hosts.add(hostname)
                logger.error('[{0}] {1}'.format(
                    hostname,
                    colored('Fact error', 'red')
                ))

    log_name = colored(name, attrs=['bold'])

    if args:
        log = 'Loaded fact {0}: {1}'.format(log_name, args)
    else:
        log = 'Loaded fact {0}'.format(log_name)

    if state.print_fact_info:
        logger.info(log)
    else:
        logger.debug(log)

    # Check we've not failed
    if not ignore_errors:
        state.fail_hosts(failed_hosts)

    # Assign the facts
    state.facts[fact_hash] = hostname_facts

    # Release the lock, return the data
    state.fact_locks[fact_hash].release()
    return state.facts[fact_hash]


def get_fact(state, hostname, name):
    '''
    Wrapper around ``get_facts`` returning facts for one host or a function that does.
    '''

    # Expecting a function to return
    if callable(FACTS[name].command):
        def wrapper(*args):
            fact_data = get_facts(state, name, args=args)

            return fact_data.get(hostname)
        return wrapper

    # Expecting the fact as a return value
    else:
        # Get the fact
        fact_data = get_facts(state, name)

        return fact_data.get(hostname)
