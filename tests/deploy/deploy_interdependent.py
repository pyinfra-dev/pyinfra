from pyinfra.operations import apt, files


# Add/remove/add same file
files.file(
    path='/somefile',
)

files.file(
    path='/somefile',
    present=False,
)

files.file(
    path='/somefile',
)

# Add/remove/add same directory
files.directory(
    path='/somedir',
)

files.directory(
    path='/somedir',
    present=False,
)

files.directory(
    path='/somedir',
)

# Add/remove/add same link
files.link(
    path='/somelink',
    target='/elsewhere',
)

files.link(
    path='/somelink',
    present=False,
)

files.link(
    path='/somelink',
    target='/elsewhere',
)


# Add/remove same apt repo
apt.repo(
    src='deb https://download.virtualbox.org/virtualbox/debian bionic contrib',
)

apt.repo(
    src='deb https://download.virtualbox.org/virtualbox/debian bionic contrib',
    present=False,
)

# Add/remove same apt package
apt.packages(
    packages=['htop'],
)

apt.packages(
    packages=['htop'],
    present=False,
)
