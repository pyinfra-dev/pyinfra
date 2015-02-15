from pyinfra.api import operation


@operation
def repo(source, target, branch='master', update=True):
    return []
