# pyinfra
# File: pyinfra/api/facts.py
# Desc: index fact classes for access via pyinfra.host

from socket import timeout as timeout_error

from gevent.lock import Semaphore
from termcolor import colored
from paramiko import SSHException

from pyinfra import logger
from pyinfra.api.exceptions import PyinfraError

from .ssh import run_shell_command
from .util import underscore, make_hash


# Index of snake_case facts -> CamelCase classes
facts = {}
# Lock on getting facts
fact_locks = {}
print_fact_info = False
print_fact_output = False


def set_print_facts(to_print_output, to_print_info):
    global print_fact_info, print_fact_output

    print_fact_info = to_print_info
    print_fact_output = to_print_output


def is_fact(name):
    return name in facts


def get_fact_names():
    '''
    Returns a list of available facts in camel_case format.
    '''

    return facts.keys()


class FactMeta(type):
    '''
    Metaclass to dynamically build the facts index.
    '''

    def __init__(cls, name, bases, attrs):
        global facts

        # Get the an instance of the fact, attach to facts
        facts[underscore(name)] = cls


class FactBase(object):
    __metaclass__ = FactMeta

    @classmethod
    def process(cls, output):
        return output[0]


def get_facts(state, name, args=None, sudo=False, sudo_user=None, print_output=False):
    '''
    Get a single fact for all hosts in the state.
    '''

    print_output = print_output or print_fact_output

    sudo = state.config.SUDO
    sudo_user = state.config.SUDO_USER
    ignore_errors = state.config.IGNORE_ERRORS

    if state.current_op_meta:
        sudo, sudo_user, ignore_errors = state.current_op_meta

    # Create an instance of the fact
    fact = facts[name]()

    command = fact.command

    if args:
        command = command(*args)

    fact_hash = make_hash((name, command, sudo, sudo_user))

    fact_locks.setdefault(fact_hash, Semaphore()).acquire()

    if facts.get(fact_hash):
        fact_locks[fact_hash].release()
        return facts[fact_hash]

    # Execute the command for each state inventory in a greenlet
    greenlets = {
        host.name: state.pool.spawn(
            run_shell_command, state, host.name, command,
            sudo=sudo, sudo_user=sudo_user, print_output=print_output,
            print_prefix='[{0}] '.format(colored(host.name, attrs=['bold']))
        )
        for host in state.inventory
    }

    hostname_facts = {}
    failed_hosts = set()

    for hostname, greenlet in greenlets.iteritems():
        try:
            channel, stdout, stderr = greenlet.get()
            data = fact.process(stdout) if stdout else None
            hostname_facts[hostname] = data

        except (timeout_error, SSHException):
            failed_hosts.add(hostname)

            if ignore_errors:
                logger.warning('[{0}] {1}'.format(
                    hostname,
                    colored('Fact error (ignored)', 'yellow')
                ))
            else:
                logger.error('[{0}] {1}'.format(
                    hostname,
                    colored('Fact error', 'red')
                ))

    log_name = colored(name, attrs=['bold'])

    if args:
        log = 'Loaded fact {0}: {1}'.format(log_name, args)
    else:
        log = 'Loaded fact {0}'.format(log_name)

    if print_fact_info:
        logger.info(log)
    else:
        logger.debug(log)

    # Remove any failed hosts from the inventory
    state.inventory.connected_hosts -= failed_hosts

    # Check we've not failed
    if not ignore_errors:
        n_connected_hosts = len(hostname_facts)
        if state.config.FAIL_PERCENT is not None:
            percent_failed = (1 - n_connected_hosts / len(state.inventory)) * 100
            if percent_failed > state.config.FAIL_PERCENT:
                raise PyinfraError('Over {0}% of hosts failed, exiting'.format(
                    state.config.FAIL_PERCENT
                ))

    facts[fact_hash] = hostname_facts
    fact_locks[fact_hash].release()
    return hostname_facts


def get_fact(state, hostname, name, print_output=False):
    '''
    Wrapper around get_facts returning facts for one host or a function that does.
    '''

    # Expecting a function to return
    if callable(facts[name].command):
        def wrapper(*args):
            fact_data = get_facts(
                state, name, args=args,
                print_output=print_output
            )
            return fact_data.get(hostname)

        return wrapper

    # Expecting the fact as a return value
    else:
        # Get the fact
        fact_data = get_facts(
            state, name,
            print_output=print_output
        )
        return fact_data.get(hostname)
