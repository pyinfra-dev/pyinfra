Pip
---


Manage pip packages. Compatible globally or inside a virtualenv.

:code:`pip.packages`
~~~~~~~~~~~~~~~~~~~~

Manage pip packages.

.. code:: python

    pip.packages(packages=None, present=True, requirements=None, virtualenv=None)

+ **packages**: list of packages to ensure
+ **present**: whether the packages should be installed
+ **requirements**: location of requirements file to install
+ **virtualenv**: root directory of virtualenv to work in

