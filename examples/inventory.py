# pyinfra
# File: example/inventories/example.py
# Desc: example inventory, not actually used anywhere

# Define a group
web_servers = [
    "web-01.company.net",
    "web-02.company.net",
]


# Define another group
db_servers = [
    "db-01.company.net",
    # Define hosts with extra, per-host, data
    ("db-02.company.net", {"hello": "world"}),
]
