from pyinfra.operations import server


async def run():
    await server.shell(
        name="Async main operation",
        commands="echo hello async deploy",
    )

    await server.shell(
        name="Async second operation",
        commands="echo second async deploy",
    )
