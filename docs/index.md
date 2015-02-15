# pyinfra

pyinfra is a deployment tool. It's configured in Python; to make a deploy you need a `config.py` and `deploy.py`. Configs contain some basic information about the group of servers you wish to deploy to. The deploy script contains **operations**, which lie at the core of pyinfra.

To deploy, you just: `pyinfra -c config.py deploy.py`
