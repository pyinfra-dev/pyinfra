from pyinfra import host
from pyinfra.modules import apt, files, init, server

SUDO = True

# If you change pxe_server value below then check/change Vagrantfile
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

    init.systemd(
        {'Restart and enable dnsmasq'},
        'dnsmasq',
        running=True,
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
    # iso = 'ubuntu-18.04.3-desktop-amd64.iso'
    iso = 'ubuntu-18.04.3-live-server-amd64.iso'
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

    init.systemd(
        {'Restart and enable nfs'},
        'nfs-kernel-server',
        restarted=True,
        running=True,
        enabled=True,
    )
