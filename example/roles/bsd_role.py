from pyinfra.modules import server, pkg


# OpenBSD packages?
pkg.packages(
    ['py-pip', 'git'],
    sudo=True,
    op='core_packages' # this and above binds these three operations to run as one
)

# add_pkg does not automatically do this
server.shell(
    'ln -sf /usr/local/bin/pip2.7 /usr/local/bin/pip',
    sudo=True
)
