"""
The server module takes care of os-level state. Targets POSIX compatibility, tested on
Linux/BSD.
"""

import shlex
from io import StringIO
from itertools import filterfalse, tee
from os import path
from time import sleep

from pyinfra import host, logger, state
from pyinfra.api import FunctionCommand, OperationError, StringCommand, operation
from pyinfra.api.util import try_int
from pyinfra.connectors.util import remove_any_sudo_askpass_file
from pyinfra.facts.files import Directory, FindInFile, Link
from pyinfra.facts.server import (
    Crontab,
    Groups,
    Hostname,
    KernelModules,
    Locales,
    Mounts,
    Os,
    Sysctl,
    Users,
    Which,
)

from . import (
    apk,
    apt,
    brew,
    bsdinit,
    dnf,
    files,
    openrc,
    pacman,
    pkg,
    systemd,
    sysvinit,
    upstart,
    xbps,
    yum,
    zypper,
)
from .util.files import chmod, sed_replace


@operation(is_idempotent=False)
def reboot(delay=10, interval=1, reboot_timeout=300):
    """
    Reboot the server and wait for reconnection.

    + delay: number of seconds to wait before attempting reconnect
    + interval: interval (s) between reconnect attempts
    + reboot_timeout: total time before giving up reconnecting

    **Example:**

    .. code:: python

        server.reboot(
            name="Reboot the server and wait to reconnect",
            delay=60,
            reboot_timeout=600,
        )
    """

    # Remove this now, before we reboot the server - if the reboot fails (expected or
    # not) we'll error if we don't clean this up now. Will simply be re-uploaded if
    # needed later.
    def remove_any_askpass_file(state, host):
        remove_any_sudo_askpass_file(host)

    yield FunctionCommand(remove_any_askpass_file, (), {})

    yield StringCommand("reboot", success_exit_codes=[0, -1])  # -1 being error/disconnected

    def wait_and_reconnect(state, host):  # pragma: no cover
        sleep(delay)
        max_retries = round(reboot_timeout / interval)

        host.connection = None  # remove the connection object
        retries = 0

        while True:
            host.connect(show_errors=False)
            if host.connection:
                break

            if retries > max_retries:
                raise Exception(
                    ("Server did not reboot in time (reboot_timeout={0}s)").format(reboot_timeout),
                )

            sleep(interval)
            retries += 1

    yield FunctionCommand(wait_and_reconnect, (), {})


@operation(is_idempotent=False)
def wait(port: int):
    """
    Waits for a port to come active on the target machine. Requires netstat, checks every
    second.

    + port: port number to wait for

    **Example:**

    .. code:: python

        server.wait(
            name="Wait for webserver to start",
            port=80,
        )
    """

    yield r"""
        while ! (netstat -an | grep LISTEN | grep -e "\.{0}" -e ":{0}"); do
            echo "waiting for port {0}..."
            sleep 1
        done
    """.format(
        port,
    )


@operation(is_idempotent=False)
def shell(commands):
    """
    Run raw shell code on server during a deploy. If the command would
    modify data that would be in a fact, the fact would not be updated
    since facts are only run at the start of a deploy.

    + commands: command or list of commands to execute on the remote server

    **Example:**

    .. code:: python

        server.shell(
            name="Run lxd auto init",
            commands=["lxd init --auto"],
        )
    """

    # Ensure we have a list
    if isinstance(commands, str):
        commands = [commands]

    for command in commands:
        yield command


@operation(is_idempotent=False)
def script(src, args=()):
    """
    Upload and execute a local script on the remote host.

    + src: local script filename to upload & execute
    + args: iterable to pass as arguments to the script

    **Example:**

    .. code:: python

        # Note: This assumes there is a file in files/hello.bash locally.
        server.script(
            name="Hello",
            src="files/hello.bash",
        )

        # Example passing arguments to the script
        server.script(
            name="Hello",
            src="files/hello.bash",
            args=("do-something", "with-this"),
        )
    """

    temp_file = state.get_temp_filename()
    yield from files.put(src, temp_file)

    yield chmod(temp_file, "+x")
    yield StringCommand(temp_file, *args)


@operation(is_idempotent=False)
def script_template(src, args=(), **data):
    """
    Generate, upload and execute a local script template on the remote host.

    + src: local script template filename

    **Example:**

    .. code:: python

        # Example showing how to pass python variable to a script template file.
        # The .j2 file can use `{{ some_var }}` to be interpolated.
        # To see output need to run pyinfra with '-v'
        # Note: This assumes there is a file in templates/hello2.bash.j2 locally.
        some_var = 'blah blah blah '
        server.script_template(
            name="Hello from script",
            src="templates/hello2.bash.j2",
            some_var=some_var,
        )
    """

    temp_file = state.get_temp_filename("{0}{1}".format(src, data))
    yield from files.template(src, temp_file, **data)

    yield chmod(temp_file, "+x")
    yield StringCommand(temp_file, *args)


@operation
def modprobe(module, present=True, force=False):
    """
    Load/unload kernel modules.

    + module: name of the module to manage
    + present: whether the module should be loaded or not
    + force: whether to force any add/remove modules

    **Example:**

    .. code:: python

        server.modprobe(
            name="Silly example for modprobe",
            module="floppy",
        )
    """
    list_value = [module] if isinstance(module, str) else module

    # NOTE: https://docs.python.org/3/library/itertools.html#itertools-recipes
    def partition(predicate, iterable):
        t1, t2 = tee(iterable)
        return list(filter(predicate, t2)), list(filterfalse(predicate, t1))

    modules = host.get_fact(KernelModules)
    present_mods, missing_mods = partition(lambda mod: mod in modules, list_value)

    args = ""
    if force:
        args = " -f"

    # Module is loaded and we don't want it?
    if not present and present_mods:
        yield "modprobe{0} -r -a {1}".format(args, " ".join(present_mods))
        for mod in present_mods:
            modules.pop(mod)

    # Module isn't loaded and we want it?
    elif present and missing_mods:
        yield "modprobe{0} -a {1}".format(args, " ".join(missing_mods))
        for mod in missing_mods:
            modules[mod] = {}

    else:
        host.noop(
            "{0} {1} {2} {3}".format(
                "modules" if len(list_value) > 1 else "module",
                "/".join(list_value),
                "are" if len(list_value) > 1 else "is",
                "loaded" if present else "not loaded",
            ),
        )


@operation
def mount(
    path,
    mounted=True,
    options=None,
    device=None,
    fs_type=None,
    # TODO: do we want to manage fstab here?
    # update_fstab=False,
):
    """
    Manage mounted filesystems.

    + path: the path of the mounted filesystem
    + mounted: whether the filesystem should be mounted
    + options: the mount options

    Options:
        If the currently mounted filesystem does not have all of the provided
        options it will be remounted with the options provided.

    ``/etc/fstab``:
        This operation does not attempt to modify the on disk fstab file - for
        that you should use the `files.line operation <./files.html#files-line>`_.
    """
    options = options or []
    options_string = ",".join(options)

    mounts = host.get_fact(Mounts)
    is_mounted = path in mounts

    # Want mount but don't have?
    if mounted and not is_mounted:
        args = []
        if fs_type:
            args.extend(["-t", fs_type])
        if options_string:
            args.extend(["-o", options_string])
        if device:
            args.append(device)
        args.append(path)

        yield StringCommand("mount", *args)
        # Should we update facts with fs_type, device, etc?
        mounts[path] = {"options": options}

    # Want no mount but mounted?
    elif mounted is False and is_mounted:
        yield "umount {0}".format(path)
        mounts.pop(path)

    # Want mount and is mounted! Check the options
    elif is_mounted and mounted and options:
        mounted_options = mounts[path]["options"]
        needed_options = set(options) - set(mounted_options)
        if needed_options:
            yield "mount -o remount,{0} {1}".format(options_string, path)
            mounts[path]["options"] = options

    else:
        host.noop(
            "filesystem {0} is {1}".format(
                path,
                "mounted" if mounted else "not mounted",
            ),
        )


@operation
def hostname(hostname, hostname_file=None):
    """
    Set the system hostname using ``hostnamectl`` or ``hostname`` on older systems.

    + hostname: the hostname that should be set
    + hostname_file: the file that permanently sets the hostname

    Hostname file:
        The hostname file only matters no systems that do not have ``hostnamectl``,
        which is part of ``systemd``.

        By default pyinfra will auto detect this by targeting ``/etc/hostname``
        on Linux and ``/etc/myname`` on OpenBSD.

        To completely disable writing the hostname file, set ``hostname_file=False``.

    **Example:**

    .. code:: python

        server.hostname(
            name="Set the hostname",
            hostname="server1.example.com",
        )
    """

    current_hostname = host.get_fact(Hostname)

    if host.get_fact(Which, command="hostnamectl"):
        if current_hostname != hostname:
            yield "hostnamectl set-hostname {0}".format(hostname)
            host.create_fact(Hostname, data=hostname)
        else:
            host.noop("hostname is set")
        return

    if hostname_file is None:
        os = host.get_fact(Os)

        if os == "Linux":
            hostname_file = "/etc/hostname"
        elif os == "OpenBSD":
            hostname_file = "/etc/myname"

    if current_hostname != hostname:
        yield "hostname {0}".format(hostname)
        host.create_fact(Hostname, data=hostname)
    else:
        host.noop("hostname is set")

    if hostname_file:
        # Create a whole new hostname file
        file = StringIO("{0}\n".format(hostname))

        # And ensure it exists
        yield from files.put(file, hostname_file)


@operation
def sysctl(
    key,
    value,
    persist=False,
    persist_file="/etc/sysctl.conf",
):
    """
    Edit sysctl configuration.

    + key: name of the sysctl setting to ensure
    + value: the value or list of values the sysctl should be
    + persist: whether to write this sysctl to the config
    + persist_file: file to write the sysctl to persist on reboot

    **Example:**

    .. code:: python

        server.sysctl(
            name="Change the fs.file-max value",
            key="fs.file-max",
            value=100000,
            persist=True,
        )
    """

    string_value = " ".join(["{0}".format(v) for v in value]) if isinstance(value, list) else value

    value = [try_int(v) for v in value] if isinstance(value, list) else try_int(value)

    existing_sysctls = host.get_fact(Sysctl)

    existing_value = existing_sysctls.get(key)
    if not existing_value or existing_value != value:
        yield "sysctl {0}='{1}'".format(key, string_value)
        existing_sysctls[key] = value
    else:
        host.noop("sysctl {0} is set to {1}".format(key, string_value))

    if persist:
        yield from files.line(
            path=persist_file,
            line="{0}[[:space:]]*=[[:space:]]*{1}".format(key, string_value),
            replace="{0} = {1}".format(key, string_value),
        )


@operation
def service(
    service,
    running=True,
    restarted=False,
    reloaded=False,
    command=None,
    enabled=None,
):
    """
    Manage the state of services. This command checks for the presence of all the
    Linux init systems ``pyinfra`` can handle and executes the relevant operation.

    + service: name of the service to manage
    + running: whether the service should be running
    + restarted: whether the service should be restarted
    + reloaded: whether the service should be reloaded
    + command: custom command execute
    + enabled: whether this service should be enabled/disabled on boot

    **Example:**

    .. code:: python

        server.service(
            name="Enable open-vm-tools service",
            service="open-vm-tools",
            enabled=True,
        )
    """

    if host.get_fact(Which, command="systemctl"):
        service_operation = systemd.service

    elif host.get_fact(Which, command="rc-service"):
        service_operation = openrc.service

    elif host.get_fact(Which, command="initctl"):
        service_operation = upstart.service

    elif (
        host.get_fact(Which, command="service")
        or host.get_fact(Link, path="/etc/init.d")
        or host.get_fact(Directory, path="/etc/init.d")
    ):
        service_operation = sysvinit.service

    # NOTE: important that we are not Linux here because /etc/rc.d will exist but checking it's
    # contents may trigger things (like a reboot: https://github.com/Fizzadar/pyinfra/issues/819)
    elif host.get_fact(Os) != "Linux" and host.get_fact(Directory, path="/etc/rc.d"):
        service_operation = bsdinit.service

    else:
        raise OperationError(
            ("No init system found " "(no systemctl, initctl, /etc/init.d or /etc/rc.d found)"),
        )

    yield from service_operation(
        service,
        running=running,
        restarted=restarted,
        reloaded=reloaded,
        command=command,
        enabled=enabled,
    )


@operation
def packages(
    packages,
    present=True,
):
    """
    Add or remove system packages. This command checks for the presence of all the
    system package managers ``pyinfra`` can handle and executes the relevant operation.

    + packages: list of packages to ensure
    + present: whether the packages should be installed

    **Example:**

    .. code:: python

        server.packages(
            name="Install Vim and vimpager",
            packages=["vimpager", "vim"],
        )
    """

    # TODO: improve this - use LinuxDistribution fact + mapping with fallback below?
    # Here to be preferred on openSUSE which also provides aptitude
    # See: https://github.com/Fizzadar/pyinfra/issues/799
    if host.get_fact(Which, command="zypper"):
        package_operation = zypper.packages

    elif host.get_fact(Which, command="apk"):
        package_operation = apk.packages

    elif host.get_fact(Which, command="apt"):
        package_operation = apt.packages

    elif host.get_fact(Which, command="brew"):
        package_operation = brew.packages

    elif host.get_fact(Which, command="dnf"):
        package_operation = dnf.packages

    elif host.get_fact(Which, command="pacman"):
        package_operation = pacman.packages

    elif host.get_fact(Which, command="xbps"):
        package_operation = xbps.packages

    elif host.get_fact(Which, command="yum"):
        package_operation = yum.packages

    elif host.get_fact(Which, command="pkg") or host.get_fact(Which, command="pkg_add"):
        package_operation = pkg.packages

    else:
        raise OperationError(
            (
                "No system package manager found "
                "(no apk, apt, brew, dnf, pacman, pkg, xbps, yum or zypper found)"
            ),
        )

    yield from package_operation(packages=packages, present=present)


@operation
def crontab(
    command,
    present=True,
    user=None,
    cron_name=None,
    minute="*",
    hour="*",
    month="*",
    day_of_week="*",
    day_of_month="*",
    special_time=None,
    interpolate_variables=False,
):
    """
    Add/remove/update crontab entries.

    + command: the command for the cron
    + present: whether this cron command should exist
    + user: the user whose crontab to manage
    + cron_name: name the cronjob so future changes to the command will overwrite
    + minute: which minutes to execute the cron
    + hour: which hours to execute the cron
    + month: which months to execute the cron
    + day_of_week: which day of the week to execute the cron
    + day_of_month: which day of the month to execute the cron
    + special_time: cron "nickname" time (@reboot, @daily, etc), overrides others
    + interpolate_variables: whether to interpolate variables in ``command``

    Cron commands:
        Unless ``name`` is specified the command is used to identify crontab entries.
        This means commands must be unique within a given users crontab. If you require
        multiple identical commands, provide a different name argument for each.

    Special times:
        When provided, ``special_time`` will be used instead of any values passed in
        for ``minute``/``hour``/``month``/``day_of_week``/``day_of_month``.

    **Example:**

    .. code:: python

        # simple example for a crontab
        server.crontab(
            name="Backup /etc weekly",
            command="/bin/tar cf /tmp/etc_bup.tar /etc",
            name="backup_etc",
            day_of_week=0,
            hour=1,
            minute=0,
        )
    """

    def comma_sep(value):
        if isinstance(value, (list, tuple)):
            return ",".join("{0}".format(v) for v in value)
        return value

    minute = comma_sep(minute)
    hour = comma_sep(hour)
    month = comma_sep(month)
    day_of_week = comma_sep(day_of_week)
    day_of_month = comma_sep(day_of_month)

    crontab = host.get_fact(Crontab, user=user)
    name_comment = "# pyinfra-name={0}".format(cron_name)

    existing_crontab = crontab.get(command)
    existing_crontab_command = command
    existing_crontab_match = command

    if not existing_crontab and cron_name:  # find the crontab by name if provided
        for cmd, details in crontab.items():
            if name_comment in details["comments"]:
                existing_crontab = details
                existing_crontab_match = cmd
                existing_crontab_command = cmd

    exists = existing_crontab is not None

    edit_commands = []
    temp_filename = state.get_temp_filename()

    if special_time:
        new_crontab_line = "{0} {1}".format(special_time, command)
    else:
        new_crontab_line = "{minute} {hour} {day_of_month} {month} {day_of_week} {command}".format(
            minute=minute,
            hour=hour,
            day_of_month=day_of_month,
            month=month,
            day_of_week=day_of_week,
            command=command,
        )

    existing_crontab_match = ".*{0}.*".format(existing_crontab_match)

    # Don't want the cron and it does exist? Remove the line
    if not present and exists:
        edit_commands.append(
            sed_replace(
                temp_filename,
                existing_crontab_match,
                "",
                interpolate_variables=interpolate_variables,
            ),
        )

    # Want the cron but it doesn't exist? Append the line
    elif present and not exists:
        if cron_name:
            if crontab:  # append a blank line if cron entries already exist
                edit_commands.append("echo '' >> {0}".format(temp_filename))
            edit_commands.append(
                "echo {0} >> {1}".format(
                    shlex.quote(name_comment),
                    temp_filename,
                ),
            )

        edit_commands.append(
            "echo {0} >> {1}".format(
                shlex.quote(new_crontab_line),
                temp_filename,
            ),
        )

    # We have the cron and it exists, do it's details? If not, replace the line
    elif present and exists:
        if any(
            (
                special_time != existing_crontab.get("special_time"),
                minute != existing_crontab.get("minute"),
                hour != existing_crontab.get("hour"),
                month != existing_crontab.get("month"),
                day_of_week != existing_crontab.get("day_of_week"),
                day_of_month != existing_crontab.get("day_of_month"),
                existing_crontab_command != command,
            ),
        ):
            edit_commands.append(
                sed_replace(
                    temp_filename,
                    existing_crontab_match,
                    new_crontab_line,
                    interpolate_variables=interpolate_variables,
                ),
            )

    if edit_commands:
        crontab_args = []
        if user:
            crontab_args.append("-u {0}".format(user))

        # List the crontab into a temporary file if it exists
        if crontab:
            yield "crontab -l {0} > {1}".format(" ".join(crontab_args), temp_filename)

        # Now yield any edits
        for edit_command in edit_commands:
            yield edit_command

        # Finally, use the tempfile to write a new crontab
        yield "crontab {0} {1}".format(" ".join(crontab_args), temp_filename)

        # Update the crontab fact
        if present:
            crontab[command] = {
                "special_time": special_time,
                "minute": minute,
                "hour": hour,
                "month": month,
                "day_of_week": day_of_week,
                "day_of_month": day_of_month,
                "comments": [cron_name] if cron_name else [],
            }
        else:
            crontab.pop(command)
    else:
        host.noop(
            "crontab {0} {1}".format(
                command,
                "exists" if present else "does not exist",
            ),
        )


@operation
def group(group, present=True, system=False, gid=None):
    """
    Add/remove system groups.

    + group: name of the group to ensure
    + present: whether the group should be present or not
    + system: whether to create a system group
    + gid: use a specific groupid number

    System users:
        System users don't exist on BSD, so the argument is ignored for BSD targets.

    **Examples:**

    .. code:: python

        server.group(
            name="Create docker group",
            group="docker",
        )

        # multiple groups
        for group in ["wheel", "lusers"]:
            server.group(
                name=f"Create the group {group}",
                group=group,
            )
    """

    groups = host.get_fact(Groups)
    os_type = host.get_fact(Os)
    is_present = group in groups

    # Group exists but we don't want them?
    if not present and is_present:
        if os_type == "FreeBSD":
            yield "pw groupdel -n {0}".format(group)
        else:
            yield "groupdel {0}".format(group)
        groups.remove(group)

    # Group doesn't exist and we want it?
    elif present and not is_present:
        args = []

        # BSD doesn't do system users
        if system and "BSD" not in host.get_fact(Os):
            args.append("-r")

        if os_type == "FreeBSD":
            args.append("-n {0}".format(group))
        else:
            args.append(group)

        if gid:
            if os_type == "FreeBSD":
                args.append("-g {0}".format(gid))
            else:
                args.append("--gid {0}".format(gid))

        # Groups are often added by other operations (package installs), so check
        # for the group at runtime before adding.
        group_add_command = "groupadd"
        if os_type == "FreeBSD":
            group_add_command = "pw groupadd"
        yield "grep '^{0}:' /etc/group || {2} {1}".format(group, " ".join(args), group_add_command)
        groups.append(group)


@operation
def user_authorized_keys(
    user,
    public_keys,
    group=None,
    delete_keys=False,
    authorized_key_directory=None,
    authorized_key_filename=None,
):
    """
    Manage `authorized_keys` of system users.

    + user: name of the user to ensure
    + public_keys: list of public keys to attach to this user, ``home`` must be specified
    + group: the users primary group
    + delete_keys: whether to remove any keys not specified in ``public_keys``

    Public keys:
        These can be provided as strings containing the public key or as a path to
        a public key file which ``pyinfra`` will read.

    **Examples:**

    .. code:: python

        server.user_authorized_keys(
            name="Ensure user has a public key",
            user="kevin",
            public_keys=["ed25519..."],
        )
    """
    if not authorized_key_directory:
        authorized_key_directory = f"/home/{user}/.ssh/"
    if not authorized_key_filename:
        authorized_key_filename = "authorized_keys"

    if isinstance(public_keys, str):
        public_keys = [public_keys]

    def read_any_pub_key_file(key):
        try_path = key
        if state.cwd:
            try_path = path.join(state.cwd, key)

        if path.exists(try_path):
            with open(try_path, "r") as f:
                return f.read().strip()

        return key

    public_keys = list(map(read_any_pub_key_file, public_keys))

    # Ensure .ssh directory
    # note that this always outputs commands unless the SSH user has access to the
    # authorized_keys file, ie the SSH user is the user defined in this function
    yield from files.directory(
        authorized_key_directory,
        user=user,
        group=group or user,
        mode=700,
    )

    authorized_key_file = f"{authorized_key_directory}/{authorized_key_filename}"

    if delete_keys:
        # Create a whole new authorized_keys file
        keys_file = StringIO(
            "{0}\n".format(
                "\n".join(public_keys),
            ),
        )

        # And ensure it exists
        yield from files.put(
            src=keys_file,
            dest=authorized_key_file,
            user=user,
            group=group or user,
            mode=600,
        )

    else:
        # Ensure authorized_keys exists
        yield from files.file(
            path=authorized_key_file,
            user=user,
            group=group or user,
            mode=600,
        )

        # And every public key is present
        for key in public_keys:
            yield from files.line(path=authorized_key_file, line=key, ensure_newline=True)


@operation
def user(
    user,
    present=True,
    home=None,
    shell=None,
    group=None,
    groups=None,
    public_keys=None,
    delete_keys=False,
    ensure_home=True,
    create_home=False,
    system=False,
    uid=None,
    comment=None,
    add_deploy_dir=True,
    unique=True,
):
    """
    Add/remove/update system users & their ssh `authorized_keys`.

    + user: name of the user to ensure
    + present: whether this user should exist
    + home: the users home directory
    + shell: the users shell
    + group: the users primary group
    + groups: the users secondary groups
    + public_keys: list of public keys to attach to this user, ``home`` must be specified
    + delete_keys: whether to remove any keys not specified in ``public_keys``
    + ensure_home: whether to ensure the ``home`` directory exists
    + create_home: whether to new user create home directories from the system skeleton
    + system: whether to create a system account
    + uid: use a specific userid number
    + comment: the user GECOS comment
    + add_deploy_dir: any public_key filenames are relative to the deploy directory
    + unique: prevent creating users with duplicate UID

    Home directory:
        When ``ensure_home`` or ``public_keys`` are provided, ``home`` defaults to
        ``/home/{name}``. When ``create_home`` is ``True`` any newly created users
        will be created with the ``-m`` flag to build a new home directory from the
        systems skeleton directory.

    Public keys:
        These can be provided as strings containing the public key or as a path to
        a public key file which ``pyinfra`` will read.

    **Examples:**

    .. code:: python

        server.user(
            name="Ensure user is removed",
            user="kevin",
            present=False,
        )

        server.user(
            name="Ensure myweb user exists",
            user="myweb",
            shell="/bin/bash",
        )

        # multiple users
        for user in ["kevin", "bob"]:
            server.user(
                name=f"Ensure user {user} is removed",
                user=user,
                present=False,
            )
    """

    users = host.get_fact(Users)
    existing_groups = host.get_fact(Groups)
    existing_user = users.get(user)
    os_type = host.get_fact(Os)
    if groups is None:
        groups = []

    if home is None:
        home = "/home/{0}".format(user)
        if existing_user:
            home = existing_user.get("home", home)

    # User not wanted?
    if not present:
        if existing_user:
            if os_type == "FreeBSD":
                yield "pw userdel -n {0}".format(user)
            else:
                yield "userdel {0}".format(user)
            users.pop(user)
        return

    # User doesn't exist but we want them?
    if present and existing_user is None:
        # Fix the case where a group of the same name already exists, tell useradd to use this
        # group rather than failing trying to create it.
        if not group and user in existing_groups:
            group = user

        # Create the user w/home/shell
        args = []

        if home:
            args.append("-d {0}".format(home))

        if shell:
            args.append("-s {0}".format(shell))

        if group:
            args.append("-g {0}".format(group))

        if groups:
            args.append("-G {0}".format(",".join(groups)))

        if system and "BSD" not in host.get_fact(Os):
            args.append("-r")

        if uid:
            if os_type == "FreeBSD":
                args.append("-u {0}".format(uid))
            else:
                args.append("--uid {0}".format(uid))

        if comment:
            args.append("-c '{0}'".format(comment))

        if not unique:
            args.append("-o")

        if create_home:
            args.append("-m")

        # Users are often added by other operations (package installs), so check
        # for the user at runtime before adding.

        add_user_command = "useradd"
        if os_type == "FreeBSD":
            add_user_command = "pw useradd"
            yield "grep '^{2}:' /etc/passwd || {0} -n {2} {1}".format(
                add_user_command,
                " ".join(args),
                user,
            )
        else:
            yield "grep '^{2}:' /etc/passwd || {0} {1} {2}".format(
                add_user_command,
                " ".join(args),
                user,
            )
        users[user] = {
            "comment": comment,
            "home": home,
            "shell": shell,
            "group": group,
            "groups": groups,
        }

    # User exists and we want them, check home/shell/keys
    else:
        args = []

        # Check homedir
        if home and existing_user["home"] != home:
            args.append("-d {0}".format(home))

        # Check shell
        if shell and existing_user["shell"] != shell:
            args.append("-s {0}".format(shell))

        # Check primary group
        if group and existing_user["group"] != group:
            args.append("-g {0}".format(group))

        # Check secondary groups, if defined
        if groups and set(existing_user["groups"]) != set(groups):
            args.append("-G {0}".format(",".join(groups)))

        if comment and existing_user["comment"] != comment:
            args.append("-c '{0}'".format(comment))

        # Need to mod the user?
        if args:
            if os_type == "FreeBSD":
                yield "pw usermod -n {1} {0}".format(" ".join(args), user)
            else:
                yield "usermod {0} {1}".format(" ".join(args), user)
            if comment:
                existing_user["comment"] = comment
            if home:
                existing_user["home"] = home
            if shell:
                existing_user["shell"] = shell
            if group:
                existing_user["group"] = group
            if groups:
                existing_user["groups"] = groups

    # Ensure home directory ownership
    if ensure_home:
        yield from files.directory(
            home,
            user=user,
            group=group or user,
            # Don't fail if the home directory exists as a link
            _no_fail_on_link=True,
        )

    # Add SSH keys
    if public_keys is not None:
        yield from user_authorized_keys(
            user,
            public_keys,
            group=group,
            delete_keys=delete_keys,
            authorized_key_directory="{0}/.ssh".format(home),
            authorized_key_filename=None,
        )


@operation
def locale(
    locale,
    present=True,
):
    """
    Enable/Disable locale.

    + locale: name of the locale to enable/disable
    + present: whether this locale should be present or not

    **Examples:**

    .. code:: python

        server.locale(
            name="Ensure en_GB.UTF-8 locale is not present",
            locale="en_GB.UTF-8",
            present=False,
        )

        server.locale(
            name="Ensure en_GB.UTF-8 locale is present",
            locale="en_GB.UTF-8",
        )

    """

    locales = host.get_fact(Locales)

    logger.debug("Enabled locales: {0}".format(locales))

    locales_definitions_file = "/etc/locale.gen"

    # Find the matching line in /etc/locale.gen
    matching_lines = host.get_fact(
        FindInFile, path=locales_definitions_file, pattern=rf"^.*{locale}[[:space:]]\+.*$"
    )

    if not matching_lines:
        raise OperationError(f"Locale {locale} not found in {locales_definitions_file}")

    if len(matching_lines) > 1:
        raise OperationError(f"Multiple locales matches for {locale} in {locales_definitions_file}")

    matching_line = matching_lines[0]

    # Remove locale
    if not present and locale in locales:
        logger.debug(f"Removing locale {locale}")

        yield from files.line(
            path=locales_definitions_file, line=f"^{matching_line}$", replace=f"# {matching_line}"
        )

        yield "locale-gen"

    # Add locale
    if present and locale not in locales:
        logger.debug(f"Adding locale {locale}")

        yield from files.replace(
            path=locales_definitions_file,
            text=f"^{matching_line}$",
            replace=f"{matching_line}".replace("# ", ""),
        )

        yield "locale-gen"
