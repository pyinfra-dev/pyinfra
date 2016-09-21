# pyinfra
# File: tests/paramiko_util.py
# Desc: paramiko fake test classes/shim for full API tests

from inspect import isclass


class FakeAgentRequestHandler(object):
    def __init__(self, arg):
        pass


class FakeChannel(object):
    def __init__(self, exit_status):
        self.exit_status = exit_status

    def exit_status_ready(self):
        return True


class FakeBuffer(object):
    def __init__(self, data, channel):
        self.channel = channel
        self.data = data

    def __iter__(self):
        return iter(self.data)


class FakeSSHClient(object):
    def set_missing_host_key_policy(self, _):
        pass

    def connect(self, hostname, *args, **kwargs):
        if isclass(hostname) and issubclass(hostname, Exception):
            raise hostname()

    def get_transport(self):
        return self

    def open_session(self):
        pass

    def exec_command(self, command, get_pty=None):
        channel = FakeChannel(0)
        return (
            channel,
            FakeBuffer([], channel),
            FakeBuffer([], channel)
        )


class FakeSFTPClient(object):
    @classmethod
    def from_transport(cls, transport):
        return cls()

    def putfo(self, file_io, remote_location):
        pass


class FakeRSAKey(object):
    @classmethod
    def from_private_key_file(cls, *args, **kwargs):
        return cls()
