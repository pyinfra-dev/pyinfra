import re

from pyinfra.api import FactBase


# Valid unit names consist of a "name prefix" and a dot and a suffix specifying the unit type.
# The "unit prefix" must consist of one or more valid characters
# (ASCII letters, digits, ":", "-", "_", ".", and "\").
# The total length of the unit name including the suffix must not exceed 256 characters.
# The type suffix must be one of
# ".service", ".socket", ".device", ".mount", ".automount",
# ".swap", ".target", ".path", ".timer", ".slice", or ".scope".
# Units names can be parameterized by a single argument called the "instance name".
# A template unit must have a single "@" at the end of the name (right before the type suffix).
# The name of the full unit is formed by inserting the instance name
# between "@" and the unit type suffix.
SYSTEMD_UNIT_NAME_REGEX = (
    r'[a-zA-Z0-9\:\-\_\.\\\@]+\.'
    r'(?:service|socket|device|mount|automount|swap|target|path|timer|slice|scope)'
)


def _make_systemctl_cmd(user_mode=False, machine=None, user_name=None):
    # base command for normal and user mode
    systemctl_cmd = 'systemctl --user' if user_mode else 'systemctl'

    # add user and machine flag if given in args
    if machine is not None:
        if user_name is not None:
            machine_opt = '--machine={1}@{0}'.format(machine, user_name)
        else:
            machine_opt = '--machine={0}'.format(machine)

        systemctl_cmd = '{0} {1}'.format(systemctl_cmd, machine_opt)

    return systemctl_cmd


class SystemdStatus(FactBase):
    '''
    Returns a dict of name -> status for systemd managed services.
    '''

    requires_command = 'systemctl'

    default = dict

    regex = r'^({systemd_unit_name_regex})\s+[a-z\-]+\s+[a-z]+\s+([a-z]+)'.format(
        systemd_unit_name_regex=SYSTEMD_UNIT_NAME_REGEX)

    def command(self, user_mode=False, machine=None, user_name=None):
        fact_cmd = _make_systemctl_cmd(
            user_mode=user_mode,
            machine=machine,
            user_name=user_name,
        )

        return '{0} -al --plain --no-legend list-units'.format(fact_cmd)

    def process(self, output):
        services = {}

        for line in output:
            line = line.strip()
            matches = re.match(self.regex, line)
            if matches:
                is_active = matches.group(2) in ('running', 'waiting', 'exited')
                services[matches.group(1)] = is_active

        return services


class SystemdEnabled(FactBase):
    '''
    Returns a dict of name -> whether enabled for systemd managed services.
    '''

    requires_command = 'systemctl'

    default = dict

    regex = r'^({systemd_unit_name_regex})\s+([a-z]+)'.format(
        systemd_unit_name_regex=SYSTEMD_UNIT_NAME_REGEX)

    def command(self, user_mode=False, machine=None, user_name=None):
        fact_cmd = _make_systemctl_cmd(
            user_mode=user_mode,
            machine=machine,
            user_name=user_name,
        )

        return (
            '{0} -al --plain --no-legend --state=loaded list-units | '
            'while read -r UNIT REST; do '
            'STATE=$({0} -P UnitFileState show -- "$UNIT"); '
            'if [ -n "$STATE" ]; then '
            'echo "$UNIT" "$STATE"; '
            'fi; '
            'done'
        ).format(fact_cmd)

    def process(self, output):
        units = {}

        for line in output:
            matches = re.match(self.regex, line)
            if matches:
                units[matches.group(1)] = (
                    matches.group(2) in ('enabled', 'static')
                )

        return units
