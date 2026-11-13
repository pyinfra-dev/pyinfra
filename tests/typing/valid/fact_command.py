from pyinfra.api import FactBase, StringCommand


class NoArgs(FactBase[str]):
    def command(self) -> str:
        return "hostname"


class PositionalArgs(FactBase[str]):
    def command(self, path: str, depth: int | None = None) -> StringCommand:
        return StringCommand("find", path)


class KeywordOnlyArgs(FactBase[str]):
    def command(self, *, path: str) -> str | StringCommand:
        return path


class Static(FactBase[str]):
    @staticmethod
    def command(path: str) -> str:
        return path


command: str = PositionalArgs().command("/etc").get_raw_value() + NoArgs().command()
