from pyinfra import host
from pyinfra.facts.server import LinuxName
from pyinfra.operations import apt, files, init, server

SUDO = True

# If you change pxe_server value below then check/change Vagrantfile
pxe_server = '192.168.0.240'
dns_server = '192.168.0.1'
interface = 'eth1'
dhcp_start = '192.168.0.220'
dhcp_end = '192.168.0.230'

# setup pxe infra

if host.get_fact(LinuxName) == 'Ubuntu':

    apt.packages(
        name='Install packages',
        packages=['dnsmasq'],
        update=True,
    )

    tftp_dir = '/srv/tftp'
    files.directory(
        name='Ensure the `{}` exists'.format(tftp_dir),
        path=tftp_dir,
    )

    tar_file = 'netboot.tar.gz'
    tar_file_full_path = '/tmp/{}'.format(tar_file)
    files.download(
        name='Download `{}`'.format(tar_file),
        src='http://archive.ubuntu.com/ubuntu/dists/bionic-updates/main/'
        'installer-amd64/current/images/netboot/{}'.format(tar_file),
        dest=tar_file_full_path,
    )

    server.shell(
        name='Extract files from tar file',
        commands='tar -xvzf {} -C {}'.format(tar_file_full_path, tftp_dir),
    )

    server.shell(
        name='Change permissions',
        commands='chown -R nobody:nogroup {}'.format(tftp_dir),
    )

    uefi_file = 'grubnetx64.efi.signed'
    uefi_full_path = '{}/{}'.format(tftp_dir, uefi_file)
    files.download(
        name='Download `{}`'.format(uefi_file),
        src='http://archive.ubuntu.com/ubuntu/dists/trusty/main/'
        'uefi/grub2-amd64/current/grubnetx64.efi.signed',
        dest=uefi_full_path,
    )

    grub_dir = '{}/grub'.format(tftp_dir)
    files.directory(
        name='Ensure the `{}` exists'.format(grub_dir),
        path=grub_dir,
    )

    files.template(
        name='Create a templated file',
        src='templates/grub.cfg.j2',
        dest='{}/grub.cfg'.format(grub_dir),
    )

    # configure dnsmasq
    files.template(
        name='Create dnsmasq configuration file',
        src='templates/dnsmasq.conf.j2',
        dest='/etc/dnsmasq.conf',
        pxe_server=pxe_server,
        dns_server=dns_server,
        interface=interface,
        dhcp_start=dhcp_start,
        dhcp_end=dhcp_end,
        tftp_dir=tftp_dir,
    )

    init.systemd(
        name='Restart and enable dnsmasq',
        service='dnsmasq',
        running=True,
        restarted=True,
        enabled=True,
    )
