# pyinfra
# File: pyinfra/facts/git.py
# Desc: local git repo facts

from __future__ import unicode_literals

from pyinfra.api.facts import FactBase


class GitBranch(FactBase):
    def command(self, name):
        return 'cd {0} && git rev-parse --abbrev-ref HEAD'.format(name)
