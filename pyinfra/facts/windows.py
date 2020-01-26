from __future__ import unicode_literals

import re
from datetime import datetime

from dateutil.parser import parse as parse_date

from pyinfra.api import FactBase


class WinHome(FactBase):
    '''
    Returns the home directory of the current user.
    '''

    command = 'echo %HOMEPATH%'
    shell = 'cmd'


class WinHostname(FactBase):
    '''
    Returns the current hostname of the server.
    '''

    command = 'hostname'
    shell = 'cmd'


class WinOs(FactBase):
    '''
    Returns the OS name according to ``systeminfo``.
    '''

    command = 'systeminfo.exe | findstr /c:"OS Name:"'
    shell = 'cmd'

    @staticmethod
    def process(output):
        new_output = ''
        match = re.match('OS Name:[ ]*(.*)', output[0])
        if match:
            new_output = match.group(1)
        return new_output


class WinOsVersion(FactBase):
    '''
    Returns the OS version according to ``systeminfo``.
    '''

    command = 'systeminfo | findstr /c:"OS Version:"'
    shell = 'cmd'

    @staticmethod
    def process(output):
        new_output = ''
        match = re.match('OS Version:[ ]*(.*)', output[0])
        if match:
            new_output = match.group(1)
        return new_output


class WinSystemType(FactBase):
    '''
    Returns the system type according to ``systeminfo``.
    '''

    command = 'systeminfo | findstr /c:"System Type:"'
    shell = 'cmd'

    @staticmethod
    def process(output):
        new_output = ''
        match = re.match('System Type:[ ]*(.*)', output[0])
        if match:
            new_output = match.group(1)
        return new_output


class WinDate(FactBase):
    '''
    Returns the current datetime on the server.
    '''

    command = 'echo %date%-%time%'
    shell = 'cmd'
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


class WinWhich(FactBase):
    '''
    Returns the full path for a command, if available.
    '''

    @staticmethod
    def command(name):
        return 'where {0}'.format(name)

    @staticmethod
    def process(output):
        return output[0].rstrip()
