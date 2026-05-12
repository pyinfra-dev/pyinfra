from pyinfra.api import operation


@operation()
def dummy_op(arg1, arg2, state=None, host=None):
    yield f"echo arg1={arg1} arg2={arg2}"
