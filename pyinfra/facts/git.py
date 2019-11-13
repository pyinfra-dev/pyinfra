from __future__ import unicode_literals

from pyinfra.api.facts import FactBase


class GitBranch(FactBase):
    @staticmethod
    def command(repo):
        return 'cd {0} && git rev-parse --abbrev-ref HEAD'.format(repo)


class GitConfig(FactBase):
    @staticmethod
    def command(repo=None):
        if repo is None:
            return 'git config --global -l'

        return 'cd {0} && git config --local -l'.format(repo)

    @staticmethod
    def process(output):
        items = {}

        for line in output:
            key, value = line.split('=', 1)
            items[key] = value

        return items
