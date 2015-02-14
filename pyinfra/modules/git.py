from pyinfra.api import op


@op
def repo(source, target, branch='master', update=True):
    return []
