"""
Provides operations to set SELinux file contexts, booleans and port types.
"""
from pyinfra import host
from pyinfra.api import QuoteString, StringCommand, operation
from pyinfra.facts.selinux import FileContext, FileContextMapping, SEBoolean, SEPort, SEPorts
from pyinfra.facts.server import Which


@operation(
    pipeline_facts={"seboolean": "bool_name"},
)
def boolean(bool_name, value, persistent=False):
    """
    Set the specified SELinux boolean to the desired state.

    + boolean: name of an SELinux boolean
    + state: 'on' or 'off'
    + persistent: whether to write updated policy or not

    Note: This operation requires root privileges.

    **Example:**

    .. code:: python

        selinux.boolean(
            name='Allow Apache to connect to LDAP server',
            'httpd_can_network_connect',
            'on',
            persistent=True
        )
    """
    _valid_states = ["on", "off"]

    if value not in _valid_states:
        raise ValueError(
            f'\'value\' must be one of \'{",".join(_valid_states)}\' but found \'{value}\'',
        )

    if host.get_fact(SEBoolean, boolean=bool_name) != value:
        persist = "-P " if persistent else ""
        yield StringCommand("setsebool", f"{persist}{bool_name}", value)
        host.create_fact(SEBoolean, kwargs={"boolean": bool_name}, data=value)
    else:
        host.noop(f"boolean '{bool_name}' already had the value '{value}'")


@operation(
    pipeline_facts={"filecontext": "path"},
)
def file_context(path, se_type):
    """
    Set the SELinux type for the specified path to the specified value.

    + path: the target path (expression) for the context
    + se_type: the SELinux type for the given target

    **Example:**

    .. code:: python

        selinux.file_context(
            name='Allow /foo/bar to be served by the web server',
            '/foo/bar',
            'httpd_sys_content_t'
        )
    """

    current = host.get_fact(FileContext, path=path) or {}
    if se_type != current.get("type", ""):
        yield StringCommand("chcon", "-t", se_type, QuoteString(path))
        host.create_fact(
            FileContext,
            kwargs={"path": path},
            data=dict(current, **{"type": se_type}),
        )
    else:
        host.noop(f"file_context: '{path}' already had type '{se_type}'")


@operation(
    pipeline_facts={"filecontextmapping": "target"},
)
def file_context_mapping(target, se_type=None, present=True):
    """
    Set the SELinux file context mapping for paths matching the target.

    + target: the target path (expression) for the context
    + se_type: the SELinux type for the given target
    + present: whether to add or remove the target -> context mapping

    Note: `file_context` does not change the SELinux file context for existing files
    so `restorecon` may need to be run manually if the file contexts cannot be created
    before the related files.

    **Example:**

    .. code:: python

        selinux.file_context_mapping(
            name='Allow Apache to serve content from the /web directory',
            r'/web(/.*)?',
            se_type='httpd_sys_content_t'
        )
    """
    if present and (se_type is None):
        raise ValueError("se_type must have a valid value if present is set")

    current = host.get_fact(FileContextMapping, target=target)
    kwargs = {"target": target}
    if present:
        option = "-a" if len(current) == 0 else ("-m" if current.get("type") != se_type else "")
        if option != "":
            yield StringCommand("semanage", "fcontext", option, "-t", se_type, QuoteString(target))
            host.create_fact(
                FileContextMapping,
                kwargs=kwargs,
                data=dict(current, **{"type": se_type}),
            )
        else:
            host.noop(f"mapping for '{target}' -> '{se_type}' already present")
    else:
        if len(current) > 0:
            yield StringCommand("semanage", "fcontext", "-d", QuoteString(target))
            host.create_fact(FileContextMapping, kwargs=kwargs, data={})
        else:
            host.noop(f"no existing mapping for '{target}'")


@operation(
    pipeline_facts={"which": "sepolicy"},
)
def port(protocol, port_num, se_type=None, present=True):
    """
    Set the SELinux type for the specified protocol and port.

    + protocol: the protocol: (udp|tcp|sctp|dccp)
    + port: the port
    + se_type: the SELinux type for the given port
    + present: whether to add or remove the SELinux type for the port

    Note: This operation requires root privileges.

    **Example:**

    .. code:: python

        selinux.port(
            name='Allow Apache to provide service on port 2222',
            'tcp',
            2222,
            'http_port_t',
        )
    """

    if present and (se_type is None):
        raise ValueError("se_type must have a valid value if present is set")

    new_type = se_type if present else ""
    direct_get = len(host.get_fact(Which, command=SEPort.requires_command) or "") > 0
    if direct_get:
        current = host.get_fact(SEPort, protocol=protocol, port=port_num)
    else:
        port_info = host.get_fact(SEPorts)
        current = port_info.get(protocol, {}).get(str(port_num), "")

    if present:
        option = "-a" if current == "" else ("-m" if current != se_type else "")
        if option != "":
            yield StringCommand("semanage", "port", option, "-t", se_type, "-p", protocol, port_num)
        else:
            host.noop(f"setype for '{protocol}/{port_num}' is already '{se_type}'")
    else:
        if current != "":
            yield StringCommand("semanage", "port", "-d", "-p", protocol, port_num)
        else:
            host.noop(f"setype for '{protocol}/{port_num}' is already unset")

    if (present and (option != "")) or (not present and (current != "")):
        if direct_get:
            host.create_fact(SEPort, kwargs={"protocol": protocol, "port": port_num}, data=new_type)
        else:
            if protocol not in port_info:
                port_info[protocol] = {}
            port_info[protocol][str(port_num)] = new_type
