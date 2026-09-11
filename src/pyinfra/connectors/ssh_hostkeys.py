"""
Host key checking policies for the SSH connector, mirroring OpenSSH's
``StrictHostKeyChecking`` values which asyncssh does not implement itself.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from asyncssh import SSHClient, SSHKey, match_known_hosts
from typing_extensions import override

from pyinfra import logger
from pyinfra.api.exceptions import ConnectError

DEFAULT_KNOWN_HOSTS_FILE = "~/.ssh/known_hosts"

HOST_KEY_POLICIES = ("ask", "off", "yes", "accept-new")


def get_host_key_policy(policy: str | None) -> str:
    if policy is None:
        return "ask"
    if policy in ("no", "off"):
        return "off"
    if policy in HOST_KEY_POLICIES:
        return policy
    raise ConnectError(f"Invalid value StrictHostKeyChecking={policy}")


def resolve_known_hosts_files(known_hosts: Any) -> list[str] | None:
    """
    Turn asyncssh's resolved ``known_hosts`` option (explicit files, files from
    the SSH config, or nothing) into a list of expanded file paths. ``None``
    means host key checking is disabled entirely (``UserKnownHostsFile none``).
    """

    if known_hosts is None:
        return None

    if isinstance(known_hosts, str):
        known_hosts = [known_hosts]

    paths = (
        [str(Path(path).expanduser()) for path in known_hosts if isinstance(path, str)]
        if isinstance(known_hosts, (list, tuple))
        else []
    )

    return paths or [str(Path(DEFAULT_KNOWN_HOSTS_FILE).expanduser())]


def _host_pattern(host: str, port: int | None) -> str:
    if port in (None, 22):
        return host
    return f"[{host}]:{port}"


def append_known_host(filename: str, host: str, port: int | None, key: SSHKey) -> None:
    public_key = key.export_public_key("openssh").decode().strip()
    path = Path(filename).expanduser()
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "a", encoding="utf-8") as known_hosts_file:
        known_hosts_file.write(f"{_host_pattern(host, port)} {public_key}\n")


class PyinfraSSHClient(SSHClient):
    """
    asyncssh calls ``validate_host_public_key`` only when a host key was not
    found in the known hosts files, so this is where the policy applies.
    """

    def __init__(self, policy: str, known_hosts_files: list[str]):
        self.policy = policy
        self.known_hosts_files = known_hosts_files

    def _existing_host_keys(self, host: str, addr: str, port: int) -> list[SSHKey]:
        existing_files = [path for path in self.known_hosts_files if Path(path).is_file()]
        if not existing_files:
            return []

        try:
            return list(match_known_hosts(existing_files, host, addr, port)[0])
        except Exception as e:
            logger.warning("Failed to load host keys from %s: %s", existing_files, e)
            return []

    def _save_host_key(self, host: str, port: int, key: SSHKey) -> None:
        if not self.known_hosts_files:
            logger.warning("No host keys filename, not saving key for: %s", host)
            return

        append_known_host(self.known_hosts_files[0], host, port, key)
        logger.warning("Added host key for %s to known_hosts", host)

    @override
    def validate_host_public_key(self, host: str, addr: str, port: int, key: SSHKey) -> bool:
        if self._existing_host_keys(host, addr, port):
            logger.warning("WARNING: REMOTE HOST IDENTIFICATION HAS CHANGED!")
            logger.warning(
                "Someone could be eavesdropping on you right now (man-in-the-middle attack)!",
            )
            logger.warning("If this is expected, you can remove the bad key using:")
            logger.warning(f"    ssh-keygen -R {_host_pattern(host, port)}")
            return False

        if self.policy == "yes":
            logger.error("No host key for %s found in known_hosts", host)
            return False

        if self.policy == "off":
            logger.warning("No host key for %s found in known_hosts", host)
            return True

        if self.policy == "ask":
            should_continue = input(
                f"No host key for {host} found in known_hosts, do you want to continue [y/n] ",
            )
            if should_continue.lower() != "y":
                return False
        else:
            logger.warning(
                f"No host key for {host} found in known_hosts, accepting & adding to host keys file",
            )

        self._save_host_key(host, port, key)
        return True
