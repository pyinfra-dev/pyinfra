from pyinfra.api import command


@command
def repo(source, target, branch='master', update=True):
    return 'GIT'
