from pyinfra.operations import apt, files


# Add/remove same file
files.file(
    path='/somefile',
)

files.file(
    path='/somefile',
    present=False,
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
