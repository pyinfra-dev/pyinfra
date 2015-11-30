Performance
===========

.. code:: shell

    ### pyinfra Performance Tests
    --> Running with 5 hosts

    --> Running test: pyinfra -i deploy/inventory.py deploy/deploy.py
    --> Removing any existing hosts
    --> Bringing up new hosts
    --> Sleeping for 20s
    --> Executing first run...
    --> Executing second run...

    --> First complete in 2.498434000 seconds
    --> Second complete in 1.927552000 seconds

    --> Running test: ansible-playbook -i playbook/inventory.py playbook/playbook.yaml
    --> Removing any existing hosts
    --> Bringing up new hosts
    --> Sleeping for 20s
    --> Executing first run...
    --> Executing second run...

    --> First complete in 1.846866000 seconds
    --> Second complete in 1.654313000 seconds

    <-- All tests complete!


.. code:: shell

    ### pyinfra Performance Tests
    --> Running with 25 hosts

    --> Running test: pyinfra -i deploy/inventory.py deploy/deploy.py
    --> Removing any existing hosts
    --> Bringing up new hosts
    --> Sleeping for 20s
    --> Executing first run...
    --> Executing second run...

    --> First complete in 7.047766000 seconds
    --> Second complete in 5.800223000 seconds

    --> Running test: ansible-playbook -i playbook/inventory.py playbook/playbook.yaml
    --> Removing any existing hosts
    --> Bringing up new hosts
    --> Sleeping for 20s
    --> Executing first run...
    --> Executing second run...

    --> First complete in 9.397780000 seconds
    --> Second complete in 8.130766000 seconds

    <-- All tests complete!


.. code:: shell

    ### pyinfra Performance Tests
    --> Running with 50 hosts

    --> Running test: pyinfra -i deploy/inventory.py deploy/deploy.py
    --> Removing any existing hosts
    --> Bringing up new hosts
    --> Sleeping for 20s
    --> Executing first run...
    --> Executing second run...

    --> First complete in 26.231039000 seconds
    --> Second complete in 15.398840000 seconds

    --> Running test: ansible-playbook -i playbook/inventory.py playbook/playbook.yaml
    --> Removing any existing hosts
    --> Bringing up new hosts
    --> Sleeping for 20s
    --> Executing first run...
    --> Executing second run...

    --> First complete in 26.753693000 seconds
    --> Second complete in 20.011880000 seconds

    <-- All tests complete!
