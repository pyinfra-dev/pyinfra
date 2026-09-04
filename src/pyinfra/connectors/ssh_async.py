from __future__ import annotations

import asyncio
import os
import socket
from random import uniform
from time import sleep
from typing import TYPE_CHECKING, Any

import asyncssh
import asyncio_gevent  # the bridge: asyncio loop driven by the gevent hub
import gevent
from gevent.lock import BoundedSemaphore
from typing_extensions import Unpack, override

from pyinfra import logger
from pyinfra.api.command import QuoteString, StringCommand
from pyinfra.api.exceptions import ConnectError
from pyinfra.api.output import echo, format_text
from pyinfra.api.util import get_file_io

from .base import BaseConnector
from .ssh import ConnectorData, SSHConnector, connector_data_meta  # reuse the @ssh data keys
from .util import (
    CommandOutput,
    OutputLine,
    execute_command_with_sudo_retry,
    make_unix_command_for_host,
)

if TYPE_CHECKING:
    from pyinfra.api.arguments import ConnectorArguments

_CHUNK = 1 << 16

# Serialise appends to known_hosts files across host greenlets.
_KNOWN_HOSTS_LOCK = BoundedSemaphore()


# The contained bridge
#
# A single gevent-hub-backed loop, shared by every host greenlet (all of which
# run in the one main-thread hub). It is driven forever in a dedicated greenlet;
# asyncio callbacks are pumped by the gevent selector so the loop cooperates with
# the rest of the engine rather than blocking it. Every asyncssh object is created
# on this one loop, so connection/process identity stays consistent across
# connect/run/disconnect (asyncio_gevent.async_to_sync would spin up a throwaway
# loop per call, orphaning the connection - hence the persistent loop here).

_loop: asyncio.AbstractEventLoop | None = None
_loop_greenlet: gevent.Greenlet | None = None


def _get_loop() -> asyncio.AbstractEventLoop:
    global _loop, _loop_greenlet
    if _loop is None:
        _loop = asyncio_gevent.EventLoop()
        _loop_greenlet = gevent.spawn(_loop.run_forever)
    return _loop


def _sync(coro):
    # Submit `coro` to the shared loop and block ONLY this greenlet until done.
    # run_coroutine_threadsafe returns a concurrent.futures.Future whose result()
    # waits on a gevent-patched Condition, so it yields to other host greenlets.
    future = asyncio.run_coroutine_threadsafe(coro, _get_loop())
    return future.result()


async def _read_process_output(
    process: asyncssh.SSHClientProcess,
    timeout: int | None,
    print_output: bool,
    print_prefix: str,
) -> CommandOutput:
    # Async equivalent of util.read_output_buffers: drain both streams
    # concurrently into one ordered list, printing as lines arrive.
    lines: list[OutputLine] = []

    async def drain(name, stream, print_func) -> None:
        if stream is None:  # eg stderr is folded into stdout when a PTY is used
            return
        async for line in stream:  # SSHReader yields decoded lines (encoding set below)
            line = line.rstrip("\n")
            lines.append(OutputLine(name, line))
            if print_output:
                echo(print_func(line), err=True)

    readers = asyncio.gather(
        drain("stdout", process.stdout, lambda line: f"{print_prefix}{line}"),
        drain("stderr", process.stderr, lambda line: f"{print_prefix}{format_text(line, 'red')}"),
    )
    try:
        await asyncio.wait_for(readers, timeout=timeout)
    except asyncio.TimeoutError:
        readers.cancel()
        raise TimeoutError()
    return CommandOutput(lines)


class AsyncSSHConnector(BaseConnector):
    """
    Experimental SSH connector backed by asyncssh instead of paramiko. A drop-in
    for the default ``@ssh`` connector - it reuses the same ``ssh_*`` host data
    keys and is targeted with ``@asyncssh/my-host.net``.

    The asyncio event loop, all asyncssh objects and the gevent<->asyncio bridge
    are fully contained within this module, so it can be used alongside the
    existing gevent-based engine without any global changes.
    """

    handles_execution = True

    data_cls = ConnectorData
    data_meta = connector_data_meta
    data: ConnectorData

    conn: asyncssh.SSHClientConnection | None = None
    sftp: asyncssh.SFTPClient | None = None
    server_host_key: asyncssh.SSHKey | None = None

    @override
    @staticmethod
    def make_names_data(name):
        yield f"@asyncssh/{name}", {"ssh_hostname": name}, []

    # Connect
    #

    @override
    def connect(self) -> None:
        hostname = self.data["ssh_hostname"] or self.host.name
        port = int(self.data["ssh_port"]) if self.data["ssh_port"] else 22

        # asyncio offloads name resolution to a thread-pool executor, where
        # gevent's cooperative getaddrinfo deadlocks on this hybrid loop. Resolve
        # here in gevent-land (which works) and hand asyncssh a numeric address so
        # it takes asyncio's numeric fast-path and skips getaddrinfo entirely.
        try:
            addr_info = socket.getaddrinfo(hostname, port, type=socket.SOCK_STREAM)
        except OSError as e:
            raise ConnectError(f"Could not resolve {hostname}: {e}") from e
        address = addr_info[0][4][0]

        # Decide host key verification up front, in gevent-land (file IO is fine
        # here). We connect by IP but must verify against the real hostname, so we
        # match the user's known_hosts ourselves and re-key the result to the IP
        # asyncssh actually sees (see _synthetic_known_hosts). Unknown hosts fall
        # through to the strict-host-key-checking policy below.
        known_hosts_arg, learn = self._resolve_host_key_policy(hostname, address, port)

        retries = self.data["ssh_connect_retries"]

        while True:
            try:
                _sync(self._connect(hostname, address, port, known_hosts_arg))
                break
            except ConnectError:
                if retries <= 0:
                    raise
                retries -= 1
                min_delay = self.data["ssh_connect_retry_min_delay"]
                max_delay = self.data["ssh_connect_retry_max_delay"]
                sleep(uniform(min_delay, max_delay))

        # Trust-on-first-use: learn the new host key per policy (accept-new/ask).
        if learn:
            self._learn_host_key(hostname, ask=learn == "ask")

    async def _connect(
        self, hostname: str, address: str, port: int, known_hosts: bytes | None
    ) -> None:
        data = self.data
        options: dict[str, Any] = {
            "host": address,
            "port": port,
            "connect_timeout": self.state.config.CONNECT_TIMEOUT,
            "known_hosts": known_hosts,
        }

        if data["ssh_user"]:
            options["username"] = data["ssh_user"]
        if data["ssh_password"]:
            options["password"] = data["ssh_password"]
        if data["ssh_key"]:
            options["client_keys"] = [data["ssh_key"]]
            if data["ssh_key_password"]:
                options["passphrase"] = data["ssh_key_password"]
        if not data["ssh_allow_agent"]:
            options["agent_path"] = None
        if data["ssh_config_file"]:
            options["config"] = [data["ssh_config_file"]]

        logger.debug("Connecting to: %s:%s (%r)", address, port, options)

        try:
            self.conn = await asyncssh.connect(**options)
        except asyncssh.HostKeyNotVerifiable as e:
            self._raise_host_key_changed(hostname, e)
        except (OSError, asyncssh.Error) as e:
            raise ConnectError(f"Could not connect: {type(e).__name__}: {e!r}") from e

        # Capture the server key so the sync layer can persist it for accept-new.
        self.server_host_key = self.conn.get_server_host_key()

    # Host key handling
    #
    # Mirrors the SSHConnector/sshuserclient policy: default ``accept-new`` (learn
    # new keys, reject changed ones), plus ``yes`` (strict), ``no``/``off`` (warn)
    # and ``ask`` (prompt). The known_hosts file defaults to ``~/.ssh/known_hosts``
    # and is overridden by ``ssh_known_hosts_file``.

    def _known_hosts_files(self) -> list[str]:
        override = self.data["ssh_known_hosts_file"]
        if override:
            return [os.path.expanduser(override)]
        return [os.path.expanduser("~/.ssh/known_hosts")]

    @staticmethod
    def _known_hosts_line(host: str, key: asyncssh.SSHKey) -> str:
        # export_public_key("openssh") returns ``algo base64`` - exactly a
        # known_hosts line minus the leading host pattern.
        return f"{host} " + key.export_public_key("openssh").decode().strip()

    def _resolve_host_key_policy(
        self, hostname: str, address: str, port: int
    ) -> tuple[bytes | None, bool | str]:
        """
        Returns ``(known_hosts_arg, learn)``. ``known_hosts_arg`` is passed to
        asyncssh: synthetic known_hosts bytes (verify during handshake) for a
        known host, or None (trust-on-first-use) for an unknown one. ``learn`` is
        False, True (accept-new) or "ask".
        """

        host_keys, ca_keys, revoked_keys = self._match_known_hosts(hostname, address, port)

        if host_keys or ca_keys:
            return self._synthetic_known_hosts(address, host_keys, ca_keys, revoked_keys), False

        # No entry for this host - apply the strict host key checking policy.
        strict = self.data["ssh_strict_host_key_checking"]

        if strict == "yes":
            raise ConnectError(
                f"No host key for {hostname} found in known_hosts "
                "(ssh_strict_host_key_checking=yes)",
            )
        if strict in ("no", "off"):
            logger.warning("No host key for %s found in known_hosts", hostname)
            return None, False
        if strict == "ask" or strict is None:
            return None, "ask"
        # accept-new (the default)
        return None, True

    def _match_known_hosts(self, hostname: str, address: str, port: int) -> tuple[list, list, list]:
        texts = []
        for filename in self._known_hosts_files():
            try:
                with open(filename, encoding="utf-8") as f:
                    texts.append(f.read())
            except FileNotFoundError:
                continue

        if not texts:
            return [], [], []

        try:
            known = asyncssh.import_known_hosts("\n".join(texts))
            host_keys, ca_keys, revoked_keys, *_x509 = known.match(hostname, address, port)
        except (asyncssh.KeyImportError, ValueError) as e:
            logger.warning("Failed to load known_hosts: %s", e)
            return [], [], []

        return list(host_keys), list(ca_keys), list(revoked_keys)

    def _synthetic_known_hosts(
        self, address: str, host_keys: list, ca_keys: list, revoked_keys: list
    ) -> bytes:
        # Re-key the keys we matched against the real hostname to the IP asyncssh
        # connects to, so it can verify them during the handshake.
        lines = [self._known_hosts_line(address, key) for key in host_keys]
        lines += [f"@cert-authority {self._known_hosts_line(address, key)}" for key in ca_keys]
        lines += [f"@revoked {self._known_hosts_line(address, key)}" for key in revoked_keys]
        return ("\n".join(lines) + "\n").encode()

    def _learn_host_key(self, hostname: str, ask: bool) -> None:
        key = self.server_host_key
        if key is None:
            return

        if ask:
            answer = input(
                f"The authenticity of host '{hostname}' can't be established.\n"
                f"Key fingerprint is {key.get_fingerprint()}.\n"
                "Are you sure you want to continue connecting (yes/no)? ",
            )
            if answer.strip().lower() not in ("yes", "y"):
                _sync(self._disconnect())
                raise ConnectError(f"Host key for {hostname} not accepted")

        target = self._known_hosts_files()[0]
        with _KNOWN_HOSTS_LOCK:
            with open(target, "a", encoding="utf-8") as f:
                f.write(self._known_hosts_line(hostname, key) + "\n")
        logger.warning("Added host key for %s to %s", hostname, target)

    def _raise_host_key_changed(self, hostname: str, error: Exception) -> None:
        logger.warning("WARNING: REMOTE HOST IDENTIFICATION HAS CHANGED!")
        logger.warning(
            "Someone could be eavesdropping on you right now (man-in-the-middle attack)!",
        )
        logger.warning("If this is expected, you can remove the bad key using:")
        logger.warning(f"    ssh-keygen -R {hostname}")
        raise ConnectError(f"Host key for {hostname} does not match known_hosts") from error

    @override
    def disconnect(self) -> None:
        if self.conn is not None:
            _sync(self._disconnect())

    async def _disconnect(self) -> None:
        if self.sftp is not None:
            self.sftp.exit()
            self.sftp = None
        assert self.conn is not None
        self.conn.close()
        await self.conn.wait_closed()

    # Run shell command
    #
    # Structure mirrors SSHConnector.run_shell_command - each sudo-retry attempt
    # bridges into async via _sync so the retry/getpass logic stays synchronous.

    @override
    def run_shell_command(
        self,
        command: StringCommand,
        print_output: bool = False,
        print_input: bool = False,
        **arguments: Unpack[ConnectorArguments],
    ) -> tuple[bool, CommandOutput]:
        _get_pty = arguments.pop("_get_pty", False)
        _timeout = arguments.pop("_timeout", None)
        _stdin = arguments.pop("_stdin", None)
        _success_exit_codes = arguments.pop("_success_exit_codes", None)

        def execute_command() -> tuple[int, CommandOutput]:
            return _sync(
                self._execute_once(
                    command,
                    _get_pty=_get_pty,
                    _timeout=_timeout,
                    _stdin=_stdin,
                    print_output=print_output,
                    print_input=print_input,
                    arguments=arguments,
                )
            )

        return_code, combined_output = execute_command_with_sudo_retry(
            self.host,
            arguments,
            execute_command,
        )

        if _success_exit_codes:
            status = return_code in _success_exit_codes
        else:
            status = return_code == 0

        return status, combined_output

    async def _execute_once(
        self,
        command: StringCommand,
        _get_pty: bool,
        _timeout: int | None,
        _stdin,
        print_output: bool,
        print_input: bool,
        arguments,
    ) -> tuple[int, CommandOutput]:
        assert self.conn is not None

        unix_command = make_unix_command_for_host(self.state, self.host, command, **arguments)
        actual_command = unix_command.get_raw_value()

        logger.debug(
            "Running command on %s: (pty=%s) %s",
            self.host.name,
            _get_pty,
            unix_command,
        )

        if print_input:
            echo(f"{self.host.print_prefix}>>> {unix_command}", err=True)

        process = await self.conn.create_process(
            actual_command,
            term_type="xterm" if _get_pty else None,  # a term_type allocates a PTY
            encoding="utf-8",
            errors="replace",
        )

        if _stdin is not None:
            lines = _stdin if isinstance(_stdin, (list, tuple)) else [_stdin]
            for line in lines:
                process.stdin.write(line if line.endswith("\n") else f"{line}\n")
        process.stdin.write_eof()

        combined_output = await _read_process_output(
            process,
            timeout=_timeout,
            print_output=print_output,
            print_prefix=self.host.print_prefix,
        )

        await process.wait()
        exit_status = process.exit_status if process.exit_status is not None else 1
        logger.debug("Command exit status: %i", exit_status)

        return exit_status, combined_output

    # File transfer
    #
    # The sudo/temp-file/chown orchestration in put_file/get_file is connector
    # agnostic, so it is lifted verbatim from SSHConnector. Only the raw SFTP
    # transfer (_put_file/_get_file) is asyncssh-specific and bridges via _sync.

    async def _get_sftp(self) -> asyncssh.SFTPClient:
        if self.sftp is None:
            assert self.conn is not None
            self.sftp = await self.conn.start_sftp_client()
        return self.sftp

    async def _put_file_async(self, filename_or_io, remote_location: str) -> None:
        sftp = await self._get_sftp()
        with get_file_io(filename_or_io) as file_io:
            async with sftp.open(remote_location, "wb", encoding=None) as remote_file:
                while chunk := file_io.read(_CHUNK):
                    await remote_file.write(chunk)

    async def _get_file_async(self, remote_filename: str, filename_or_io) -> None:
        sftp = await self._get_sftp()
        with get_file_io(filename_or_io, "wb") as file_io:
            async with sftp.open(remote_filename, "rb", encoding=None) as remote_file:
                while chunk := await remote_file.read(_CHUNK):
                    file_io.write(chunk)

    def _put_file(self, filename_or_io, remote_location):
        logger.debug("Attempting upload of %s to %s", filename_or_io, remote_location)

        attempts = 0
        last_e = None

        while attempts < 3:
            try:
                _sync(self._put_file_async(filename_or_io, remote_location))
                return
            except OSError as e:
                logger.warning(f"Failed to upload file, retrying: {e}")
                attempts += 1
                last_e = e

        if last_e is not None:
            raise last_e

    def _get_file(self, remote_filename, filename_or_io):
        _sync(self._get_file_async(remote_filename, filename_or_io))

    @override
    def get_file(
        self,
        remote_filename: str,
        filename_or_io,
        remote_temp_filename=None,
        print_output: bool = False,
        print_input: bool = False,
        **arguments: Unpack[ConnectorArguments],
    ) -> bool:
        """
        Download a file from the remote host using SFTP. Supports download files
        with sudo by copying to a temporary directory with read permissions,
        downloading and then removing the copy.
        """

        _sudo = arguments.get("_sudo", False)
        _su_user = arguments.get("_su_user", None)

        if _sudo or _su_user:
            # Get temp file location
            temp_file = remote_temp_filename or self.host.get_temp_filename(remote_filename)

            # Copy the file to the tempfile location and add read permissions
            command = StringCommand(
                "cp", remote_filename, temp_file, "&&", "chmod", "+r", temp_file
            )

            copy_status, output = self.run_shell_command(
                command,
                print_output=print_output,
                print_input=print_input,
                **arguments,
            )

            if copy_status is False:
                logger.error(f"File download copy temp error: {output.stderr}")
                return False

            try:
                self._get_file(temp_file, filename_or_io)

            # Ensure that, even if we encounter an error, we (attempt to) remove the
            # temporary copy of the file.
            finally:
                remove_status, output = self.run_shell_command(
                    StringCommand("rm", "-f", temp_file),
                    print_output=print_output,
                    print_input=print_input,
                    **arguments,
                )

            if remove_status is False:
                logger.error(f"File download remove temp error: {output.stderr}")
                return False

        else:
            self._get_file(remote_filename, filename_or_io)

        if print_output:
            echo(
                f"{self.host.print_prefix}file downloaded: {remote_filename}",
                err=True,
            )

        return True

    @override
    def put_file(
        self,
        filename_or_io,
        remote_filename,
        remote_temp_filename=None,
        print_output: bool = False,
        print_input: bool = False,
        **arguments: Unpack[ConnectorArguments],
    ) -> bool:
        """
        Upload file-ios to the specified host using SFTP. Supports uploading files
        with sudo by uploading to a temporary directory then moving & chowning.
        """

        noauth_arguments = arguments.copy()

        _sudo = noauth_arguments.pop("_sudo", False)
        _sudo_user = noauth_arguments.pop("_sudo_user", False)
        _doas = noauth_arguments.pop("_doas", False)
        _doas_user = noauth_arguments.pop("_doas_user", False)
        _dzdo = noauth_arguments.pop("_dzdo", False)
        _dzdo_user = noauth_arguments.pop("_dzdo_user", False)
        _su_user = noauth_arguments.pop("_su_user", None)

        # _chdir is the only one of the global arguments that could require _sudo to succeed
        # and _sudo isn't present in arguments as removed above
        noauth_arguments.pop("_chdir", False)

        # sudo/su are a little more complicated, as you can only sftp with the SSH
        # user connected, so upload to tmp and copy/chown w/sudo and/or su_user
        if _sudo or _doas or _dzdo or _su_user:
            # Get temp file location
            temp_file = remote_temp_filename or self.host.get_temp_filename(remote_filename)
            self._put_file(filename_or_io, temp_file)

            # Make sure our sudo/su user can access the file
            other_user = _su_user or _sudo_user or _doas_user or _dzdo_user
            if other_user:
                status, output = self.run_shell_command(
                    StringCommand("setfacl", "-m", f"u:{other_user}:r", temp_file),
                    print_output=print_output,
                    print_input=print_input,
                    **noauth_arguments,
                )

                if status is False:
                    logger.error(f"Error on handover to sudo/su user: {output.stderr}")
                    return False

            # Execute run_shell_command w/sudo, etc
            command = StringCommand("cp", temp_file, QuoteString(remote_filename))

            status, output = self.run_shell_command(
                command,
                print_output=print_output,
                print_input=print_input,
                **arguments,
            )

            if status is False:
                logger.error(f"File upload error: {output.stderr}")
                return False

            # Delete the temporary file now that we've successfully copied it
            status, output = self.run_shell_command(
                StringCommand("rm", "-f", temp_file),
                print_output=print_output,
                print_input=print_input,
                **noauth_arguments,
            )

            if status is False:
                logger.error(f"Unable to remove temporary file: {output.stderr}")
                return False

        # No sudo and no su_user, so just upload it!
        else:
            self._put_file(filename_or_io, remote_filename)

        if print_output:
            echo(
                f"{self.host.print_prefix}file uploaded: {remote_filename}",
                err=True,
            )

        return True

    # rsync shells out to the local rsync binary over the ssh CLI - it is fully
    # transport-independent and reuses the same ssh_* data keys, so reuse the
    # SSHConnector implementation as-is.
    check_can_rsync = SSHConnector.check_can_rsync
    rsync = SSHConnector.rsync
