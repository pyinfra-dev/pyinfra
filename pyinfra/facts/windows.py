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
    shell_executable = 'ps'

    @staticmethod
    def process(output):
        bios = {}
        for line in output:
            line_data = line.split(':')
            if len(line_data) > 1:
                bios.update({line_data[0].strip(): line_data[1].strip()})
        new_output = {'windows_bios': bios}
        return new_output


def _format_windows_for_key(subject, primary_key, output):
    '''Format the windows powershell output that uses 'Format-Line'
       into a dict of dicts
    '''
    primary_key = primary_key.strip()
    lines = {}
    one_item = {}
    key_value = ''
    for line in output:
        # split line on ':'
        line_data = line.split(':')
        if len(line_data) > 1:
            # we have a data line
            this_key = line_data[0].strip()
            this_data = line_data[1].strip()
            if len(line_data) > 2:
                # there was a ':' in the data, so reconstitute the value
                this_data = ':'.join(line_data[1:]).strip()
            if this_key != primary_key:
                one_item.update({this_key: this_data})
            else:
                key_value = this_data
        else:
            # we probably came across a blank line, write the line of data
            if one_item:
                lines[key_value] = one_item
                one_item = {}
                key_value = ''
    return {subject: {primary_key: lines}}


class WindowsProcessors(FactBase):
    '''
    Returns the processors info.
    '''

    command = 'Get-CimInstance -ClassName Win32_Processor | Format-List -Property *'
    shell_executable = 'ps'

    @staticmethod
    def process(output):
        return _format_windows_for_key('windows_processors', 'DeviceID', output)


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


class WindowsHotfixes(FactBase):
    '''
    Returns the Windows hotfixes.
    '''

    command = 'Get-CimInstance -ClassName Win32_QuickFixEngineering | Format-List -Property *'
    shell_executable = 'ps'

    @staticmethod
    def process(output):
        return _format_windows_for_key('windows_hotfixes', 'HotFixID', output)


class WindowsLocalDrivesInfo(FactBase):
    '''
    Returns the Windows local drives info.
    '''

    command = 'Get-CimInstance -ClassName Win32_LogicalDisk -Filter "DriveType=3" '\
              '| Format-List -Property *'
    shell_executable = 'ps'

    @staticmethod
    def process(output):
        return _format_windows_for_key('windows_local_drives_info', 'DeviceID', output)


class WindowsLoggedInUserInfo(FactBase):
    '''
    Returns the Windows user logged in info.
    '''

    command = 'Get-CimInstance -ClassName Win32_ComputerSystem -Property UserName ' \
              '| Format-List -Property *'
    shell_executable = 'ps'

    @staticmethod
    def process(output):
        return _format_windows_for_key('windows_logged_in_user_info', 'Name', output)


class WindowsLogonSessionInfo(FactBase):
    '''
    Returns the Windows user logon session info.
    '''

    command = 'Get-CimInstance -ClassName Win32_LogonSession | Format-List -Property *'
    shell_executable = 'ps'

    @staticmethod
    def process(output):
        return _format_windows_for_key('windows_logon_session_info', 'LogonId', output)


class WindowsAliases(FactBase):
    '''
    Returns the Windows aliases.
    '''

    command = 'Get-Alias | Format-List -Property *'
    shell_executable = 'ps'

    @staticmethod
    def process(output):
        return _format_windows_for_key('windows_get_aliases', 'Definition', output)


# TODO: Services (tip: 'Get-Command -Noun Service' or
# simply 'Get-Command' to see what you can do...)
# Stop-Service -Name <name>
# Suspend-Service -Name <name>
# Restart-Service -Name <name>
class WindowsServices(FactBase):
    '''
    Returns the Windows services.
    '''

    command = 'Get-CimInstance -ClassName Win32_Service | Format-List -Property *'
    shell_executable = 'ps'

    @staticmethod
    def process(output):
        return _format_windows_for_key('windows_services', 'Name', output)


# TODO: for operations: Stop-Process <id>
class WindowsProcesses(FactBase):
    '''
    Returns the Windows processes.
    '''

    command = 'Get-Process | Format-List -Property *'
    shell_executable = 'ps'

    @staticmethod
    def process(output):
        return _format_windows_for_key('windows_processes', 'Id', output)


class WindowsNetworkConfiguration(FactBase):
    '''
    Returns the Windows network configuration.
    '''

    command = 'Get-CimInstance -Class Win32_NetworkAdapterConfiguration | Format-List -Property *'
    shell_executable = 'ps'

    @staticmethod
    def process(output):
        return _format_windows_for_key('windows_network_configuration', 'Index', output)


class WindowsInstallerApplications(FactBase):
    '''
    Returns the Windows installer applications.
    '''

    command = 'Get-CimInstance -Class Win32_Product | Format-List -Property *'
    shell_executable = 'ps'

    @staticmethod
    def process(output):
        return _format_windows_for_key('windows_installer_applications',
                                       'IdentifyingNumber', output)
