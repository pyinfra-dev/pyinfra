from pyinfra import host
from pyinfra.facts.files import File
from pyinfra.facts.server import LinuxName
from pyinfra.operations import apt, files, init, server

SUDO = True

# If you change pxe_server value below then check/change Vagrantfile
pxe_server = '192.168.0.240'
interface = 'eth1'
dhcp_start = '192.168.0.220'
dhcp_end = '192.168.0.230'

# setup pxe infra

if host.get_fact(LinuxName) == 'Ubuntu':

    apt.packages(
        name='Install packages',
        packages=['dnsmasq', 'nfs-kernel-server', 'syslinux', 'pxelinux'],
        update=True,
    )

    # configure dnsmasq
    files.template(
        name='Create dnsmasq configuration file',
        src='templates/dnsmasq.conf.j2',
        dest='/etc/dnsmasq.conf',
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
            name='Ensure the directory `{}` exists'.format(dir),
            path=dir,
        )

    init.systemd(
        name='Restart and enable dnsmasq',
        service='dnsmasq',
        running=True,
        restarted=True,
        enabled=True,
    )

    files.line(
        name='Ensure /netboot/nfs is in /etc/exports',
        path='/etc/exports',
        line=r'/netboot/nfs .*',
        replace='/netboot/nfs *(ro,sync,no_wdelay,insecure_locks,'
        'no_root_squash,insecure,no_subtree_check)',
    )

    server.shell(
        name='Make share available',
        commands='exportfs -a',
    )

    if not host.get_fact(File, path='/netboot/tftp/pxelinux.0'):
        server.shell(
            name='Copy pxelinux.0 ',
            commands='cp -v /usr/lib/PXELINUX/pxelinux.0 /netboot/tftp/',
        )

    files_to_create = ['ldlinux.c32', 'libcom32.c32', 'libutil.c32', 'vesamenu.c32']
    for file in files_to_create:
        if not host.get_fact(File, path='/netboot/tftp/{}'.format(file)):
            server.shell(
                name='Copy `{}` to /net/tftp directory'.format(file),
                commands='cp -v /usr/lib/syslinux/modules/bios/{} /netboot/tftp/'.format(file),
            )

    files.template(
        name='Create a templated file',
        src='templates/default.j2',
        dest='/netboot/tftp/pxelinux.cfg/default',
        pxe_server=pxe_server,
    )

    # TODO: check sha
    # TODO: check pgp?
    # iso = 'ubuntu-18.04.3-desktop-amd64.iso'
    iso = 'ubuntu-18.04.3-live-server-amd64.iso'
    iso_full_path = '/tmp/{}'.format(iso)
    files.download(
        name='Download `{}` iso'.format(iso),
        src='http://releases.ubuntu.com/18.04/{}'.format(iso),
        dest=iso_full_path,
    )

    server.shell(
        name='Mount iso',
        commands='mount -o loop {} /mnt'.format(iso_full_path),
    )

    server.shell(
        name='Copy contents of ISO to mount',
        commands='cp -Rfv /mnt/* /netboot/nfs/ubuntu1804/',
    )

    # copy vmlinuz and initrd files
    init_files = ['vmlinuz', 'initrd']
    for file in init_files:
        if not host.get_fact(File, path='/netboot/tftp/ubuntu1804/{}'.format(file)):
            server.shell(
                name='Copy `{}` file'.format(file),
                commands=(
                    'cp -v /netboot/nfs/ubuntu1804/casper/{} '
                    '/netboot/tftp/ubuntu1804/{}'.format(file, file)
                ),
            )

    server.shell(
        name='Set permissions',
        commands='chmod -Rfv 777 /netboot',
    )

    server.shell(
        name='Unmount /mnt',
        commands='umount /mnt',
    )

    init.systemd(
        name='Restart and enable nfs',
        service='nfs-kernel-server',
        restarted=True,
        running=True,
        enabled=True,
    )
