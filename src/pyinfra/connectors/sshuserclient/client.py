"""
This file as originally part of the "sshuserclient" pypi package. The GitHub
source has now vanished (https://github.com/tobald/sshuserclient).
"""

import os
from os import path

from gevent.lock import BoundedSemaphore
from paramiko import (
    HostKeys,
    MissingHostKeyPolicy,
    ProxyCommand,
    SSHClient as ParamikoClient,
    SSHException,
)
from paramiko.agent import AgentRequestHandler
from paramiko.hostkeys import HostKeyEntry
from typing_extensions import override

from pyinfra import logger
from pyinfra.api.exceptions import PyinfraError
from pyinfra.api.util import memoize
from pyinfra.connectors.ssh_util import load_key_with_certificate

from .config import SSHConfig

HOST_KEYS_LOCK = BoundedSemaphore()


class StrictPolicy(MissingHostKeyPolicy):
    @override
    def missing_host_key(self, client, hostname, key):
        logger.error("No host key for %s found in known_hosts", hostname)
        raise SSHException(f"StrictPolicy: No host key for {hostname} found in known_hosts")


def append_hostkey(client, hostname, key):
    """Append hostname to the clients host_keys_file"""

    if client._host_keys_filename is None:
        logger.warning("No host keys filename, not saving key for: %s", hostname)
        return

    with HOST_KEYS_LOCK:
        # The paramiko client saves host keys incorrectly whereas the host keys object does
        # this correctly, so use that with the client filename variable.
        # See: https://github.com/paramiko/paramiko/pull/1989
        host_key_entry = HostKeyEntry([hostname], key)
        if host_key_entry is None:
            raise SSHException(
                f"Append Hostkey: Failed to parse host {hostname}, could not append to hostfile",
            )
        with open(client._host_keys_filename, "a") as host_keys_file:
            hk_entry = host_key_entry.to_line()
            if hk_entry is None:
                raise SSHException(f"Append Hostkey: Failed to append hostkey ({host_key_entry})")

            host_keys_file.write(hk_entry)


class AcceptNewPolicy(MissingHostKeyPolicy):
    @override
    def missing_host_key(self, client, hostname, key):
        logger.warning(
            (
                f"No host key for {hostname} found in known_hosts, "
                "accepting & adding to host keys file"
            ),
        )

        append_hostkey(client, hostname, key)
        logger.warning("Added host key for %s to known_hosts", hostname)


class AskPolicy(MissingHostKeyPolicy):
    @override
    def missing_host_key(self, client, hostname, key):
        should_continue = input(
            f"No host key for {hostname} found in known_hosts, do you want to continue [y/n] ",
        )
        if should_continue.lower() != "y":
            raise SSHException(
                f"AskPolicy: No host key for {hostname} found in known_hosts",
            )
        append_hostkey(client, hostname, key)
        logger.warning("Added host key for %s to known_hosts", hostname)
        return


class WarningPolicy(MissingHostKeyPolicy):
    @override
    def missing_host_key(self, client, hostname, key):
        logger.warning("No host key for %s found in known_hosts", hostname)


def _attach_identity_with_certificate(cfg: dict, host_config: dict) -> None:
    """
    Replace ``cfg["key_filename"]`` with a pre-built ``pkey`` when an ssh_config
    ``IdentityFile`` exists on disk. Honours ``CertificateFile`` directives and
    falls back to the implicit ``<key>-cert.pub`` lookup so OpenSSH-style CA
    auth works without explicit pyinfra ``ssh_key`` configuration (issue #1569).
    Silent fall-through when no identity exists keeps the legacy paramiko
    ``key_filename`` flow for missing or otherwise unloadable files.
    """

    identity_files = host_config.get("identityfile") or []
    if isinstance(identity_files, str):
        identity_files = [identity_files]

    certificate_files = host_config.get("certificatefile") or []
    if isinstance(certificate_files, str):
        certificate_files = [certificate_files]
    certificate_filename = certificate_files[0] if certificate_files else None

    for identity_file in identity_files:
        expanded = path.expanduser(identity_file)
        if not path.isfile(expanded):
            continue
        try:
            cfg["pkey"] = load_key_with_certificate(
                key_filename=identity_file,
                certificate_filename=certificate_filename,
            )
        except (PyinfraError, SSHException, OSError) as e:
            logger.debug("Could not load identity %s with certificate: %s", identity_file, e)
            continue
        cfg.pop("key_filename", None)
        return


def get_missing_host_key_policy(policy):
    if policy is None or policy == "ask":
        return AskPolicy()
    if policy == "no" or policy == "off":
        return WarningPolicy()
    if policy == "yes":
        return StrictPolicy()
    if policy == "accept-new":
        return AcceptNewPolicy()
    raise SSHException(f"Invalid value StrictHostKeyChecking={policy}")


@memoize
def get_ssh_config(user_config_file=None):
    logger.debug("Loading SSH config: %s", user_config_file)

    if user_config_file is None:
        user_config_file = path.expanduser("~/.ssh/config")

    if path.exists(user_config_file):
        with open(user_config_file, encoding="utf-8") as f:
            ssh_config = SSHConfig()
            ssh_config.parse(f)
            return ssh_config


@memoize
def get_host_keys(filenames):
    """
    Load host keys from one or more files.

    Args:
        filenames: A tuple of filenames to load host keys from.
    """
    with HOST_KEYS_LOCK:
        host_keys = HostKeys()

        for filename in filenames:
            try:
                host_keys.load(filename)
            # When paramiko encounters a bad host keys line it sometimes bails the
            # entire load incorrectly.
            # See: https://github.com/paramiko/paramiko/pull/1990
            except Exception as e:
                logger.warning("Failed to load host keys from %s: %s", filename, e)

        return host_keys


class SSHClient(ParamikoClient):
    """
    An SSHClient which honors ssh_config and supports proxyjumping
    original idea at http://bitprophet.org/blog/2012/11/05/gateway-solutions/.
    """

    @override
    def connect(  # type: ignore[override]
        self,
        hostname,
        _pyinfra_ssh_forward_agent=None,
        _pyinfra_ssh_config_file=None,
        _pyinfra_ssh_known_hosts_file=None,
        _pyinfra_ssh_strict_host_key_checking=None,
        _pyinfra_ssh_paramiko_connect_kwargs=None,
        **kwargs,
    ):
        (
            hostname,
            config,
            forward_agent,
            missing_host_key_policy,
            host_keys_files,
            keep_alive,
            identity_agent,
        ) = self.parse_config(
            hostname,
            kwargs,
            ssh_config_file=_pyinfra_ssh_config_file,
            strict_host_key_checking=_pyinfra_ssh_strict_host_key_checking,
        )
        self.set_missing_host_key_policy(missing_host_key_policy)
        config.update(kwargs)

        if _pyinfra_ssh_known_hosts_file:
            host_keys_files = (path.expanduser(_pyinfra_ssh_known_hosts_file),)

        # Overwrite paramiko empty defaults with @memoize-d host keys object
        self._host_keys = get_host_keys(host_keys_files)
        # Use the first file for writing new host keys
        if len(host_keys_files) > 0:
            self._host_keys_filename = host_keys_files[0]

        if _pyinfra_ssh_paramiko_connect_kwargs:
            config.update(_pyinfra_ssh_paramiko_connect_kwargs)

        self._ssh_config = config
        self.identity_agent = identity_agent

        # Honor IdentityAgent from SSH config by temporarily setting SSH_AUTH_SOCK
        # so Paramiko's Agent class connects to the correct socket.
        old_auth_sock = os.environ.get("SSH_AUTH_SOCK")
        if identity_agent:
            os.environ["SSH_AUTH_SOCK"] = identity_agent
        try:
            super().connect(hostname, **config)
        finally:
            if identity_agent:
                if old_auth_sock is not None:
                    os.environ["SSH_AUTH_SOCK"] = old_auth_sock
                else:
                    os.environ.pop("SSH_AUTH_SOCK", None)

        if _pyinfra_ssh_forward_agent is not None:
            forward_agent = _pyinfra_ssh_forward_agent

        if keep_alive:
            transport = self.get_transport()
            assert transport is not None, "No transport"
            transport.set_keepalive(keep_alive)

        if forward_agent:
            transport = self.get_transport()
            assert transport is not None, "No transport"
            session = transport.open_session()
            AgentRequestHandler(session)

    def gateway(self, hostname, host_port, target, target_port, timeout=None):
        transport = self.get_transport()
        assert transport is not None, "No transport"
        return transport.open_channel(
            "direct-tcpip",
            (target, target_port),
            (hostname, host_port),
            timeout=timeout,
        )

    def parse_config(
        self,
        hostname,
        initial_cfg=None,
        ssh_config_file=None,
        strict_host_key_checking=None,
    ):
        cfg: dict = {"port": 22}
        cfg.update(initial_cfg or {})

        keep_alive = 0
        forward_agent = False
        identity_agent = None
        missing_host_key_policy = get_missing_host_key_policy(strict_host_key_checking)
        host_keys_files = (path.expanduser("~/.ssh/known_hosts"),)

        ssh_config = get_ssh_config(ssh_config_file)
        if not ssh_config:
            return (
                hostname,
                cfg,
                forward_agent,
                missing_host_key_policy,
                host_keys_files,
                keep_alive,
                identity_agent,
            )

        host_config = ssh_config.lookup(hostname)
        forward_agent = host_config.get("forwardagent") == "yes"

        # If not overridden, apply any StrictHostKeyChecking
        if strict_host_key_checking is None and "stricthostkeychecking" in host_config:
            missing_host_key_policy = get_missing_host_key_policy(
                host_config["stricthostkeychecking"],
            )

        if "userknownhostsfile" in host_config:
            # OpenSSH supports multiple space-separated known hosts files
            host_keys_files = tuple(
                path.expanduser(f) for f in host_config["userknownhostsfile"].split()
            )

        if "hostname" in host_config:
            hostname = host_config["hostname"]

        if "user" in host_config:
            cfg["username"] = host_config["user"]

        if "identityfile" in host_config:
            cfg["key_filename"] = host_config["identityfile"]
            _attach_identity_with_certificate(cfg, host_config)

        if "port" in host_config:
            cfg["port"] = int(host_config["port"])

        # Respect ``ConnectTimeout`` from ssh_config (issue #971): without this,
        # paramiko waits on its own default and a ProxyJump hop can hang for
        # minutes before failing.
        if "connecttimeout" in host_config and "timeout" not in cfg:
            cfg["timeout"] = int(host_config["connecttimeout"])

        if "serveraliveinterval" in host_config:
            keep_alive = int(host_config["serveraliveinterval"])

        if "identityagent" in host_config:
            agent_path = host_config["identityagent"]
            if agent_path.lower() != "none":
                identity_agent = path.expanduser(agent_path)

        if "proxycommand" in host_config:
            cfg["sock"] = ProxyCommand(host_config["proxycommand"])

        elif "proxyjump" in host_config:
            hops = host_config["proxyjump"].split(",")
            sock = None
            # Propagate the target's timeout down so hop connections and the
            # direct-tcpip channel don't hang forever when the network misbehaves
            # (issue #971). Individual hops can still override via their own
            # ``ConnectTimeout`` in ssh_config.
            target_timeout = cfg.get("timeout")

            for i, hop in enumerate(hops):
                hop_hostname, hop_config = self.derive_shorthand(ssh_config, hop)
                logger.debug("SSH ProxyJump through %s:%s", hop_hostname, hop_config["port"])

                hop_connect_kwargs = dict(hop_config)
                if "timeout" not in hop_connect_kwargs and target_timeout is not None:
                    hop_connect_kwargs["timeout"] = target_timeout

                c = SSHClient()
                c.connect(
                    hop_hostname,
                    _pyinfra_ssh_config_file=ssh_config_file,
                    sock=sock,
                    **hop_connect_kwargs,
                )

                if i == len(hops) - 1:
                    target = hostname
                    target_config = {"port": cfg["port"]}
                else:
                    target, target_config = self.derive_shorthand(ssh_config, hops[i + 1])

                sock = c.gateway(
                    hostname,
                    cfg["port"],
                    target,
                    target_config["port"],
                    timeout=target_timeout,
                )
            cfg["sock"] = sock

        return (
            hostname,
            cfg,
            forward_agent,
            missing_host_key_policy,
            host_keys_files,
            keep_alive,
            identity_agent,
        )

    @staticmethod
    def derive_shorthand(ssh_config, host_string):
        shorthand_config = {}
        user_hostport = host_string.rsplit("@", 1)
        hostport = user_hostport.pop()
        user = user_hostport[0] if user_hostport and user_hostport[0] else None
        if user:
            shorthand_config["username"] = user

        # IPv6: can't reliably tell where addr ends and port begins, so don't
        # try (and don't bother adding special syntax either, user should avoid
        # this situation by using port=).
        if hostport.count(":") > 1:
            hostname = hostport
        # IPv4: can split on ':' reliably.
        else:
            host_port = hostport.rsplit(":", 1)
            hostname = host_port.pop(0) or None
            if host_port and host_port[0]:
                shorthand_config["port"] = int(host_port[0])

        base_config = ssh_config.lookup(hostname)

        config = {
            "port": base_config.get("port", 22),
            "username": base_config.get("user"),
        }
        if "connecttimeout" in base_config:
            config["timeout"] = int(base_config["connecttimeout"])
        config.update(shorthand_config)

        return hostname, config
