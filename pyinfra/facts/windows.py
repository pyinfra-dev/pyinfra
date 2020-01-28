from __future__ import unicode_literals

import re
from datetime import datetime

from dateutil.parser import parse as parse_date

from pyinfra.api import FactBase


class WindowsHome(FactBase):
    '''
    Returns the home directory of the current user.
    '''

    command = 'echo %HOMEPATH%'


class WindowsHostname(FactBase):
    '''
    Returns the current hostname of the server.
    '''

    command = 'hostname'


class WindowsOs(FactBase):
    '''
    Returns the OS name according to ``systeminfo``.
    '''

    command = 'systeminfo.exe | findstr /c:"OS Name:"'

    @staticmethod
    def process(output):
        new_output = ''
        match = re.match('OS Name:[ ]*(.*)', output[0])
        if match:
            new_output = match.group(1)
        return new_output


class WindowsBios(FactBase):
    '''
    Returns the BIOS info.
    '''

    command = 'Get-CimInstance -ClassName Win32_BIOS'

    @staticmethod
    def process(output):
        bios = {}
        for line in output:
            line_data = line.split(':')
            if len(line_data) > 1:
                bios.update({line_data[0].strip(): line_data[1].strip()})
        new_output = {'windows_bios': bios}
        return new_output


class WindowsProcessors(FactBase):
    '''
    Returns the processors info.
    '''

    command = 'Get-CimInstance -ClassName Win32_Processor | Format-List'

    @staticmethod
    def process(output):
        procs = []
        one_proc_data = {}
        for line in output:
            line_data = line.split(':')
            if len(line_data) > 1:
                one_proc_data.update({line_data[0].strip(): line_data[1].strip()})
            else:
                if one_proc_data:
                    procs.append(one_proc_data)
                    one_proc_data = {}
        new_output = {'windows_processors': procs}
        return new_output


class WindowsOsVersion(FactBase):
    '''
    Returns the OS version according to ``systeminfo``.
    '''

    command = 'systeminfo | findstr /c:"OS Version:"'

    @staticmethod
    def process(output):
        new_output = ''
        match = re.match('OS Version:[ ]*(.*)', output[0])
        if match:
            new_output = match.group(1)
        return new_output


class WindowsSystemType(FactBase):
    '''
    Returns the system type according to ``systeminfo``.
    '''

    command = 'systeminfo | findstr /c:"System Type:"'

    @staticmethod
    def process(output):
        new_output = ''
        match = re.match('System Type:[ ]*(.*)', output[0])
        if match:
            new_output = match.group(1)
        return new_output


class WindowsDate(FactBase):
    '''
    Returns the current datetime on the server.
    '''

    command = 'echo %date%-%time%'
    default = datetime.now

    @staticmethod
    def process(output):
        new_output = ''.join(output)
        return parse_date(new_output)


class WindowsLocalGroups(FactBase):
    '''
    Returns a list of groups on the system.
    '''

    command = 'net localgroup | findstr [^*]'

    default = list

    @staticmethod
    def process(output):
        groups = []
        for group in output:
            # Note: If run this command thru ps, there are headers/footer.
            # remove empty groups and those groups that are not local
            if group != '' and group[0] == '*':
                groups.append(group)
        return groups


class WindowsWhere(FactBase):
    '''
    Returns the full path for a command, if available.
    '''

    @staticmethod
    def command(name):
        return 'where {0}'.format(name)

    @staticmethod
    def process(output):
        return output[0].rstrip()
