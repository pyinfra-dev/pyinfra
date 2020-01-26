from __future__ import unicode_literals

import re

from pyinfra.api.facts import FactBase

from .util.win_files import parse_win_ls_output


class WinFile(FactBase):
    # Types must match WIN_FLAG_TO_TYPE in .util.win_files.py
    type = 'file'
    shell = 'ps'

    def command(self, name):
        self.name = name
        return 'ls {0}'.format(name)

    def process(self, output):
        # Note: The first 7 lines are header lines
        return parse_win_ls_output(output[7], self.type)
