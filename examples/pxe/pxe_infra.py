from pyinfra import host
from pyinfra.modules import apt, files, init, server

SUDO = True

# If you change pxe_server value below then check/change Vagrantfile
pxe_server = '192.168.0.240'
dns_server = '192.168.0.1'
interface = 'eth1'
dhcp_start = '192.168.0.220'
dhcp_end = '192.168.0.230'

# setup pxe infra

if host.fact.linux_name == 'Ubuntu':

    apt.packages(
        {'Install packages'},
        ['dnsmasq'],
        update=True,
    )

    tftp_dir = '/srv/tftp'
    files.directory(
        {'Ensure the `{}` exists'.format(tftp_dir)},
        tftp_dir,
    )

    tar_file = 'netboot.tar.gz'
    tar_file_full_path = '/tmp/{}'.format(tar_file)
    files.download(
        {'Download `{}`'.format(tar_file)},
        'http://archive.ubuntu.com/ubuntu/dists/bionic-updates/main/'
        'installer-amd64/current/images/netboot/{}'.format(tar_file),
        tar_file_full_path,
    )

    server.shell(
        {'Extract files from tar file'},
        'tar -xvzf {} -C {}'.format(tar_file_full_path, tftp_dir),
    )

    server.shell(
        {'Change permissions'},
        'chown -R nobody:nogroup {}'.format(tftp_dir),
    )

    # configure dnsmasq
    files.template(
        {'Create dnsmasq configuration file'},
        'templates/dnsmasq.conf.j2',
        '/etc/dnsmasq.conf',
        pxe_server=pxe_server,
        dns_server=dns_server,
        interface=interface,
        dhcp_start=dhcp_start,
        dhcp_end=dhcp_end,
        tftp_dir=tftp_dir,
    )

    init.systemd(
        {'Restart and enable dnsmasq'},
        'dnsmasq',
        running=True,
        restarted=True,
        enabled=True,
    )
