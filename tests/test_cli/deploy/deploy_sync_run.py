from pyinfra.operations import server


def run():
    server.shell(
        name="Sync run main operation",
        commands="echo hello sync run deploy",
    )

    server.shell(
        name="Sync run second operation",
        commands="echo second sync run deploy",
    )
