from __future__ import annotations

import shlex
from dataclasses import dataclass
from getpass import getpass
from queue import Queue
from socket import timeout as timeout_error
from subprocess import PIPE, Popen
from typing import TYPE_CHECKING, Callable, Iterable, Optional, Union

import click
import gevent

from pyinfra import logger
from pyinfra.api import MaskString, QuoteString, StringCommand
from pyinfra.api.util import memoize

if TYPE_CHECKING:
    from pyinfra.api.arguments import ConnectorArguments
    from pyinfra.api.host import Host
    from pyinfra.api.state import State


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


def run_local_process(
    command: str,
    stdin=None,
    timeout: Optional[int] = None,
    print_output: bool = False,
    print_prefix: str = "",
) -> tuple[int, "CommandOutput"]:
    process = Popen(command, shell=True, stdout=PIPE, stderr=PIPE, stdin=PIPE)

    if stdin:
        write_stdin(stdin, process.stdin)

    assert process.stdout is not None
    assert process.stderr is not None

    combined_output = read_output_buffers(
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


# Command output buffer handling
#


@dataclass
class OutputLine:
    buffer_name: str
    line: str


@dataclass
class CommandOutput:
    combined_lines: list[OutputLine]

    def __iter__(self):
        yield from self.combined_lines

    @property
    def output_lines(self) -> list[str]:
        return [line.line for line in self.combined_lines]

    @property
    def output(self) -> str:
        return "\n".join(self.output_lines)

    @property
    def stdout_lines(self) -> list[str]:
        return [line.line for line in self.combined_lines if line.buffer_name == "stdout"]

    @property
    def stdout(self) -> str:
        return "\n".join(self.stdout_lines)

    @property
    def stderr_lines(self) -> list[str]:
        return [line.line for line in self.combined_lines if line.buffer_name == "stderr"]

    @property
    def stderr(self) -> str:
        return "\n".join(self.stderr_lines)


def read_buffer(
    name: str,
    io: Iterable,
    output_queue: Queue[OutputLine],
    print_output=False,
    print_func=None,
) -> None:
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
        output_queue.put(OutputLine(name, line))

        if print_output:
            _print(line)


def read_output_buffers(
    stdout_buffer: Iterable,
    stderr_buffer: Iterable,
    timeout: Optional[int],
    print_output: bool,
    print_prefix: str,
) -> CommandOutput:
    output_queue: Queue[OutputLine] = Queue()

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

    return CommandOutput(list(output_queue.queue))


# Connector execution control
#


def execute_command_with_sudo_retry(
    host: "Host",
    command_arguments: "ConnectorArguments",
    execute_command: Callable[..., tuple[int, CommandOutput]],
) -> tuple[int, CommandOutput]:
    return_code, output = execute_command()

    # If we failed look for a sudo password prompt line and re-submit using the sudo password. Look
    # at all lines here in case anything else gets printed, eg in:
    # https://github.com/pyinfra-dev/pyinfra/issues/1292
    if return_code != 0 and output and output.combined_lines:
        for line in reversed(output.combined_lines):
            if line.line.strip() == "sudo: a password is required":
                # If we need a password, ask the user for it and attach to the host
                # internal connector data for use when executing future commands.
                sudo_password = getpass("{0}sudo password: ".format(host.print_prefix))
                host.connector_data["prompted_sudo_password"] = sudo_password
                return_code, output = execute_command()
                break

    return return_code, output


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


def remove_any_sudo_askpass_file(host) -> None:
    sudo_askpass_path = host.connector_data.get("sudo_askpass_path")
    if sudo_askpass_path:
        host.run_shell_command("rm -f {0}".format(sudo_askpass_path))
        host.connector_data["sudo_askpass_path"] = None


@memoize
def _show_use_su_login_warning() -> None:
    logger.warning(
        (
            "Using `use_su_login` may not work: "
            "some systems (MacOS, OpenBSD) ignore the flag when executing a command, "
            "use `sudo` + `use_sudo_login` instead."
        ),
    )


def extract_control_arguments(arguments: "ConnectorArguments") -> "ConnectorArguments":
    control_arguments: "ConnectorArguments" = {}

    if "_success_exit_codes" in arguments:
        control_arguments["_success_exit_codes"] = arguments.pop("_success_exit_codes")
    if "_timeout" in arguments:
        control_arguments["_timeout"] = arguments.pop("_timeout")
    if "_get_pty" in arguments:
        control_arguments["_get_pty"] = arguments.pop("_get_pty")
    if "_stdin" in arguments:
        control_arguments["_stdin"] = arguments.pop("_stdin")

    return control_arguments


def _ensure_sudo_askpass_set_for_host(host: "Host"):
    if host.connector_data.get("sudo_askpass_path"):
        return
    _, output = host.run_shell_command(SUDO_ASKPASS_COMMAND)
    host.connector_data["sudo_askpass_path"] = shlex.quote(output.stdout_lines[0])


def make_unix_command_for_host(
    state: "State",
    host: "Host",
    command: StringCommand,
    **command_arguments,
) -> StringCommand:
    if not command_arguments.get("_sudo"):
        # If no sudo, we've nothing to do here
        return make_unix_command(command, **command_arguments)

    # If the sudo password is not set in the direct arguments,
    # set it from the connector data value.
    if "_sudo_password" not in command_arguments or not command_arguments["_sudo_password"]:
        command_arguments["_sudo_password"] = host.connector_data.get("prompted_sudo_password")

    if command_arguments["_sudo_password"]:
        # Ensure the askpass path is correctly set and passed through
        _ensure_sudo_askpass_set_for_host(host)
        command_arguments["_sudo_askpass_path"] = host.connector_data["sudo_askpass_path"]
    return make_unix_command(command, **command_arguments)


# Connector command generation
#


def make_unix_command(
    command: StringCommand,
    _env=None,
    _chdir=None,
    _shell_executable="sh",
    # Su config
    _su_user=None,
    _use_su_login=False,
    _su_shell=None,
    _preserve_su_env=False,
    # Sudo config
    _sudo=False,
    _sudo_user=None,
    _use_sudo_login=False,
    _sudo_password="",
    _sudo_askpass_path=None,
    _preserve_sudo_env=False,
    # Doas config
    _doas=False,
    _doas_user=None,
) -> StringCommand:
    """
    Builds a shell command with various kwargs.
    """

    if _shell_executable is not None and not isinstance(_shell_executable, str):
        _shell_executable = "sh"

    if _env:
        env_string = " ".join(['"{0}={1}"'.format(key, value) for key, value in _env.items()])
        command = StringCommand("export", env_string, "&&", command)

    if _chdir:
        command = StringCommand("cd", _chdir, "&&", command)

    command_bits: list[Union[str, StringCommand, QuoteString]] = []

    if _doas:
        command_bits.extend(["doas", "-n"])

        if _doas_user:
            command_bits.extend(["-u", _doas_user])

    if _sudo_password and _sudo_askpass_path:
        command_bits.extend(
            [
                "env",
                "SUDO_ASKPASS={0}".format(_sudo_askpass_path),
                MaskString("{0}={1}".format(SUDO_ASKPASS_ENV_VAR, shlex.quote(_sudo_password))),
            ],
        )

    if _sudo:
        command_bits.extend(["sudo", "-H"])

        if _sudo_password:
            command_bits.extend(["-A", "-k"])  # use askpass, disable cache
        else:
            command_bits.append("-n")  # disable prompt/interactivity

        if _use_sudo_login:
            command_bits.append("-i")

        if _preserve_sudo_env:
            command_bits.append("-E")

        if _sudo_user:
            command_bits.extend(("-u", _sudo_user))

    if _su_user:
        command_bits.append("su")

        if _use_su_login:
            _show_use_su_login_warning()
            command_bits.append("-l")

        if _preserve_su_env:
            command_bits.append("-m")

        if _su_shell:
            command_bits.extend(["-s", "`which {0}`".format(_su_shell)])

        command_bits.extend([_su_user, "-c"])

        if _shell_executable is not None:
            # Quote the whole shell -c 'command' as BSD `su` does not have a shell option
            command_bits.append(
                QuoteString(StringCommand(_shell_executable, "-c", QuoteString(command))),
            )
        else:
            command_bits.append(QuoteString(StringCommand(command)))
    else:
        if _shell_executable is not None:
            command_bits.extend([_shell_executable, "-c", QuoteString(command)])
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
