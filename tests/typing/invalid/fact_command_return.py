from pyinfra.api import FactBase


class ReturnsInt(FactBase[str]):
    def command(self) -> int:
        return 1


class ReturnsOptional(FactBase[str]):
    def command(self, path: str) -> str | None:
        return None
