import re
from datetime import datetime

from dateutil.parser import parse as parse_date

from pyinfra.api import FactBase


class Home(FactBase):
    """
    Returns the home directory of the current user.
    """

    command = "echo %HOMEPATH%"
    shell_executable = "cmd"

    @staticmethod
    def process(output):
        return "".join(output).replace("\n", "")


class Hostname(FactBase):
    """
    Returns the current hostname of the server.
    """

    command = "hostname"

    @staticmethod
    def process(output):
        return "".join(output).replace("\n", "")


class LastReboot(FactBase):
    """
    Returns the date and time of the last reboot.
    """

    command = (
        "Get-CimInstance -ClassName Win32_OperatingSystem | "
        "Select -ExpandProperty LastBootUptime"
    )

    @staticmethod
    def process(output):
        return "".join(output).replace("\n", "")


class Os(FactBase):
    """
    Returns the OS name according to ``systeminfo``.
    """

    command = 'systeminfo.exe | findstr /c:"OS Name:"'

    @staticmethod
    def process(output):
        new_output = ""
        match = re.match("OS Name:[ ]*(.*)", output[0])
        if match:
            new_output = match.group(1)
        return new_output


class Bios(FactBase):
    """
    Returns the BIOS info.
    """

    command = "Get-CimInstance -ClassName Win32_BIOS"

    @staticmethod
    def process(output):
        bios = {}
        for line in output:
            line_data = line.split(":")
            if len(line_data) > 1:
                bios.update({line_data[0].strip(): line_data[1].strip()})
        return bios


def _format_windows(output):
    lines = {}
    for line in output:
        # split line on ':'
        line_data = line.split(":")
        if len(line_data) > 1:
            # we have a data line
            this_key = line_data[0].strip()
            this_data = line_data[1].strip()
            if len(line_data) > 2:
                # there was a ':' in the data, so reconstitute the value
                this_data = ":".join(line_data[1:]).strip()
            lines[this_key] = this_data
    return lines


def _format_windows_for_key(primary_key, output, return_primary_key=True):
    """Format the windows powershell output that uses 'Format-Line'
    into a dict of dicts.
    """
    primary_key = primary_key.strip()
    lines = {}
    one_item = {}
    key_value = ""
    for line in output:
        # split line on ':'
        line_data = line.split(":")
        if len(line_data) > 1:
            # we have a data line
            this_key = line_data[0].strip()
            this_data = line_data[1].strip()
            if len(line_data) > 2:
                # there was a ':' in the data, so reconstitute the value
                this_data = ":".join(line_data[1:]).strip()
            if this_key != primary_key:
                one_item.update({this_key: this_data})
            else:
                key_value = this_data
        else:
            if line == "":
                if one_item:
                    lines[key_value] = one_item
                    one_item = {}
                    key_value = ""
            else:
                # append this_data to the existing entry
                this_data = line.strip()
                appended_data = one_item[this_key] + this_data
                one_item.update({this_key: appended_data})
    if return_primary_key:
        return {primary_key: lines}
    return lines


class Processors(FactBase):
    """
    Returns the processors info.
    """

    command = "Get-CimInstance -ClassName Win32_Processor | Format-List -Property *"

    @staticmethod
    def process(output):
        return _format_windows_for_key("DeviceID", output)


class OsVersion(FactBase):
    """
    Returns the OS version according to ``systeminfo``.
    """

    command = 'systeminfo | findstr /c:"OS Version:"'

    @staticmethod
    def process(output):
        new_output = ""
        match = re.match("OS Version:[ ]*(.*)", output[0])
        if match:
            new_output = match.group(1)
        return new_output


class SystemType(FactBase):
    """
    Returns the system type according to ``systeminfo``.
    """

    command = 'systeminfo | findstr /c:"System Type:"'

    @staticmethod
    def process(output):
        new_output = ""
        match = re.match("System Type:[ ]*(.*)", output[0])
        if match:
            new_output = match.group(1)
        return new_output


class Date(FactBase):
    """
    Returns the current datetime on the server.
    """

    command = "echo %date%-%time%"
    shell_executable = "cmd"
    default = datetime.now

    @staticmethod
    def process(output):
        new_output = "".join(output)
        return parse_date(new_output)


class LocalGroups(FactBase):
    """
    Returns a list of groups on the system.
    """

    command = "net localgroup | findstr [^*]"

    default = list

    @staticmethod
    def process(output):
        groups = []
        for group in output:
            # Note: If run this command thru ps, there are headers/footer.
            # remove empty groups and those groups that are not local
            if group != "" and group[0] == "*":
                groups.append(group)
        return groups


class Where(FactBase):
    """
    Returns the full path for a command, if available.
    """

    shell_executable = "cmd"

    @staticmethod
    def command(name):
        return "where {0}".format(name)

    @staticmethod
    def process(output):
        return output[0].rstrip()


class Hotfixes(FactBase):
    """
    Returns the Windows hotfixes.
    """

    command = "Get-CimInstance -ClassName Win32_QuickFixEngineering | Format-List -Property *"

    @staticmethod
    def process(output):
        return _format_windows_for_key("HotFixID", output)


class LocalDrivesInfo(FactBase):
    """
    Returns the Windows local drives info.
    """

    command = (
        'Get-CimInstance -ClassName Win32_LogicalDisk -Filter "DriveType=3" '
        "| Format-List -Property *"
    )

    @staticmethod
    def process(output):
        return _format_windows_for_key("DeviceID", output)


class LoggedInUserInfo(FactBase):
    """
    Returns the Windows user logged in info.
    """

    command = (
        "Get-CimInstance -ClassName Win32_ComputerSystem -Property UserName "
        "| Format-List -Property *"
    )

    @staticmethod
    def process(output):
        return _format_windows_for_key("Name", output)


class LogonSessionInfo(FactBase):
    """
    Returns the Windows user logon session info.
    """

    command = "Get-CimInstance -ClassName Win32_LogonSession | Format-List -Property *"

    @staticmethod
    def process(output):
        return _format_windows_for_key("LogonId", output)


class Aliases(FactBase):
    """
    Returns the Windows aliases.
    """

    command = "Get-Alias | Format-List -Property *"

    @staticmethod
    def process(output):
        return _format_windows_for_key("Name", output)


class Services(FactBase):
    """
    Returns the Windows services.
    """

    command = "Get-CimInstance -ClassName Win32_Service | Format-List -Property *"

    @staticmethod
    def process(output):
        return _format_windows_for_key("Name", output)


class Service(FactBase):
    """
    Returns info about a Windows service.
    """

    def command(self, name):
        return "Get-Service -Name {} | Format-List -Property *".format(name)

    def process(self, output):
        return _format_windows_for_key("Name", output, return_primary_key=False)


class Processes(FactBase):
    """
    Returns the Windows processes.
    """

    command = "Get-Process | Format-List -Property *"

    @staticmethod
    def process(output):
        return _format_windows_for_key("Id", output)


class NetworkConfiguration(FactBase):
    """
    Returns the Windows network configuration.
    """

    command = "Get-CimInstance -Class Win32_NetworkAdapterConfiguration | Format-List -Property *"

    @staticmethod
    def process(output):
        return _format_windows_for_key("Index", output)


class InstallerApplications(FactBase):
    """
    Returns the Windows installer applications.
    """

    command = "Get-CimInstance -Class Win32_Product | Format-List -Property *"

    @staticmethod
    def process(output):
        return _format_windows_for_key("IdentifyingNumber", output)


class ComputerInfo(FactBase):
    """
    Returns the Windows info.
    """

    command = "Get-ComputerInfo | Format-List -Property *"

    @staticmethod
    def process(output):
        return _format_windows(output)
