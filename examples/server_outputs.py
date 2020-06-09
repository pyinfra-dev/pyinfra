from pyinfra.operations import server

SUDO = True

# Various different outputs

# To see output need to run pyinfra with '-v'
a = server.script(
    {'Hello'},
    'files/hello.bash',
)
print('a', a)

# To see output need to run pyinfra with '-v'
b = server.shell(
    {'Say Hello'},
    'echo Hello',
)
print('b', b)
