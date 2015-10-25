Pip
---


Manage pip packages. Compatible globally or inside a virtualenv.

:code:`pip.packages`
~~~~~~~~~~~~~~~~~~~~
.. code:: python

    pip.packages(packages=None, present=True, requirements=None, venv=None)

Manage pip packages. Options:

+ **packages**: list of packages to ensure
+ **present**: whether the packages should be installed
+ **requirements**: location of requirements file to install
+ **venv**: root directory of virtualenv to work in

