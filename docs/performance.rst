Performance
===========

.. code:: shell

    ### pyinfra Performance Tests
    --> Running with 5 hosts

    --> Running test: pyinfra -i deploy/inventory.py deploy/deploy.py
    --> Removing any existing hosts
    --> Bringing up new hosts
    --> Executing first run...
    --> Executing second run...

    --> First complete in 2.139081000 seconds
    --> Second complete in 1.567480000 seconds

    --> Running test: ansible-playbook -i playbook/inventory.py playbook/playbook.yaml
    --> Removing any existing hosts
    --> Bringing up new hosts
    --> Executing first run...
    --> Executing second run...

    --> First complete in 2.061040000 seconds
    --> Second complete in 1.704296000 seconds

    <-- All tests complete!


.. code:: shell

    ### pyinfra Performance Tests
    --> Running with 50 hosts

    --> Running test: pyinfra -i deploy/inventory.py deploy/deploy.py
    --> Removing any existing hosts
    --> Bringing up new hosts
    --> Executing first run...
    --> Executing second run...

    --> First complete in 23.637547000 seconds
    --> Second complete in 14.014011000 seconds

    --> Running test: ansible-playbook -i playbook/inventory.py playbook/playbook.yaml
    --> Removing any existing hosts
    --> Bringing up new hosts
    --> Executing first run...
    --> Executing second run...

    --> First complete in 23.942866000 seconds
    --> Second complete in 20.004602000 seconds

    <-- All tests complete!
