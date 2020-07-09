'''
This example demonstrates how pyinfra executes for loops by default and provides
an example of looping while preserving the order.
'''

from pyinfra import state
from pyinfra.operations import server

SUDO = True

items = ['a', 'b', 'c']


# This loop will be executed as:
# > item: a
# > item: b
# > item: c
# > end item: a
# > end item: b
# > end item: c
for item in items:
    server.shell(name='item: {0}'.format(item), commands='hi')
    server.shell(name='end item: {0}'.format(item), commands='hi')


# This loop will be executed as:
# > item: a
# > end item: a
# > item: b
# > end item: b
# > item: c
# > end item: c
with state.preserve_loop_order(items) as loop_items:
    for item in loop_items():
        server.shell(name='item: {0}'.format(item), commands='hi')
        server.shell(name='end item: {0}'.format(item), commands='hi')
