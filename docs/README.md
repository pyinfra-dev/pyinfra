
# pyinfra

pyinfra is a deployment tool. Deploys can be executed via a [CLI](./quick_start.md) or [Python API](./api/README.md). In both cases a two things are needed: an **inventory** and a list of **operations**. The inventory manages and groups the target hosts/data and the operations define the desired state of the target host. Using these a [one-or-two pass deploy](./deploy_process.md) is executed.

pyinfra targets POSIX compatability and is currently tested against Ubuntu, Debian, CentOS & OpenBSD.

+ [Quick start](./quick_start.md)
+ [Modules list](./modules/README.md)
+ [Example deploy](../example)
+ [API Example](example/api_deploy.py)
