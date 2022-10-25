"""
This file as originally part of the "sshuserclient" pypi package. The GitHub
source has now vanished (https://github.com/tobald/sshuserclient).
"""

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

from pyinfra import logger
from pyinfra.api.util import memoize

from .config import SSHConfig

HOST_KEYS_LOCK = BoundedSemaphore()


class StrictPolicy(MissingHostKeyPolicy):
    def missing_host_key(self, client, hostname, key):
        logger.error("No host key for {0} found in known_hosts".format(hostname))
        raise SSHException(
            "StrictPolicy: No host key for {0} found in known_hosts".format(hostname),
        )


class AcceptNewPolicy(MissingHostKeyPolicy):
    def missing_host_key(self, client, hostname, key):
        logger.warning(
            (
                f"No host key for {hostname} found in known_hosts, "
                "accepting & adding to host keys file"
            ),
        )

        with HOST_KEYS_LOCK:
            host_keys = client.get_host_keys()
            host_keys.add(hostname, key.get_name(), key)
            # The paramiko client saves host keys incorrectly whereas the host keys object does
            # this correctly, so use that with the client filename variable.
            # See: https://github.com/paramiko/paramiko/pull/1989
            host_keys.save(client._host_keys_filename)


class AskPolicy(MissingHostKeyPolicy):
    def missing_host_key(self, client, hostname, key):
        should_continue = input(
            "No host key for {0} found in known_hosts, do you want to continue [y/n] ".format(
                hostname,
            ),
        )
        if should_continue.lower() != "y":
            raise SSHException(
                "AskPolicy: No host key for {0} found in known_hosts".format(hostname),
            )
        with HOST_KEYS_LOCK:
            host_keys = client.get_host_keys()
            host_keys.add(hostname, key.get_name(), key)
            # The paramiko client saves host keys incorrectly whereas the host keys object does
            # this correctly, so use that with the client filename variable.
            # See: https://github.com/paramiko/paramiko/pull/1989
            host_keys.save(client._host_keys_filename)
        logger.warning("Added host key for {0} to known_hosts".format(hostname))
        return


class WarningPolicy(MissingHostKeyPolicy):
    def missing_host_key(self, client, hostname, key):
        logger.warning("No host key for {0} found in known_hosts".format(hostname))


def get_missing_host_key_policy(policy):
    if policy is None or policy == "ask":
        return AskPolicy()
    if policy == "no" or policy == "off":
        return WarningPolicy()
    if policy == "yes":
        return StrictPolicy()
    if policy == "accept-new":
        return AcceptNewPolicy()
    raise SSHException("Invalid value StrictHostKeyChecking={}".format(policy))


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
def get_host_keys(filename):
    with HOST_KEYS_LOCK:
        host_keys = HostKeys()

        try:
            host_keys.load(filename)
        # When paramiko encounters a bad host keys line it sometimes bails the
        # entire load incorrectly.
        # See: https://github.com/paramiko/paramiko/pull/1990
        except Exception as e:
            logger.warning("Failed to load host keys from {0}: {1}".format(filename, e))

        return host_keys


class SSHClient(ParamikoClient):
    """
    An SSHClient which honors ssh_config and supports proxyjumping
    original idea at http://bitprophet.org/blog/2012/11/05/gateway-solutions/.
    """

    def connect(
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
            host_keys_file,
        ) = self.parse_config(
            hostname,
            kwargs,
            ssh_config_file=_pyinfra_ssh_config_file,
            strict_host_key_checking=_pyinfra_ssh_strict_host_key_checking,
        )
        self.set_missing_host_key_policy(missing_host_key_policy)
        config.update(kwargs)

        if _pyinfra_ssh_known_hosts_file:
            host_keys_file = _pyinfra_ssh_known_hosts_file

        # Overwrite paramiko empty defaults with @memoize-d host keys object
        self._host_keys = get_host_keys(host_keys_file)
        self._host_keys_filename = host_keys_file

        if _pyinfra_ssh_paramiko_connect_kwargs:
            config.update(_pyinfra_ssh_paramiko_connect_kwargs)

        self._ssh_config = config
        super().connect(hostname, **config)

        if _pyinfra_ssh_forward_agent is not None:
            forward_agent = _pyinfra_ssh_forward_agent

        if forward_agent:
            # Enable SSH forwarding
            session = self.get_transport().open_session()
            AgentRequestHandler(session)

    def gateway(self, hostname, host_port, target, target_port):
        transport = self.get_transport()
        return transport.open_channel(
            "direct-tcpip",
            (target, target_port),
            (hostname, host_port),
        )

    def parse_config(
        self,
        hostname,
        initial_cfg=None,
        ssh_config_file=None,
        strict_host_key_checking=None,
    ):
        cfg = {"port": 22}
        cfg.update(initial_cfg or {})

        forward_agent = False
        missing_host_key_policy = get_missing_host_key_policy(strict_host_key_checking)
        host_keys_file = path.expanduser("~/.ssh/known_hosts")  # OpenSSH default

        ssh_config = get_ssh_config(ssh_config_file)
        if not ssh_config:
            return hostname, cfg, forward_agent, missing_host_key_policy, host_keys_file

        host_config = ssh_config.lookup(hostname)
        forward_agent = host_config.get("forwardagent") == "yes"

        # If not overridden, apply any StrictHostKeyChecking
        if strict_host_key_checking is None and "stricthostkeychecking" in host_config:
            missing_host_key_policy = get_missing_host_key_policy(
                host_config["stricthostkeychecking"],
            )

        if "userknownhostsfile" in host_config:
            host_keys_file = path.expanduser(host_config["userknownhostsfile"])

        if "hostname" in host_config:
            hostname = host_config["hostname"]

        if "user" in host_config:
            cfg["username"] = host_config["user"]

        if "identityfile" in host_config:
            cfg["key_filename"] = host_config["identityfile"]

        if "port" in host_config:
            cfg["port"] = int(host_config["port"])

        if "proxycommand" in host_config:
            cfg["sock"] = ProxyCommand(host_config["proxycommand"])

        elif "proxyjump" in host_config:
            hops = host_config["proxyjump"].split(",")
            sock = None

            for i, hop in enumerate(hops):
                hop_hostname, hop_config = self.derive_shorthand(ssh_config, hop)
                logger.debug("SSH ProxyJump through %s:%s", hop_hostname, hop_config["port"])

                c = SSHClient()
                c.connect(
                    hop_hostname, _pyinfra_ssh_config_file=ssh_config_file, sock=sock, **hop_config
                )

                if i == len(hops) - 1:
                    target = hostname
                    target_config = {"port": cfg["port"]}
                else:
                    target, target_config = self.derive_shorthand(ssh_config, hops[i + 1])

                sock = c.gateway(hostname, cfg["port"], target, target_config["port"])
            cfg["sock"] = sock

        return hostname, cfg, forward_agent, missing_host_key_policy, host_keys_file

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
        config.update(shorthand_config)

        return hostname, config
