Getting Started
===============

This guide should help describe the basics of deploying stuff with pyinfra. First install pyinfra using pip:

.. code:: bash

    # install pyinfra using pip
    pip install pyinfra

To do something with pyinfra you need two things:

**Inventory**:
    A set of hosts to target and any data/variables. Hosts can be in one or more groups and both groups and hosts can have different data associated with them.

**Operations**:
    Actions to take or state to apply to/on the hosts in the inventory. From simple shell commands to specific state such as "ensure this apt package is installed".


Ad-hoc commands with ``pyinfra``
--------------------------------

Let's start off executing a simple one off shell command. The first argument always specifies the inventory and the following arguments the operations to execute:

.. code:: shell

    # Usage:
    pyinfra INVENTORY OPERATIONS...

    # Execute an arbitrary shell command
    pyinfra my-server.net exec -- echo "hello world"

    # Execute a shell command to a docker container
    pyinfra @docker/ubuntu exec -- bash --version

As you'll see, ``pyinfra`` runs the echo command and prints the output. See the :ref:`available command line options <cli:CLI arguments & options>` and :ref:`examples of ad-hoc commands <cli:Ad-hoc command execution>`.

More examples:

.. code:: shell

    # Ensure a package is installed on a Centos 8 instance
    pyinfra @vagrant/centos8 dnf.packages vim sudo=true

    # Ensure a package is installed on multiple instances
    pyinfra @vagrant/ubuntu18,@vagrant/debian9 apt.packages vim sudo=true

    # Stop a service on a remote host
    pyinfra some_remote_host init.systemd httpd sudo=True running=False


Create a Deploy
---------------

A deploy simply refers to a collection of inventories and operations defined in Python files. Unlike ad-hoc commands, ``pyinfra`` deploys can be saved and reused. Think of a deploy like Ansible's playbook or Chef's cookbook. We'll now replicate the above command line as a deploy.

To get started let's create an ``inventory.py`` containing our hosts to target:

.. code:: python

    # Define groups of hosts as lists
    my_hosts = ['my-server.net']

Now we need a ``deploy.py`` containing our operations to execute:

.. code:: python

    # Import pyinfra modules, each containing operations to use
    from pyinfra.modules import server

    # Run some simple command
    server.shell( # the module.operation
        {'Execute hello world script'},  # This text print in the output of a deploy
operation
        'echo "hello world"',  # the argument(s) to the operation
    )

We can now execute this deploy like so:

.. code:: shell

    # the optional verbose flag '-v' will print the command output
    pyinfra -v inventory.py deploy.py

That's the basics of ``pyinfra``! Possible next steps:

+ If you like to dive right into the code check out `the examples on GitHub <https://github.com/Fizzadar/pyinfra/tree/master/examples>`_
+ You can also read the :doc:`building a deploy guide <./deploys>` which covers pyinfra's deploy features
+ Or :doc:`the CLI user guide <./cli>` which covers ad-hoc usage of ``pyinfra``.


pyinfra from Windows
--------------------

Tested on WindowsServer2019 with python 3.7.

+ Download `Python <https://www.python.org/downloads/windows/>`
  (ex: python-3.7.6-amd64.exe). Install as Administrator and 
  ensure the 'Add Python to PATH' option is selected.)

+ Open a new powershell (as your login user), run:

.. code:: shell

    # install python virtual environment package
    pip install virtualenv

+ Upgrade pip (optional):

.. code:: shell

    # upgrade pip (optional)
    python -m pip install --upgrade pip

+ Create a new python virtual environment:

.. code:: shell

    # create a new python virtual environment
    virtualenv.exe venv

+ Activate the python virtual environment:

.. code:: shell

    # activate the python virtual environment
    .\venv\Scripts\activate

- Install pyinfra:

.. code:: shell

    # install pyinfra using pip
    pip install pyinfra


If you need to build any python packages on Windows, perhaps because one of the 'pip' packages above fails, you may need a c++ compiler. One possible solution is below.

+ Download `Visual Studio Community Edition <https://visualstudio.microsoft.com/downloads/>` and
  install Visual Studio as Administrator. Select the 'Desktop development with C++' option and
  ensure at least these options are selected:

    + "MSVC v142..."
    + "Windows 10 SDK..."
    + "C++ cmake tools for windows"
    + "C++ ATL for latest..."
    + "C++/cli support for v142..."
    + "C++ Modules for v142..."

