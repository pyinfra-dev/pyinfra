'''
This file as originally part of the "sshuserclient" pypi package. The GitHub
source has now vanished (https://github.com/tobald/sshuserclient).
'''

from os import path

from paramiko import (
    AutoAddPolicy,
    ProxyCommand,
    SSHClient as ParamikoClient,
)
from paramiko.agent import AgentRequestHandler

from pyinfra import logger
from pyinfra.api.util import memoize

from .config import SSHConfig


@memoize
def get_ssh_config():
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

    def connect(self, hostname, _pyinfra_force_forward_agent=None, **kwargs):
        hostname, config, forward_agent = self.parse_config(hostname, kwargs)
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

    def parse_config(self, hostname, initial_cfg=None):
        cfg = {'port': 22}
        cfg.update(initial_cfg or {})

        forward_agent = False

        ssh_config = get_ssh_config()
        if not ssh_config:
            return hostname, cfg, forward_agent

        host_config = ssh_config.lookup(hostname)
        forward_agent = host_config.get('forwardagent') == 'yes'

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
                c.set_missing_host_key_policy(AutoAddPolicy())
                c.connect(hop_hostname, sock=sock, **hop_config)

                if i == len(hops) - 1:
                    target = hostname
                    target_config = {'port': cfg['port']}
                else:
                    target, target_config = self.derive_shorthand(hops[i + 1])

                sock = c.gateway(hostname, cfg['port'], target, target_config['port'])
            cfg['sock'] = sock

        return hostname, cfg, forward_agent

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
