from pyinfra.operations import files, server

SUDO = True
FAIL_PERCENT = 0


server.user(
    name='Create the pyinfra user',
    user='pyinfra',
)

files.file(
    name='Create a file as the pyinfra user using sudo',
    path='/home/pyinfra/sudo_testfile',
    sudo_user='pyinfra',
)

files.file(
    name='Create a file as the pyinfra user using su',
    path='/home/pyinfra/su_testfile',
    su_user='pyinfra',
)
