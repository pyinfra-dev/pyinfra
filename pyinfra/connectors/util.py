import shlex
from getpass import getpass
from socket import timeout as timeout_error
from subprocess import PIPE, Popen

import click
import gevent
from gevent.queue import Queue

from pyinfra import logger
from pyinfra.api import MaskString, QuoteString, StringCommand
from pyinfra.api.util import memoize

SUDO_ASKPASS_ENV_VAR = "PYINFRA_SUDO_PASSWORD"
SUDO_ASKPASS_COMMAND = r"""
temp=$(mktemp "${{TMPDIR:=/tmp}}/pyinfra-sudo-askpass-XXXXXXXXXXXX")
cat >"$temp"<<'__EOF__'
#!/bin/sh
printf '%s\n' "${0}"
__EOF__
chmod 755 "$temp"
echo "$temp"
""".format(
    SUDO_ASKPASS_ENV_VAR,
)


def read_buffer(type_, io, output_queue, print_output=False, print_func=None):
    """
    Reads a file-like buffer object into lines and optionally prints the output.
    """

    def _print(line):
        if print_func:
            line = print_func(line)

        click.echo(line, err=True)

    for line in io:
        # Handle local Popen shells returning list of bytes, not strings
        if not isinstance(line, str):
            line = line.decode("utf-8")

        line = line.rstrip("\n")
        output_queue.put((type_, line))

        if print_output:
            _print(line)


def execute_command_with_sudo_retry(host, command_kwargs, execute_command):
    return_code, combined_output = execute_command()

    if return_code != 0 and combined_output:
        last_line = combined_output[-1][1]
        if last_line.strip() == "sudo: a password is required":
            command_kwargs["use_sudo_password"] = True  # ask for the password
            return_code, combined_output = execute_command()

    return return_code, combined_output


def run_local_process(
    command,
    stdin=None,
    timeout=None,
    print_output=False,
    print_prefix=None,
):
    process = Popen(command, shell=True, stdout=PIPE, stderr=PIPE, stdin=PIPE)

    if stdin:
        write_stdin(stdin, process.stdin)

    combined_output = read_buffers_into_queue(
        process.stdout,
        process.stderr,
        timeout=timeout,
        print_output=print_output,
        print_prefix=print_prefix,
    )

    logger.debug("--> Waiting for exit status...")
    process.wait()
    logger.debug("--> Command exit status: %i", process.returncode)

    # Close any open file descriptors
    process.stdout.close()
    process.stderr.close()

    return process.returncode, combined_output


def read_buffers_into_queue(
    stdout_buffer,
    stderr_buffer,
    timeout,
    print_output,
    print_prefix,
):
    output_queue = Queue()

    # Iterate through outputs to get an exit status and generate desired list
    # output, done in two greenlets so stdout isn't printed before stderr. Not
    # attached to state.pool to avoid blocking it with 2x n-hosts greenlets.
    stdout_reader = gevent.spawn(
        read_buffer,
        "stdout",
        stdout_buffer,
        output_queue,
        print_output=print_output,
        print_func=lambda line: "{0}{1}".format(print_prefix, line),
    )
    stderr_reader = gevent.spawn(
        read_buffer,
        "stderr",
        stderr_buffer,
        output_queue,
        print_output=print_output,
        print_func=lambda line: "{0}{1}".format(
            print_prefix,
            click.style(line, "red"),
        ),
    )

    # Wait on output, with our timeout (or None)
    greenlets = gevent.wait((stdout_reader, stderr_reader), timeout=timeout)

    # Timeout doesn't raise an exception, but gevent.wait returns the greenlets
    # which did complete. So if both haven't completed, we kill them and fail
    # with a timeout.
    if len(greenlets) != 2:
        stdout_reader.kill()
        stderr_reader.kill()

        raise timeout_error()

    return list(output_queue.queue)


def split_combined_output(combined_output):
    stdout = []
    stderr = []

    for type_, line in combined_output:
        if type_ == "stdout":
            stdout.append(line)
        elif type_ == "stderr":
            stderr.append(line)
        else:  # pragma: no cover
            raise ValueError("Incorrect output line type: {0}".format(type_))

    return stdout, stderr


def write_stdin(stdin, buffer):
    if hasattr(stdin, "readlines"):
        stdin = stdin.readlines()
    if not isinstance(stdin, (list, tuple)):
        stdin = [stdin]

    for line in stdin:
        if not line.endswith("\n"):
            line = "{0}\n".format(line)
        line = line.encode()
        buffer.write(line)
    buffer.close()


def _get_sudo_password(host, use_sudo_password):
    if not host.connector_data.get("sudo_askpass_path"):
        _, stdout, _ = host.run_shell_command(SUDO_ASKPASS_COMMAND)
        host.connector_data["sudo_askpass_path"] = shlex.quote(stdout[0])

    if use_sudo_password is True:
        sudo_password = host.connector_data.get("sudo_password")
        if not sudo_password:
            sudo_password = getpass("{0}sudo password: ".format(host.print_prefix))
            host.connector_data["sudo_password"] = sudo_password
        sudo_password = sudo_password
    elif callable(use_sudo_password):
        sudo_password = use_sudo_password()
    else:
        sudo_password = use_sudo_password

    return shlex.quote(sudo_password)


def remove_any_sudo_askpass_file(host):
    sudo_askpass_path = host.connector_data.get("sudo_askpass_path")
    if sudo_askpass_path:
        host.run_shell_command("rm -f {0}".format(sudo_askpass_path))
        host.connector_data["sudo_askpass_path"] = None


@memoize
def _show_use_su_login_warning():
    logger.warning(
        (
            "Using `use_su_login` may not work: "
            "some systems (MacOS, OpenBSD) ignore the flag when executing a command, "
            "use `sudo` + `use_sudo_login` instead."
        ),
    )


def make_unix_command_for_host(state, host, *command_args, **command_kwargs):
    use_sudo_password = command_kwargs.pop("use_sudo_password", None)
    if use_sudo_password:
        command_kwargs["sudo_password"] = _get_sudo_password(host, use_sudo_password)
        command_kwargs["sudo_askpass_path"] = host.connector_data.get("sudo_askpass_path")

    return make_unix_command(*command_args, **command_kwargs)


def make_unix_command(
    command,
    env=None,
    chdir=None,
    shell_executable="sh",
    # Su config
    su_user=None,
    use_su_login=False,
    su_shell=None,
    preserve_su_env=False,
    # Sudo config
    sudo=False,
    sudo_user=None,
    use_sudo_login=False,
    sudo_password=False,
    sudo_askpass_path=None,
    preserve_sudo_env=False,
    # Doas config
    doas=False,
    doas_user=None,
):
    """
    Builds a shell command with various kwargs.
    """

    if shell_executable is not None and not isinstance(shell_executable, str):
        shell_executable = "sh"

    if isinstance(command, bytes):
        command = command.decode("utf-8")

    if env:
        env_string = " ".join(['"{0}={1}"'.format(key, value) for key, value in env.items()])
        command = StringCommand("export", env_string, "&&", command)

    if chdir:
        command = StringCommand("cd", chdir, "&&", command)

    command_bits = []

    if doas:
        command_bits.extend(["doas", "-n"])

        if doas_user:
            command_bits.extend(["-u", doas_user])

    if sudo_password and sudo_askpass_path:
        command_bits.extend(
            [
                "env",
                "SUDO_ASKPASS={0}".format(sudo_askpass_path),
                MaskString("{0}={1}".format(SUDO_ASKPASS_ENV_VAR, sudo_password)),
            ],
        )

    if sudo:
        command_bits.extend(["sudo", "-H"])

        if sudo_password:
            command_bits.extend(["-A", "-k"])  # use askpass, disable cache
        else:
            command_bits.append("-n")  # disable prompt/interactivity

        if use_sudo_login:
            command_bits.append("-i")

        if preserve_sudo_env:
            command_bits.append("-E")

        if sudo_user:
            command_bits.extend(("-u", sudo_user))

    if su_user:
        command_bits.append("su")

        if use_su_login:
            _show_use_su_login_warning()
            command_bits.append("-l")

        if preserve_su_env:
            command_bits.append("-m")

        if su_shell:
            command_bits.extend(["-s", "`which {0}`".format(su_shell)])

        command_bits.extend([su_user, "-c"])

        if shell_executable is not None:
            # Quote the whole shell -c 'command' as BSD `su` does not have a shell option
            command_bits.append(
                QuoteString(StringCommand(shell_executable, "-c", QuoteString(command))),
            )
        else:
            command_bits.append(QuoteString(StringCommand(command)))
    else:
        if shell_executable is not None:
            command_bits.extend([shell_executable, "-c", QuoteString(command)])
        else:
            command_bits.extend([command])

    return StringCommand(*command_bits)


def make_win_command(command):
    """
    Builds a windows command with various kwargs.
    """

    # Quote the command as a string
    command = shlex.quote(str(command))
    command = "{0}".format(command)

    return command
