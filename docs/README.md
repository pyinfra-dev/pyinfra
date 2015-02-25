# pyinfra

pyinfra is a deployment tool. It's configured in Python; to make a deploy you need a `config.py` and `deploy.py`. Configs contain some basic information about the group of servers you wish to deploy to. The deploy script contains **operations**, which lie at the core of pyinfra.

+ [Quick start](./quick_start.md)
+ [Modules list](./modules)

### API/Internals

Subject to _enormous change_ while pyinfra still very much conceptual.

+ [Operations](./operations.md)
+ [Facts](./facts.md)
