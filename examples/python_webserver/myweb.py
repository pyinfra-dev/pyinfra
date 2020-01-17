from pyinfra import host
from pyinfra.modules import files, init, server

SUDO = True

if host.fact.linux_name in ['Ubuntu']:

    server.user(
        {'Ensure myweb user exists'},
        'myweb',
        shell='/bin/bash',
    )

    files.directory(
        {'Ensure /web exists'},
        '/web',
        user='myweb',
        group='myweb',
    )

    files.template(
        {'Create script to run inside the service'},
        'templates/myweb.sh.j2',
        '/usr/local/bin/myweb.sh',
        mode='755',
        user='myweb',
        group='myweb',
    )

    files.template(
        {'Create service file'},
        'templates/myweb.service.j2',
        '/etc/systemd/system/myweb.service',
        mode='755',
        user='root',
        group='root',
    )

    files.template(
        {'Create index.html'},
        'templates/index.html.j2',
        '/web/index.html',
    )

    files.link(
        {'Create link /web/index.htm that points to /web/index.html'},
        '/web/index.htm',
        '/web/index.html',
    )

    files.line(
        {'Ensure myweb can run /usr/bin/python3 without password'},
        '/etc/sudoers',
        r'myweb .*',
        replace='myweb ALL=(ALL) NOPASSWD: /usr/bin/python3',
    )

    server.shell(
        {'Check that sudoers file is ok'},
        'visudo -c',
    )

    init.systemd(
        {'Restart and enable myweb'},
        'myweb',
        running=True,
        restarted=True,
        enabled=True,
        daemon_reload=True,
    )

    server.wait(
        {'Wait until myweb starts'},
        port=80,
    )
