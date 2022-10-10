import re
from collections import defaultdict

from pyinfra.api import FactBase

FIELDS = ["user", "role", "type", "level"]  # order is significant, do not change


class SEBoolean(FactBase):
    """
    Returns the status of a SELinux Boolean as a string (``on`` or ``off``).
    If ``boolean`` does not exist, ``SEBoolean`` returns the empty string.
    """

    requires_command = "getsebool"
    default = str

    def command(self, boolean):
        return "getsebool {0}".format(boolean)

    def process(self, output):
        components = output[0].split(" --> ")
        return components[1]


class FileContext(FactBase):
    """
    Returns structured SELinux file context data for a specified file
    or ``None`` if the file does not exist.

    .. code:: python

        {
            "user": "system_u",
            "role": "object_r",
            "type": "default_t",
            "level": "s0",
        }
    """

    def command(self, path):
        return "stat -c %C {0} || exit 0".format(path)

    def process(self, output):
        context = {}
        components = output[0].split(":")
        context["user"] = components[0]
        context["role"] = components[1]
        context["type"] = components[2]
        context["level"] = components[3]
        return context


class FileContextMapping(FactBase):
    """
    Returns structured SELinux file context data for the specified target path prefix
    using the same format as :ref:`selinux.FileContext`.  If there is no mapping, it returns ``{}``
    Note: This fact requires root privileges.
    """

    requires_command = "semanage"
    default = dict

    def command(self, target):
        return "set -o pipefail && semanage fcontext -n -l | (grep '^{0}' || true)".format(target)

    def process(self, output):
        # example output: /etc       all files          system_u:object_r:etc_t:s0 # noqa: SC100
        # but lines at end that won't match: /etc/systemd/system = /usr/lib/systemd/system
        if len(output) != 1:
            return self.default()
        m = re.match(r"^.*\s+(\w+):(\w+):(\w+):(\w+)", output[0])
        return {k: m.group(i) for i, k in enumerate(FIELDS, 1)} if m is not None else self.default()


class SEPorts(FactBase):
    """
    Returns the SELinux 'type' definitions for ``(tcp|udp|dccp|sctp)`` ports.
    Note: This fact requires root privileges.

    .. code:: python
        {
            "tcp": { 22: "ssh_port_t", ...},
            "udp": { ...}
        }
    """

    requires_command = "semanage"
    default = dict
    # example output: amqp_port_t                    tcp      15672, 5671-5672  # noqa: SC100
    _regex = re.compile(r"^([\w_]+)\s+(\w+)\s+([\w\-,\s]+)$")

    def command(self):
        return "semanage port -ln"

    def process(self, output):
        labels = defaultdict(dict)
        for line in output:
            m = SEPorts._regex.match(line)
            if m is None:  # something went wrong
                continue
            if m.group(1) == "unreserved_port_t":  # these cover the entire space
                continue
            for item in m.group(3).split(","):
                item = item.strip()
                if "-" in item:
                    pieces = item.split("-")
                    start, stop = int(pieces[0]), int(pieces[1])
                else:
                    start = stop = int(item)
                labels[m.group(2)].update({port: m.group(1) for port in range(start, stop + 1)})

        return labels


class SEPort(FactBase):
    """
    Returns the SELinux 'type' for the specified protocol ``(tcp|udp|dccp|sctp)`` and port number.
    If no type has been set, ``SEPort`` returns the empty string.
    Note: ``policycoreutils-dev`` must be installed for this to work.
    """

    requires_command = "sepolicy"
    default = str

    def command(self, protocol, port):
        return "(sepolicy network -p {0} 2>/dev/null || true) | grep {1}".format(port, protocol)

    def process(self, output):
        # if type set, first line is specific and second is generic type for port range
        # each rows in the format "22: tcp ssh_port_t 22"

        return output[0].split(" ")[2] if len(output) > 1 else self.default()
