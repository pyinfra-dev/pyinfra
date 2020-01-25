from __future__ import unicode_literals

import re
from datetime import datetime

from dateutil.parser import parse as parse_date

from pyinfra.api import FactBase, ShortFactBase
from pyinfra.api.util import try_int


class WinHome(FactBase):
    '''
    Returns the home directory of the current user.
    '''

    command = 'echo %HOMEPATH%'


class WinHostname(FactBase):
    '''
    Returns the current hostname of the server.
    '''

    command = 'hostname'


class WinOs(FactBase):
    '''
    Returns the OS name according to ``uname`` or ``systeminfo``.
    '''

    command = 'systeminfo.exe | findstr /c:"OS Name:"'


class WinOsVersion(FactBase):
    '''
    Returns the OS version according to ``uname`` or ``systeminfo``.
    '''

    command = 'systeminfo | findstr /c:"OS Version:"'


class WinArch(FactBase):
    '''
    Returns the system architecture according to ``uname`` or ``systeminfo``.
    '''

    command = 'systeminfo | findstr /c:"System Type:"'


class WinWhich(FactBase):
    '''
    Returns the path of a given command, if available.
    '''

    @staticmethod
    def command(name):
        return 'where {0}'.format(name)


class WinDate(FactBase):
    '''
    Returns the current datetime on the server.
    '''

    command = 'echo %date%-%time%'
    default = datetime.now

    @staticmethod
    def process(output):
        new_output = ''.join(output)
        return parse_date(new_output)

class WinLocalGroups(FactBase):
    '''
    Returns a list of groups on the system.
    '''

    command = 'net localgroup | findstr [^*]'

    default = list

    @staticmethod
    def process(output):
        groups = output
        # remove empty group
        groups.remove('')

        return groups
