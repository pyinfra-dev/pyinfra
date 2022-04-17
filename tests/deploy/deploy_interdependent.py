from pyinfra.operations import apt, brew, files, git, server, systemd

# Add/remove/add same file
files.file(
    path="/somefile",
)

files.file(
    path="/somefile",
    present=False,
)

files.file(
    path="/somefile",
)

# Add/remove/add same directory
files.directory(
    path="/somedir",
)

files.directory(
    path="/somedir",
    present=False,
)

files.directory(
    path="/somedir",
)

# Add/remove/add same link
files.link(
    path="/somelink",
    target="/elsewhere",
)

files.link(
    path="/somelink",
    present=False,
)

files.link(
    path="/somelink",
    target="/elsewhere",
)


# Add/remove/add same user
server.user(
    user="someuser",
)

server.user(
    user="someuser",
    present=False,
)

server.user(
    user="someuser",
)

# Add/remove/add same group
server.group(
    group="somegroup",
)

server.group(
    group="somegroup",
    present=False,
)

server.group(
    group="somegroup",
)


# Add/remove same apt repo
apt.repo(
    src="deb https://download.virtualbox.org/virtualbox/debian bionic contrib",
)

apt.repo(
    src="deb https://download.virtualbox.org/virtualbox/debian bionic contrib",
    present=False,
)

# Add/remove same apt package
apt.packages(
    packages=["htop"],
)

apt.packages(
    packages=["htop"],
    present=False,
)


# Add/remove/add same brew tap
brew.tap(
    "sometap/somewhere",
)

brew.tap(
    "sometap/somewhere",
    present=False,
)

brew.tap(
    "sometap/somewhere",
)


# Add/change/add same git config
git.config(
    "somekey",
    "somevalue",
)

git.config(
    "somekey",
    "someothervalue",
)

git.config(
    "somekey",
    "somevalue",
)


# Start/stop/start same systemd service
systemd.service(
    "someservice",
)

systemd.service(
    "someservice",
    running=False,
)

systemd.service(
    "someservice",
)
