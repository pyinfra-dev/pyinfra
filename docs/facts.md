# Facts

pyinfra uses **facts** to determine the existing state of a remote server. Operations use this information to generate commands which alter the state. Facts are read-only and are populated at the beginning of the deploy.

Facts can be executed/tested via the command line:

```sh
# Example how to get multiple facts from a server myhost.com
pyinfra myhost.com fact server.Date server.Hostname ...
```

If you want to pass an argument to a fact, pass it with `key=value`. For example:

```sh
# See if the package 'openssh-server' is installed servers myhost.com and myhost2.com
pyinfra myhost.com,myhost2.com fact deb.DebPackage name=openssh-server
```

Multiple facts with arguments may be called like so:

```sh
pyinfra @local fact files.File path=setup.py files.File path=anotherfile.txt
```

You can leverage facts within [operations](using-operations.md) like this:

```python
from pyinfra import host
from pyinfra.facts.server import LinuxName

if host.get_fact(LinuxName) == 'Ubuntu':
    apt.packages(...)
```

**Want a new fact?** Check out [the writing facts guide](api/facts.md).

--8<-- "facts-cards.html"
