from pyinfra import host
from pyinfra.facts.server import LinuxName
from pyinfra.operations import files, init, server

SUDO = True

if host.get_fact(LinuxName) in ['Ubuntu']:

    server.user(
        name='Ensure myweb user exists',
        user='myweb',
        shell='/bin/bash',
    )

    files.directory(
        name='Ensure /web exists',
        path='/web',
        user='myweb',
        group='myweb',
    )

    files.template(
        name='Create script to run inside the service',
        src='templates/myweb.sh.j2',
        dest='/usr/local/bin/myweb.sh',
        mode='755',
        user='myweb',
        group='myweb',
    )

    files.template(
        name='Create service file',
        src='templates/myweb.service.j2',
        dest='/etc/systemd/system/myweb.service',
        mode='755',
        user='root',
        group='root',
    )

    files.template(
        name='Create index.html',
        src='templates/index.html.j2',
        dest='/web/index.html',
    )

    files.link(
        name='Create link /web/index.htm that points to /web/index.html',
        path='/web/index.htm',
        target='/web/index.html',
    )

    # Note: Allowing sudo to python is not a very secure.
    files.line(
        name='Ensure myweb can run /usr/bin/python3 without password',
        path='/etc/sudoers',
        line=r'myweb .*',
        replace='myweb ALL=(ALL) NOPASSWD: /usr/bin/python3',
    )

    server.shell(
        name='Check that sudoers file is ok',
        commands='visudo -c',
    )

    init.systemd(
        name='Restart and enable myweb',
        service='myweb',
        running=True,
        restarted=True,
        enabled=True,
        daemon_reload=True,
    )

    server.wait(
        name='Wait until myweb starts',
        port=80,
    )
