Performance
===========

This page contains a summary of the latest performance tests. The source code for the tests
is available `on GitHub <https://github.com/Fizzadar/pyinfra-performance>`_. You can also view the `full test results <https://github.com/Fizzadar/pyinfra-performance/blob/develop/latest_results.txt>`_.


**5 hosts**

.. code::

    --> Running tests: pyinfra -i deploy/inventory.py deploy/deploy.py
    --> First complete in 2.420728000 seconds
    --> Second complete in 1.946565000 seconds

    --> Running tests: ansible-playbook -i playbook/inventory.py playbook/playbook.yaml -c ssh
    --> First complete in 2.945665000 seconds
    --> Second complete in 1.654146000 seconds

    --> Running tests: ansible-playbook -i playbook/inventory.py playbook/playbook.yaml -c paramiko
    --> First complete in 7.942255000 seconds
    --> Second complete in 8.053086000 seconds


**15 hosts**

.. code::

    --> Running tests: pyinfra -i deploy/inventory.py deploy/deploy.py
    --> First complete in 4.002151000 seconds
    --> Second complete in 3.405913000 seconds

    --> Running tests: ansible-playbook -i playbook/inventory.py playbook/playbook.yaml -c ssh
    --> First complete in 8.137818000 seconds
    --> Second complete in 4.115502000 seconds

    --> Running tests: ansible-playbook -i playbook/inventory.py playbook/playbook.yaml -c paramiko
    --> First complete in 22.373341000 seconds
    --> Second complete in 22.933183000 seconds


**25 hosts**

.. code::

    --> Running tests: pyinfra -i deploy/inventory.py deploy/deploy.py
    --> First complete in 6.508553000 seconds
    --> Second complete in 5.720865000 seconds

    --> Running tests: ansible-playbook -i playbook/inventory.py playbook/playbook.yaml -c ssh
    --> First complete in 14.714010000 seconds
    --> Second complete in 7.110009000 seconds

    --> Running tests: ansible-playbook -i playbook/inventory.py playbook/playbook.yaml -c paramiko
    --> First complete in 39.348739000 seconds
    --> Second complete in 38.424486000 seconds


**50 hosts**

.. code::

    --> Running tests: pyinfra -i deploy/inventory.py deploy/deploy.py
    --> First complete in 14.393754000 seconds
    --> Second complete in 11.465988000 seconds

    --> Running tests: ansible-playbook -i playbook/inventory.py playbook/playbook.yaml -c ssh
    --> First complete in 28.466202000 seconds
    --> Second complete in 13.888249000 seconds

    --> Running tests: ansible-playbook -i playbook/inventory.py playbook/playbook.yaml -c paramiko
    --> First complete in 81.422183000 seconds
    --> Second complete in 80.385777000 seconds
