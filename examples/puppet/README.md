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

    pyinfra inv.py step1.py

3. Sign agent and do a puppet run

    pyinfra inv.py step2.py

4. Deploy a manifest to master and do a puppet run on agent

    pyinfra inv.py step3.py

5. Do an adhoc puppet run on just the agents:

    pyinfra inv.py --limit agent_servers puppet.agent sudo=true use_sudo_login=true

6. Misc pyinfra commands (showing various options):

    # If running from vagrant
    pyinfra @vagrant/agent fact rpm_packages
    pyinfra @vagrant/agent yum.packages vim sudo=True present=True
    pyinfra @vagrant/agent init.systemd httpd sudo=True running=False

or

    pyinfra inv.py --limit master_servers fact rpm_packages
    pyinfra inv.py yum.packages vim sudo=True present=True
    pyinfra inv.py --limit agent_servers init.systemd httpd sudo=True running=False

    # If running against digital ocean instances
    pyinfra do_inv.py --limit master_servers fact rpm_packages
    pyinfra do_inv.py yum.packages vim sudo=True present=True
    pyinfra do_inv.py --limit agent_servers init.systemd httpd sudo=True running=False

7. Destroy vagrant VMs when done with demo

    vagrant destroy
