# pyinfra
# File: pyinfra/api/pipelining.py
# Desc: pipelining related functions and helpers

from __future__ import unicode_literals

from inspect import getargspec

import six

from pyinfra import logger


class PipelineFacts(object):
    def __init__(self, state):
        self.state = state
        self.state.ops_to_pipeline = []
        self.state.facts_to_pipeline = {}

    def __enter__(self):
        self.state.pipelining = True

    def __exit__(self, type_, value, traceback):
        self.state.pipelining = False

        # Get pipelined facts!
        # for name, args in six.iteritems(self.state.facts_to_pipeline):
        #     get_facts(self.state, name, pipeline_args=args)

        # Actually build our ops
        for (host_name, func, args, kwargs) in self.state.ops_to_pipeline:
            logger.debug(
                'Replaying op: {0}, args={1}, kwargs={2}'.format(func, args, kwargs)
            )

            func(self.state, self.state.inventory[host_name], *args, **kwargs)

    def process(self, func, decorated_func, args, kwargs):
        pipeline_facts = getattr(decorated_func, 'pipeline_facts', None)

        if pipeline_facts:
            func_args = list(getargspec(func).args)
            func_args = func_args[2:]

            for fact_name, arg_name in six.iteritems(pipeline_facts):
                index = func_args.index(arg_name)

                if len(args) >= index:
                    fact_arg = args[index]
                else:
                    fact_arg = kwargs.get(arg_name)

                if fact_arg:
                    # Get the sudo/sudo_user state, because facts are uniquely hashed
                    # using their name, command and sudo/sudo_user.
                    sudo = kwargs.get('sudo', self.state.config.SUDO)
                    sudo_user = kwargs.get('sudo_user', self.state.config.SUDO_USER)

                    self.state.facts_to_pipeline.setdefault(
                        (fact_name, sudo, sudo_user), set()
                    ).add(fact_arg)
