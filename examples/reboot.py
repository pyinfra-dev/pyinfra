from pyinfra.operations import init, server


init.systemd(
    name='Disable ufw',
    service='ufw',
    running=False,
    enabled=False,
)

server.reboot(
    name='Reboot the server',
    delay=5,
    timeout=30,
)

server.shell(
    name='Ensure ufw is not running',
    commands='systemctl status ufw',
    success_exit_codes=[3],
)
