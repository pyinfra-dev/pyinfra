# Ssh demo
Spin up two VMs and ssh a file from one to the other.
Also demos how you can use a group (like "@vagrant").

# To try it out

Be sure to be in this directory when running these commands.

To try out:

1. Spin up VMs:

    vagrant up

2. To see facts from all "@vagrant" instances, run:

    pyinfra @vagrant fact ipv4_addresses

3. Run the ssh demo deploys:

    # TODO: had to break into 3 separate deploys to go in sequence.
    # Is there a better way?
    pyinfra @vagrant ssh_demo1.py
    pyinfra @vagrant/two ssh_demo2.py
    pyinfra @vagrant/one ssh_demo3.py

4. Clean up tmp file

    rm /tmp/one_vagrant_id_rsa.pub

5. Destroy VMs

    vagrant destroy
