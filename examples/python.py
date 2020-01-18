from pyinfra.modules import python

SUDO = True


def my_callback(state, host, hello=None):
    command = 'echo hello'
    if hello:
        command = command + ' ' + hello
    status, stdout, stderr = host.run_shell_command(state, command=command, sudo=SUDO)
    assert status is True  # ensure the command executed OK
    if 'hello ' not in str(stdout):
        raise Exception('`{}` problem with callback stdout:{} stderr:{}'.format(
            command, stdout, stderr))


python.call(my_callback, hello='world')
