from __future__ import annotations

import ntpath
import os
from pathlib import PurePath
from shlex import quote
from socket import timeout as SocketTimeoutError
from typing import IO, AnyStr

from paramiko import Channel
from paramiko.transport import Transport

SCP_COMMAND = b"scp"


# Unicode conversion functions; assume UTF-8
def asbytes(s: bytes | str | PurePath) -> bytes:
    """Turns unicode into bytes, if needed.

    Assumes UTF-8.
    """
    if isinstance(s, bytes):
        return s
    elif isinstance(s, PurePath):
        return bytes(s)
    else:
        return s.encode("utf-8")


def asunicode(s: bytes | str) -> str:
    """Turns bytes into unicode, if needed.

    Uses UTF-8.
    """
    if isinstance(s, bytes):
        return s.decode("utf-8", "replace")
    else:
        return s


class SCPClient:
    """
    An scp1 implementation, compatible with openssh scp.
    Raises SCPException for all transport related errors. Local filesystem
    and OS errors pass through.

    Main public methods are .putfo and .getfo
    """

    def __init__(
        self,
        transport: Transport,
        buff_size: int = 16384,
        socket_timeout: float = 10.0,
    ):
        self.transport = transport
        self.buff_size = buff_size
        self.socket_timeout = socket_timeout
        self._channel: Channel | None = None
        self.scp_command = SCP_COMMAND

    @property
    def channel(self) -> Channel:
        """Return an open Channel, (re)opening if needed."""
        if self._channel is None or self._channel.closed:
            self._channel = self.transport.open_session()
        return self._channel

    def __enter__(self):
        _ = self.channel  # triggers opening if not already open
        return self

    def __exit__(self, type, value, traceback):
        self.close()

    def putfo(
        self,
        fl: IO[AnyStr],
        remote_path: str | bytes,
        mode: str | bytes = "0644",
        size: int | None = None,
    ) -> None:
        if size is None:
            pos = fl.tell()
            fl.seek(0, os.SEEK_END)  # Seek to end
            size = fl.tell() - pos
            fl.seek(pos, os.SEEK_SET)  # Seek back

        self.channel.settimeout(self.socket_timeout)
        self.channel.exec_command(
            self.scp_command + b" -t " + asbytes(quote(asunicode(remote_path)))
        )
        self._recv_confirm()
        self._send_file(fl, remote_path, mode, size=size)
        self.close()

    def getfo(self, remote_path: str, fl: IO):
        remote_path_sanitized = quote(remote_path)
        if os.name == "nt":
            remote_file_name = ntpath.basename(remote_path_sanitized)
        else:
            remote_file_name = os.path.basename(remote_path_sanitized)
        self.channel.settimeout(self.socket_timeout)
        self.channel.exec_command(self.scp_command + b" -f " + asbytes(remote_path_sanitized))
        self._recv_all(fl, remote_file_name)
        self.close()
        return fl

    def close(self):
        """close scp channel"""
        if self._channel is not None:
            self._channel.close()
            self._channel = None

    def _send_file(self, fl, name, mode, size):
        basename = asbytes(os.path.basename(name))
        # The protocol can't handle \n in the filename.
        # Quote them as the control sequence \^J for now,
        # which is how openssh handles it.
        self.channel.sendall(
            ("C%s %d " % (mode, size)).encode("ascii") + basename.replace(b"\n", b"\\^J") + b"\n"
        )
        self._recv_confirm()
        file_pos = 0
        buff_size = self.buff_size
        chan = self.channel
        while file_pos < size:
            chan.sendall(fl.read(buff_size))
            file_pos = fl.tell()
        chan.sendall(b"\x00")
        self._recv_confirm()

    def _recv_confirm(self):
        # read scp response
        msg = b""
        try:
            msg = self.channel.recv(512)
        except SocketTimeoutError:
            raise SCPException("Timeout waiting for scp response")
        # slice off the first byte, so this compare will work in py2 and py3
        if msg and msg[0:1] == b"\x00":
            return
        elif msg and msg[0:1] == b"\x01":
            raise SCPException(asunicode(msg[1:]))
        elif self.channel.recv_stderr_ready():
            msg = self.channel.recv_stderr(512)
            raise SCPException(asunicode(msg))
        elif not msg:
            raise SCPException("No response from server")
        else:
            raise SCPException("Invalid response from server", msg)

    def _recv_all(self, fh: IO, remote_file_name: str) -> None:
        # loop over scp commands, and receive as necessary
        commands = (b"C",)
        while not self.channel.closed:
            # wait for command as long as we're open
            self.channel.sendall(b"\x00")
            msg = self.channel.recv(1024)
            if not msg:  # chan closed while receiving
                break
            assert msg[-1:] == b"\n"
            msg = msg[:-1]
            code = msg[0:1]
            if code not in commands:
                raise SCPException(asunicode(msg[1:]))
            self._recv_file(msg[1:], fh, remote_file_name)

    def _recv_file(self, cmd: bytes, fh: IO, remote_file_name: str) -> None:
        chan = self.channel
        parts = cmd.strip().split(b" ", 2)

        try:
            size = int(parts[1])
        except (ValueError, IndexError):
            chan.send(b"\x01")
            chan.close()
            raise SCPException("Bad file format")

        buff_size = self.buff_size
        pos = 0
        chan.send(b"\x00")
        try:
            while pos < size:
                # we have to make sure we don't read the final byte
                if size - pos <= buff_size:
                    buff_size = size - pos
                data = chan.recv(buff_size)
                if not data:
                    raise SCPException("Underlying channel was closed")
                fh.write(data)
                pos = fh.tell()
            msg = chan.recv(512)
            if msg and msg[0:1] != b"\x00":
                raise SCPException(asunicode(msg[1:]))
        except SocketTimeoutError:
            chan.close()
            raise SCPException("Error receiving, socket.timeout")


class SCPException(Exception):
    """SCP exception class"""

    pass
