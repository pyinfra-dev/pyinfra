hosts = (
    [
        "somehost",
        ("anotherhost", {"ssh_port": 1022}),
    ],
    {},
)

generator_hosts = (host for host in ("hosta", "hostb"))
