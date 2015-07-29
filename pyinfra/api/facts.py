# pyinfra
# File: pyinfra/api/facts.py
# Desc: index fact classes for access via pyinfra.host

from gevent.lock import Semaphore
from termcolor import colored

from pyinfra import state, logger

from .ssh import run_shell_command
from .util import underscore, make_hash


# Index of snake_case facts -> CamelCase classes
facts = {}
# Lock on getting facts
fact_locks = {}
print_facts = False

def set_print_facts(to_print):
    global print_facts
    print_facts = to_print

def is_fact(name):
    return name in facts

def get_fact_names():
    return facts.keys()


class FactMeta(type):
    '''Metaclass to dynamically build the facts index.'''
    def __init__(cls, name, bases, attrs):
        global facts

        # Get the an instance of the fact, attach to facts
        facts[underscore(name)] = cls()

class FactBase(object):
    __metaclass__ = FactMeta

    def process(self, output):
        return output[0]


def get_facts(name, arg=None, sudo=False, sudo_user=None, print_output=False):
    print_output = print_output or print_facts
    fact = facts[name]
    command = fact.command

    if arg:
        command = command(arg)

    fact_hash = make_hash((name, command, sudo, sudo_user))

    fact_locks.setdefault(fact_hash, Semaphore()).acquire()

    if facts.get(fact_hash):
        fact_locks[fact_hash].release()
        return facts[fact_hash]

    # Execute the command for each state inventory in a greenlet
    greenlets = {
        host.ssh_hostname: state.fact_pool.spawn(
            run_shell_command, host.ssh_hostname, command,
            sudo=sudo, sudo_user=sudo_user, print_output=print_output,
            print_prefix='[{0}] '.format(colored(host.ssh_hostname, attrs=['bold']))
        )
        for host in state.inventory
    }

    hostname_facts = {}

    for hostname, greenlet in greenlets.iteritems():
        channel, stdout, stderr = greenlet.get()
        data = fact.process(stdout) if stdout else None
        hostname_facts[hostname] = data

    log_name = colored(name, attrs=['bold'])
    if arg:
        logger.info('Loaded fact {0}: {1}'.format(log_name, arg))
    else:
        logger.info('Loaded fact {0}'.format(log_name))

    facts[fact_hash] = hostname_facts
    fact_locks[fact_hash].release()
    return hostname_facts


def get_fact(hostname, name, print_output=False):
    '''Wrapper around get_facts returning facts for one host or a function that does.'''
    print_output = print_output or print_facts
    sudo = False
    sudo_user = None

    if state.current_op_sudo:
        sudo, sudo_user = state.current_op_sudo

    # Expecting a function to return
    if callable(facts[name].command):
        def wrapper(arg):
            fact_data = get_facts(
                name, arg,
                sudo=sudo, sudo_user=sudo_user, print_output=print_output
            )
            return fact_data.get(hostname)

        return wrapper

    # Expecting the fact as a return value
    else:
        # Get the fact
        fact_data = get_facts(name, sudo=sudo, sudo_user=sudo_user, print_output=print_output)
        return fact_data.get(hostname)
