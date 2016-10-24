Lxd
---


The LXD modules manage LXD containers

:code:`lxd.container`
~~~~~~~~~~~~~~~~~~~~~

Manage LXD containers.

.. code:: python

    lxd.container(name, present=True, image=ubuntu:16.04)

Note: does not check if an existing container is based on the specified
image.

+ **name**: name of the container
+ **image**: image to base the container on
+ **present**: whether the container should be present or absent

