# Checked with: mypy --disallow-any-expr --follow-imports=silent tests/typing/valid/deploy_decorator.py
from typing_extensions import assert_type

from pyinfra.api import deploy
from pyinfra.operations import server


@deploy("Install things")
def install_things(packages: list[str], update: bool = False) -> None:
    server.shell(commands=[f"install {package}" for package in packages])


@deploy()
def count_things(path: str) -> int:
    server.shell(commands=[f"ls {path}"])
    return 1


assert_type(install_things(packages=["nginx"], update=True), None)
assert_type(install_things(packages=["nginx"], _sudo=True, _sudo_user="pyinfra"), None)
assert_type(count_things(path="/tmp"), int)
assert_type(count_things(path="/tmp", _sudo=True), int)
