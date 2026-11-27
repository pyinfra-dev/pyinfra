from pyinfra.api import deploy


@deploy()
def count_things(path: str) -> int:
    return 1


count_things(path="/tmp", _invalid_kwarg=True)

name: str = count_things(path="/tmp")
