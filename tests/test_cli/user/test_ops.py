from pyinfra.api import operation


@operation()
def dummy_op(arg1, arg2, state=None, host=None):
    yield "echo arg1={0} arg2={1}".format(arg1, arg2)
