'''
This file as originally part of the "sshuserclient" pypi package. The GitHub
source has now vanished (https://github.com/tobald/sshuserclient).
'''

from os import path

from paramiko import (
    MissingHostKeyPolicy,
    ProxyCommand,
    SSHClient as ParamikoClient,
    SSHException,
)
from paramiko.agent import AgentRequestHandler

from pyinfra import logger
from pyinfra.api.util import memoize

from .config import SSHConfig


class StrictPolicy(MissingHostKeyPolicy):
    def missing_host_key(self, client, hostname, key):
        logger.error('No host key for {0} found in known_hosts'.format(hostname))
        raise SSHException(
            'StrictPolicy: No host key for {0} found in known_hosts'.format(hostname))


class AskPolicy(MissingHostKeyPolicy):
    def missing_host_key(self, client, hostname, key):
        should_continue = input(
            'No host key for {0} found in known_hosts, do you want to continue [y/n]'.format(
                hostname))
        if should_continue.lower() != 'y':
            raise SSHException(
                'AskPolicy: No host key for {0} found in known_hosts'.format(hostname))
        else:
            client.get_host_keys().add(hostname, key.get_name(), key)
            if client._host_keys_filename is not None:
                client.save_host_keys(client._host_keys_filename)
            logger.warning('Added host key for {0} to known_hosts'.format(hostname))
            return


class WarningPolicy(MissingHostKeyPolicy):
    def missing_host_key(self, client, hostname, key):
        logger.warning('No host key for {0} found in known_hosts'.format(hostname))


@memoize
def get_ssh_config(user_config_file=None):
    if user_config_file is None:
        user_config_file = path.expanduser('~/.ssh/config')
    if path.exists(user_config_file):
        with open(user_config_file) as f:
            ssh_config = SSHConfig()
            ssh_config.parse(f)
            return ssh_config


class SSHClient(ParamikoClient):
    '''
    An SSHClient which honors ssh_config and supports proxyjumping
    original idea at http://bitprophet.org/blog/2012/11/05/gateway-solutions/.
    '''

    def connect(
        self,
        hostname,
        _pyinfra_force_forward_agent=None,
        _pyinfra_ssh_config_file=None,
        **kwargs
    ):
        hostname, config, forward_agent, missing_host_key_policy = self.parse_config(
            hostname,
            kwargs,
            ssh_config_file=_pyinfra_ssh_config_file,
        )
        self.set_missing_host_key_policy(missing_host_key_policy)
        config.update(kwargs)
        super(SSHClient, self).connect(hostname, **config)

        if _pyinfra_force_forward_agent is not None:
            forward_agent = _pyinfra_force_forward_agent

        if forward_agent:
            # Enable SSH forwarding
            session = self.get_transport().open_session()
            AgentRequestHandler(session)

    def gateway(self, hostname, host_port, target, target_port):
        transport = self.get_transport()
        return transport.open_channel(
            'direct-tcpip',
            (target, target_port),
            (hostname, host_port),
        )

    def parse_config(self, hostname, initial_cfg=None, ssh_config_file=None):
        cfg = {'port': 22}
        cfg.update(initial_cfg or {})

        forward_agent = False

        ssh_config = get_ssh_config(ssh_config_file)
        if not ssh_config:
            return hostname, cfg, forward_agent

        host_config = ssh_config.lookup(hostname)
        forward_agent = host_config.get('forwardagent') == 'yes'

        missing_host_key_policy = AskPolicy()

        if 'stricthostkeychecking' in host_config:
            v = host_config['stricthostkeychecking']
            if v == 'ask':
                missing_host_key_policy = AskPolicy()
            elif v == 'no' or v == 'off':
                missing_host_key_policy = WarningPolicy()
            elif v == 'yes':
                missing_host_key_policy = StrictPolicy()
            else:
                raise SSHException(
                    'Invalid value StrictHostKeyChecking={}'.format(
                        host_config['stricthostkeychecking']))

        if 'hostname' in host_config:
            hostname = host_config['hostname']

        if 'user' in host_config:
            cfg['username'] = host_config['user']

        if 'identityfile' in host_config:
            cfg['key_filename'] = host_config['identityfile']

        if 'port' in host_config:
            cfg['port'] = int(host_config['port'])

        if 'proxycommand' in host_config:
            cfg['sock'] = ProxyCommand(host_config['proxycommand'])

        elif 'proxyjump' in host_config:
            hops = host_config['proxyjump'].split(',')
            sock = None

            for i, hop in enumerate(hops):
                hop_hostname, hop_config = self.derive_shorthand(hop)
                logger.debug('SSH ProxyJump through %s:%s', hop_hostname, hop_config['port'])

                c = SSHClient()
                c.connect(hop_hostname, sock=sock, **hop_config)

                if i == len(hops) - 1:
                    target = hostname
                    target_config = {'port': cfg['port']}
                else:
                    target, target_config = self.derive_shorthand(hops[i + 1])

                sock = c.gateway(hostname, cfg['port'], target, target_config['port'])
            cfg['sock'] = sock

        return hostname, cfg, forward_agent, missing_host_key_policy

    @staticmethod
    def derive_shorthand(host_string):
        shorthand_config = {}
        user_hostport = host_string.rsplit('@', 1)
        hostport = user_hostport.pop()
        user = user_hostport[0] if user_hostport and user_hostport[0] else None
        if user:
            shorthand_config['username'] = user

        # IPv6: can't reliably tell where addr ends and port begins, so don't
        # try (and don't bother adding special syntax either, user should avoid
        # this situation by using port=).
        if hostport.count(':') > 1:
            hostname = hostport
        # IPv4: can split on ':' reliably.
        else:
            host_port = hostport.rsplit(':', 1)
            hostname = host_port.pop(0) or None
            if host_port and host_port[0]:
                shorthand_config['port'] = int(host_port[0])

        base_config = get_ssh_config().lookup(hostname)

        config = {
            'port': base_config.get('port', 22),
            'username': base_config.get('username'),
        }
        config.update(shorthand_config)

        return hostname, config
