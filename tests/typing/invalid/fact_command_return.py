from pyinfra.api import ShellFact


class ReturnsInt(ShellFact[str]):
    def command(self) -> int:
        return 1


class ReturnsOptional(ShellFact[str]):
    def command(self, path: str) -> str | None:
        return None
