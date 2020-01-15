from pyinfra import host
from pyinfra.modules import apt, files, init, server

# Create a simple PXE server that allows you to boot Ubuntu Desktop
# Used https://linuxhint.com/pxe_boot_ubuntu_server/ as starting point.
#
# To try this out: (change ip to be on your local network)
# 1. Modify the ../Vagrantfile and add this line the ubuntu18
#    ubuntu.vm.network "public_network", ip: "192.168.0.240"
# 2. Spin up an Ubuntu18 instance ('cd ..; vagrant up ubuntu18')
# 3. Modify the network to be "Bridged Networking/Autodetect" after VM has been booted.
# 4. Run this deploy:
#    pyinfra  --user vagrant --password vagrant 192.168.0.240 pxe_infra.py
#
# Test that it actually works from VMware by:
#  1. Create a new custom virtual machine
#  2. Linux/Other Linux 3.x kernel 64-bit
#  3. Legacy BIOS
#  4. Accept defaults for VM
#  5. Go into Network Adapter, and change to "Bridged Networking/Autodetect"
#
# Notes:
# 1. This deploy requires two files from templates/ directory:
#    default.j2 and dnsmask.conf.j2
# 2. For troubleshooting, connect to pxe_server and see /var/log/syslog or
#    run "systemctl status dnsmasq" or
#    run "systemctl status nfs-kernel-server".
# 3. The vagrant box does not have ufw (firewall) enabled. You should/may.

SUDO = True

# If you change pxe_server value then check/change ../Vagrantfile
pxe_server = '192.168.0.240'
interface = 'eth1'
dhcp_start = '192.168.0.220'
dhcp_end = '192.168.0.230'

# setup pxe infra

if host.fact.linux_name == 'Ubuntu':

    apt.packages(
        {'Install packages'},
        ['dnsmasq', 'nfs-kernel-server', 'syslinux', 'pxelinux'],
        update=True,
    )

    # configure dnsmasq
    files.template(
        {'Create dnsmasq configuration file'},
        'templates/dnsmasq.conf.j2',
        '/etc/dnsmasq.conf',
        pxe_server=pxe_server,
        interface=interface,
        dhcp_start=dhcp_start,
        dhcp_end=dhcp_end,
    )

    # create necessary directories
    dirs = [
        '/netboot/tftp',
        '/netboot/nfs',
        '/netboot/tftp/pxelinux.cfg',
        '/mnt',
        '/netboot/nfs/ubuntu1804',
        '/netboot/tftp/ubuntu1804',
    ]
    for dir in dirs:
        files.directory(
            {'Ensure the directory `{}` exists'.format(dir)},
            dir,
        )

    # TODO: how to see if the service started ok
    init.d(
        {'Restart and enable dnsmasq'},
        'dnsmasq',
        restarted=True,
        enabled=True,
    )

    files.line(
        {'Ensure /netboot/nfs is in /etc/exports'},
        '/etc/exports',
        r'/netboot/nfs .*',
        replace='/netboot/nfs *(ro,sync,no_wdelay,insecure_locks,'
        'no_root_squash,insecure,no_subtree_check)',
    )

    server.shell(
        {'Make share available'},
        'exportfs -a',
    )

    if not host.fact.file('/netboot/tftp/pxelinux.0'):
        server.shell(
            {'Copy pxelinux.0 '},
            'cp -v /usr/lib/PXELINUX/pxelinux.0 /netboot/tftp/',
        )

    files_to_create = ['ldlinux.c32', 'libcom32.c32', 'libutil.c32', 'vesamenu.c32']
    for file in files_to_create:
        if not host.fact.file('/netboot/tftp/{}'.format(file)):
            server.shell(
                {'Copy `{}` to /net/tftp directory'.format(file)},
                'cp -v /usr/lib/syslinux/modules/bios/{} /netboot/tftp/'.format(file),
            )

    files.template(
        {'Create a templated file'},
        'templates/default.j2',
        '/netboot/tftp/pxelinux.cfg/default',
        pxe_server=pxe_server,
    )

    # TODO: check sha
    # TODO: check pgp?
    iso = 'ubuntu-18.04.3-desktop-amd64.iso'
    iso_full_path = '/tmp/{}'.format(iso)
    files.download(
        {'Download `{}` iso'.format(iso)},
        'http://releases.ubuntu.com/18.04/{}'.format(iso),
        iso_full_path,
    )

    server.shell(
        {'Mount iso'},
        'mount -o loop {} /mnt'.format(iso_full_path),
    )

    server.shell(
        {'Copy contents of ISO to mount'},
        'cp -Rfv /mnt/* /netboot/nfs/ubuntu1804/',
    )

    # copy vmlinuz and initrd files
    init_files = ['vmlinuz', 'initrd']
    for file in init_files:
        if not host.fact.file('/netboot/tftp/ubuntu1804/{}'.format(file)):
            server.shell(
                {'Copy `{}` file'.format(file)},
                'cp -v /netboot/nfs/ubuntu1804/casper/{} '
                '/netboot/tftp/ubuntu1804/{}'.format(file, file),
            )

    server.shell(
        {'Set permissions'},
        'chmod -Rfv 777 /netboot',
    )

    server.shell(
        {'Unmount /mnt'},
        'umount /mnt',
    )

    init.d(
        {'Restart and enable nfs'},
        'nfs-kernel-server',
        restarted=True,
        enabled=True,
    )
