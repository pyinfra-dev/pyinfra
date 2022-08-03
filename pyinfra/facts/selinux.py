import re

from pyinfra.api import FactBase

FIELDS = ["user", "role", "type", "level"] # order is significant, do not change

class FileContext(FactBase):
    """
    Returns structured SELinux file context data for a specified file.

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
    """

    requires_command = "semanage"
    default = dict

    def command(self, target):
        return "semanage fcontext -n -l | grep '^ {0}'".format(target)

    def process(self, output):
        # /etc                                               all files          system_u:object_r:etc_t:s0
        if len(output) != 1:
            return self.default()
        m = re.match(r"^.*\s+(\w+):(\w+):(\w+):(\w+)", output[0])
        return {k: m.group(i) for i,k in enumerate(FIELDS, 1)} if m is not None else self.default()


class SEBoolean(FactBase):
    """
    Returns the status of a SELinux Boolean as a string (``on`` or ``off``)
    """

    requires_command = "getsebool"
    default = lambda x: ""

    def command(self, boolean):
        return "getsebool {0}".format(boolean)

    def process(self, output):
        components = output[0].split(" --> ")
        return components[1]


class SEPort(FactBase):
    """
    Returns the SELinux 'type' for the specified protocol ``(tcp|udp|dccp|sctp)`` and port number.
    """

    requires_command = "sepolicy"
    default = lambda x: ""

    def command(self, protocol, port):
        return "(sepolicy network -p {0} 2>/dev/null || true) | grep {1}".format(port, protocol)

    def process(self, output):
        # if type set, first line is specific and second is generic type for port range
        # each rows in the format "22: tcp ssh_port_t 22"
        if len(output) < 1:
            return self.default()

        return output[0].split(" ")[2] if len(output) > 0 else self.default()

