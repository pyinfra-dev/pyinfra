from pyinfra.api import operation


@operation
def execute(callback, **kwargs):
    return [(callback, kwargs)]
