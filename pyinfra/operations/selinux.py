"""
Provides operations to set SELinux file contexts, booleans and port types.
"""
from pyinfra import host
from pyinfra.api import QuoteString, StringCommand, operation
from pyinfra.facts.selinux import FileContext, FileContextMapping, SEBoolean, SEPort


@operation
def file_context(path, se_type):
    """
    Set the SELinux type for the specified path .

    + path: the target path (expression) for the context
    + se_type: the SELinux type for the given target

    **Example:**

    .. code:: python

        selinux.file_context(
            name = "Allow /foo/bar to be served by the web server",
            "/foo/bar",
            "httpd_sys_content_t"
        )
    """

    current = host.get_fact(FileContext, path=path)
    if se_type != current.get("type", ""):
        yield StringCommand('chcon', '-t', se_type, QuoteString(path))
        host.create_fact(FileContext, kwargs={"path": path}, data=dict(current, **{"type":se_type}))
    else:
        host.noop(f'file_context: \'{path}\' already had type \'{se_type}\'')


@operation
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

        selinux.file_context(
            name = "Allow Apache to serve content from the /web directory",
            "/web(/.*)?",
            se_type="httpd_sys_content_t"
        )
    """
    if present and (se_type is None):
        raise ValueError(f'se_type must have a valid value if present is set')

    current = host.get_fact(FileContextMapping, target=target)
    kwargs = {"target": target}
    if present:
        op = '-a' if len(current) == 0 else ('-m' if current.get('type') != se_type else '')
        if op != "":
            yield StringCommand('semanage', 'fcontext', op, '-t', se_type, QuoteString(target))
            host.create_fact(FileContextMapping, kwargs=kwargs, data=dict(current, **{"type":se_type}))
        else:
            host.noop(f'mapping for \'{target}\' -> \'{se_type}\' already present')
    else:
        if len(current) > 0:
            yield StringCommand('semanage', 'fcontext', '-d', QuoteString(target))
            host.create_fact(FileContextMapping, kwargs=kwargs,data={})
        else:
            host.noop(f'no existing mapping for \'{target}\'')


@operation
def se_boolean(boolean, state, persistent=False):
    """
    Set the SELinux boolean to the desired state.

    + boolean: name of an SELinux boolean
    + state: 'on' or 'off'
    + persistent: whether to write updated policy or not

    **Example:**

    .. code:: python

        selinux.boolean(
            name = "Allow Apache to connect to TBD",
            "httpd_can_network_connect",
            "on",
            persistent=True
        )
    """
    _valid_states = ["on", "off"]

    if state not in _valid_states:
        raise ValueError(
            f"se_boolean: 'state' must be one of '{','.join(_valid_states)}' but found '{state}'",
        )

    if host.get_fact(SEBoolean, boolean=boolean) != state:
        persist = "-P " if persistent else ""
        yield StringCommand("setsebool", f"{persist}{boolean}", state)
        host.create_fact(SEBoolean, kwargs={"boolean": boolean}, data=state)
    else:
        host.noop(f"seboolean '{boolean}' already had the value '{state}'")



@operation
def se_port(protocol, port, se_type=None, present=True):
    """
    Set the SELinux type for the specified protocol and port.

    + protocol: the protocol: (udp|tcp|sctp|dccp)
    + port: the port
    + se_type: the SELinux type for the given port
    + present: whether to add or remove the SELinux type for the port

    **Example:**

    .. code:: python

        selinux.boolean(
            name = "Allow Apache to connect to LDAP server",
            "httpd_can_network_connect",
            "on",
            persistent=True
        )
    """

    if present and (se_type is None):
        raise ValueError(f'se_port: se_type must have a valid value if present is set')

    kwargs = {'protocol': protocol, 'port': port}
    current = host.get_fact(SEPort, protocol=protocol, port=port)
    if present:
        op = '-a' if current == '' else ('-m' if current != se_type else '')
        if op != '':
            yield StringCommand('semanage', 'port', op, '-t', se_type, '-p', protocol, port)
            host.create_fact(SEPort, kwargs=kwargs, data=se_type,)
        else:
            host.noop(f'setype for \'{protocol}/{port}\' is already \'{se_type}\'')
    else:
        if current != '':
            yield StringCommand('semanage', 'port', '-d', '-p', protocol, port)
            host.create_fact(SEPort, kwargs=kwargs, data='')
        else:
            host.noop(f'setype for \'{protocol}/{port}\' is already unset')
