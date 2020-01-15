from inspect import isclass
from unittest import TestCase

from paramiko import (
    RSAKey,
    SFTPClient,
    SSHClient,
)
from paramiko.agent import AgentRequestHandler

from pyinfra.api.connectors import ssh


class PatchSSHTestCase(TestCase):
    '''
    A test class that patches out the paramiko SSH parts such that they succeed as normal.
    The SSH tests above check these are called correctly.
    '''

    @classmethod
    def setUpClass(cls):
        ssh.SSHClient = FakeSSHClient
        ssh.SFTPClient = FakeSFTPClient
        ssh.RSAKey = FakeRSAKey
        ssh.AgentRequestHandler = FakeAgentRequestHandler

    @classmethod
    def tearDownClass(cls):
        ssh.SSHClient = SSHClient
        ssh.SFTPClient = SFTPClient
        ssh.RSAKey = RSAKey
        ssh.AgentRequestHandler = AgentRequestHandler


class FakeAgentRequestHandler(object):
    def __init__(self, arg):
        pass


class FakeChannel(object):
    def __init__(self, exit_status):
        self.exit_status = exit_status

    def exit_status_ready(self):
        return True

    def recv_exit_status(self):
        return self.exit_status

    def write(self, data):
        pass

    def close(self):
        pass


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
            FakeBuffer([], channel),
        )


class FakeSFTPClient(object):
    @classmethod
    def from_transport(cls, transport):
        return cls()

    def putfo(self, file_io, remote_location):
        pass

    def getfo(self, remote_location, file_io):
        pass


class FakeRSAKey(object):
    @classmethod
    def from_private_key_file(cls, *args, **kwargs):
        return cls()
