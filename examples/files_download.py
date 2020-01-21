from pyinfra import host
from pyinfra.modules import apt, files

SUDO = True

if host.fact.linux_name == 'Ubuntu':

    apt.packages(
        {'Install wget'},
        ['wget'],
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
    {'Download `{}`'.format(tarfile)},
    'http://dl-cdn.alpinelinux.org/alpine/v3.11/releases/x86_64/{}'.format(tarfile),
    tarfile_full_path,
)

files.download(
    {'Download `{}`'.format(sha256file)},
    'http://dl-cdn.alpinelinux.org/alpine/v3.11/releases/x86_64/{}'.format(sha256file),
    sha256file_full_path,
)
