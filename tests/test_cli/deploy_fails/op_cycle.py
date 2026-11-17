from pyinfra import host
from pyinfra.operations import server

# a and d run first then second, b second then third, c1 third then first, d1 has one between.
for i in range(2):
    if (host.name[0] in "ad" and i == 0) or (host.name == "c1" and i == 1):
        server.shell(name="first", commands="echo first")

    if host.name == "d1" and i == 0:
        server.shell(name="between", commands="echo between")

    if host.name[0] != "c" and i == 0:
        server.shell(name="second", commands="echo second")

    if host.name[0] in "bc" and i == 0:
        server.user("third", home="/h")
