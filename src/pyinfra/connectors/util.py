from __future__ import annotations

from dataclasses import dataclass
from getpass import getpass
from queue import Queue
from socket import timeout as timeout_error
from gevent.subprocess import PIPE, Popen
from typing import TYPE_CHECKING, Callable, Iterable, Optional, Union

import gevent

from pyinfra import logger
from pyinfra.api.output import echo, format_text
from pyinfra.api import MaskString, QuoteString, StringCommand
from pyinfra.api.exceptions import PyinfraError
from pyinfra.api.util import memoize

if TYPE_CHECKING:
    from pyinfra.api.arguments import ConnectorArguments
    from pyinfra.api.host import Host
    from pyinfra.api.state import State


SUDO_ASKPASS_ENV_VAR = "PYINFRA_SUDO_PASSWORD"
SU_ASKPASS_ENV_VAR = "PYINFRA_SU_PASSWORD"


ASKPASS_COMMAND = r"""
temp=$(mktemp "${{TMPDIR:={0}}}/pyinfra-sudo-askpass-XXXXXXXXXXXX")
cat >"$temp"<<'__EOF__'
#!/bin/sh
printf '%s\n' "${1}"
__EOF__
chmod 755 "$temp"
echo "$temp"
"""


def run_local_process(
    command: str,
    stdin=None,
    timeout: Optional[int] = None,
    print_output: bool = False,
    print_prefix: str = "",
) -> tuple[int, "CommandOutput"]:
    process = Popen(command, shell=True, stdout=PIPE, stderr=PIPE, stdin=PIPE)

    assert process.stdout is not None
    assert process.stderr is not None
    assert process.stdin is not None

    # Write any stdin and then close it
    if stdin:
        write_stdin(stdin, process.stdin)
    process.stdin.close()

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

        echo(line, err=True)

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
            format_text(line, "red"),
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
    # Best-effort cleanup: this is called from host.disconnect(), and the
    # connection may already be broken (e.g. after `server.reboot`). Swallow
    # any errors from the remote ``rm`` and still clear the local state so a
    # reconnect will regenerate a fresh askpass file.
    sudo_askpass_path = host.connector_data.get("sudo_askpass_path")
    if sudo_askpass_path:
        try:
            host.run_shell_command(StringCommand("rm", "-f", QuoteString(sudo_askpass_path)))
        except Exception as e:
            logger.debug("Could not remove sudo askpass file %s: %s", sudo_askpass_path, e)
        host.connector_data["sudo_askpass_path"] = None

    su_askpass_path = host.connector_data.get("su_askpass_path")
    if su_askpass_path:
        try:
            host.run_shell_command(StringCommand("rm", "-f", QuoteString(su_askpass_path)))
        except Exception as e:
            logger.debug("Could not remove su askpass file %s: %s", su_askpass_path, e)
        host.connector_data["su_askpass_path"] = None


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
    return _ensure_askpass_set_for_host(host, "sudo_askpass_path", SUDO_ASKPASS_ENV_VAR)


def _ensure_su_askpass_set_for_host(host: "Host"):
    return _ensure_askpass_set_for_host(host, "su_askpass_path", SU_ASKPASS_ENV_VAR)


def _ensure_askpass_set_for_host(host: "Host", key: str, env_var: str):
    if host.connector_data.get(key):
        return
    ok, output = host.run_shell_command(ASKPASS_COMMAND.format(host.get_temp_dir_config(), env_var))

    if not ok:
        raise PyinfraError("Failed to create sudo_askpass command: {0}".format(output.output))

    if not output.stdout_lines:
        raise PyinfraError(
            "Failed to create sudo_askpass command: no output produced by command: {0}".format(
                output.output,
            )
        )

    host.connector_data[key] = output.stdout_lines[0]


def make_unix_command_for_host(
    state: "State",
    host: "Host",
    command: StringCommand,
    **command_arguments,
) -> StringCommand:
    # Handle sudo password
    if command_arguments.get("_sudo"):
        # If the sudo password is not set in the direct arguments,
        # set it from the connector data value.
        if "_sudo_password" not in command_arguments or not command_arguments["_sudo_password"]:
            command_arguments["_sudo_password"] = host.connector_data.get("prompted_sudo_password")

        if command_arguments.get("_sudo_password"):
            # Ensure the askpass path is correctly set and passed through
            _ensure_sudo_askpass_set_for_host(host)
            command_arguments["_sudo_askpass_path"] = host.connector_data["sudo_askpass_path"]

    # Handle su password
    if command_arguments.get("_su_user"):
        if command_arguments.get("_su_password"):
            _ensure_su_askpass_set_for_host(host)
            command_arguments["_su_askpass_path"] = host.connector_data["su_askpass_path"]

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
    _su_password="",
    _su_askpass_path=None,
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
    # Dzdo config
    _dzdo=False,
    _dzdo_user=None,
    # Retry config (ignored in command generation but passed through)
    _retries=0,
    _retry_delay=0,
    _retry_until=None,
    # Temp dir config (ignored in command generation, used for temp file path generation)
    _temp_dir=None,
) -> StringCommand:
    """
    Builds a shell command with various kwargs.
    """

    if _shell_executable is not None and not isinstance(_shell_executable, str):
        _shell_executable = "sh"

    if _env:
        env_bits: list[Union[str, StringCommand, QuoteString]] = ["export"]
        for key, value in _env.items():
            # Quote the whole `key=value` pair so arbitrary values cannot break
            # out into additional shell tokens. Invalid identifiers in `key` will
            # fail safely when the shell rejects the resulting `export` statement.
            env_bits.append(QuoteString("{0}={1}".format(key, value)))
        env_bits.append("&&")
        env_bits.append(command)
        command = StringCommand(*env_bits)

    if _chdir:
        command = StringCommand("cd", QuoteString(_chdir), "&&", command)

    command_bits: list[Union[str, StringCommand, QuoteString]] = []

    if _doas:
        command_bits.extend(["doas", "-n"])

        if _doas_user:
            command_bits.extend(["-u", QuoteString(_doas_user)])

    if _dzdo:
        command_bits.extend(["dzdo", "-H", "-n"])

        if _dzdo_user:
            command_bits.extend(["-u", QuoteString(_dzdo_user)])

    if _sudo_password and _sudo_askpass_path:
        command_bits.extend(
            [
                "env",
                StringCommand("SUDO_ASKPASS=", QuoteString(_sudo_askpass_path), _separator=""),
                MaskString(
                    "{0}={1}".format(
                        SUDO_ASKPASS_ENV_VAR,
                        StringCommand(QuoteString(_sudo_password)).get_raw_value(),
                    )
                ),
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
            command_bits.extend(("-u", QuoteString(_sudo_user)))

    if _su_user:
        if _su_password and _su_askpass_path:
            command_bits.extend(
                [
                    "env",
                    MaskString(
                        "{0}={1}".format(
                            SU_ASKPASS_ENV_VAR,
                            StringCommand(QuoteString(_su_password)).get_raw_value(),
                        )
                    ),
                    QuoteString(_su_askpass_path),
                    "|",
                ],
            )

        command_bits.append("su")

        if _use_su_login:
            _show_use_su_login_warning()
            command_bits.append("-l")

        if _preserve_su_env:
            command_bits.append("-m")

        if _su_shell:
            # Resolve the shell via `command -v`, with the user-supplied shell
            # name safely quoted so it cannot inject extra shell syntax.
            command_bits.extend(
                [
                    "-s",
                    StringCommand("$(command -v ", QuoteString(_su_shell), ")", _separator=""),
                ]
            )

        command_bits.extend([QuoteString(_su_user), "-c"])

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
    command = StringCommand(QuoteString(str(command))).get_raw_value()

    return command
