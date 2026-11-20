from pyinfra.api import ShellFact, StringCommand


class NoArgs(ShellFact[str]):
    def command(self) -> str:
        return "hostname"


class PositionalArgs(ShellFact[str]):
    def command(self, path: str, depth: int | None = None) -> StringCommand:
        return StringCommand("find", path)


class KeywordOnlyArgs(ShellFact[str]):
    def command(self, *, path: str) -> str | StringCommand:
        return path


class Static(ShellFact[str]):
    @staticmethod
    def command(path: str) -> str:
        return path


command: str = PositionalArgs().command("/etc").get_raw_value() + NoArgs().command()
