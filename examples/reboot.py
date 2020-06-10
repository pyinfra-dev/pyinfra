from pyinfra.operations import init, server

SUDO = True


init.systemd(
    {'Disable ufw'},
    'ufw',
    running=False,
    enabled=False,
)

server.reboot(
    {'Reboot the server'},
    delay=5,
    timeout=30,
)

server.shell(
    {'Ensure ufw is not running'},
    'systemctl status ufw',
    success_exit_codes=[3],
)
