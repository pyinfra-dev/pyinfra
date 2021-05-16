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


class SystemdStatus(FactBase):
    '''
    Returns a dict of name -> status for systemd managed services.
    '''

    command = 'systemctl -al list-units'
    requires_command = 'systemctl'

    default = dict

    regex = r'^({systemd_unit_name_regex})\s+[a-z\-]+\s+[a-z]+\s+([a-z]+)'.format(
        systemd_unit_name_regex=SYSTEMD_UNIT_NAME_REGEX)

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

    command = '''
        systemctl --no-legend -al list-unit-files | while read -r UNIT STATUS; do
            if [ "$STATUS" = generated ] &&
                systemctl is-enabled $UNIT >/dev/null 2>&1; then
                STATUS=enabled
            fi
            echo $UNIT $STATUS
        done
    '''
    requires_command = 'systemctl'

    default = dict

    regex = r'^({systemd_unit_name_regex})\s+([a-z]+)'.format(
        systemd_unit_name_regex=SYSTEMD_UNIT_NAME_REGEX)

    def process(self, output):
        units = {}

        for line in output:
            matches = re.match(self.regex, line)
            if matches:
                units[matches.group(1)] = (
                    matches.group(2) in ('enabled', 'static')
                )

        return units
