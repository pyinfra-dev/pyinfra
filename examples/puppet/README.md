# Puppet demo
Spin up two VMs: a master and an agent.

Notes:

1. Used [this](https://www.howtoforge.com/tutorial/centos-puppet-master-and-agent/) as
a guide.

2. Does not take any firewalls into account.

# To try it out

Be sure to be in this directory when running these commands.

To try out:

1. Spin up VMs:

    vagrant up

2. Install master and agent

    pyinfra @vagrant step1.py

3. Sign agent and do a puppet run

    # TODO: bug in the puppet.agent() not sourcing the .bash_profile?
    pyinfra @vagrant step2.py

4. Deploy a manifest to master and do a puppet run on agent

    pyinfra @vagrant step3.py

5. Do an adhoc puppet run on just the agent:

    pyinfra @vagrant/agent puppet.agent sudo=true

6. Destroy VMs when done with demo

    vagrant destroy
