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
    r"[a-zA-Z0-9\:\-\_\.\\\@]+\."
    r"(?:service|socket|device|mount|automount|swap|target|path|timer|slice|scope)"
)


def _make_systemctl_cmd(user_mode=False, machine=None, user_name=None):
    # base command for normal and user mode
    systemctl_cmd = "systemctl --user" if user_mode else "systemctl"

    # add user and machine flag if given in args
    if machine is not None:
        if user_name is not None:
            machine_opt = "--machine={1}@{0}".format(machine, user_name)
        else:
            machine_opt = "--machine={0}".format(machine)

        systemctl_cmd = "{0} {1}".format(systemctl_cmd, machine_opt)

    return systemctl_cmd


class SystemdStatus(FactBase):
    """
    Returns a dictionary map of systemd units to booleans indicating whether they are active.

    + user_mode: whether to use user mode
    + machine: machine name

    .. code:: python

        {
            "ssh.service": True,
            "containerd.service": True,
            "apt-daily.timer": False,
        }
    """

    requires_command = "systemctl"

    default = dict

    state_key = "SubState"
    state_values = ["running", "waiting", "exited"]

    def command(self, user_mode=False, machine=None, user_name=None):
        fact_cmd = _make_systemctl_cmd(
            user_mode=user_mode,
            machine=machine,
            user_name=user_name,
        )

        return f"{fact_cmd} show --all --property Id --property {self.state_key} '*'"

    def process(self, output):
        services = {}

        current_unit = None
        for line in output:
            line = line.strip()

            try:
                key, value = line.split("=", 1)
            except ValueError:
                current_unit = None  # reset current_unit just in case
                continue

            if key == "Id" and re.match(SYSTEMD_UNIT_NAME_REGEX, value):
                current_unit = value
                continue

            if key == self.state_key and current_unit:
                services[current_unit] = value in self.state_values

        return services


class SystemdEnabled(SystemdStatus):
    """
    Returns a dictionary map of systemd units to booleans indicating whether they are enabled.

    .. code:: python

        {
            "ssh.service": True,
            "containerd.service": True,
            "apt-daily.timer": False,
        }
    """

    state_key = "UnitFileState"
    state_values = ["enabled", "static"]
