from pyinfra import host
from pyinfra.facts.server import LinuxName
from pyinfra.operations import apt, files

SUDO = True

if host.get_fact(LinuxName) == 'Ubuntu':

    apt.packages(
        name='Install wget',
        packages=['wget'],
        update=True,
    )

# Full URL:
# http://dl-cdn.alpinelinux.org/alpine/v3.11/releases/x86_64/alpine-netboot-3.11.2-x86_64.tar.gz
# sha256 is here
# http://dl-cdn.alpinelinux.org/alpine/v3.11/releases/x86_64/alpine-netboot-3.11.2-x86_64.tar.gz.sha256
tarfile = 'alpine-netboot-3.11.2-x86_64.tar.gz'
tarfile_full_path = '/tmp/{}'.format(tarfile)
sha256file = tarfile + '.sha256'
sha256file_full_path = '/tmp/{}'.format(sha256file)

# TODO: Check if download was successful
files.download(
    name='Download `{}`'.format(tarfile),
    src='http://dl-cdn.alpinelinux.org/alpine/v3.11/releases/x86_64/{}'.format(tarfile),
    dest=tarfile_full_path,
)

files.download(
    name='Download `{}`'.format(sha256file),
    src='http://dl-cdn.alpinelinux.org/alpine/v3.11/releases/x86_64/{}'.format(sha256file),
    dest=sha256file_full_path,
)
