# Interact with Digital Ocean
Interact with Digital Ocean

See [python-digitalocean](https://github.com/koalalorenzo/python-digitalocean) and 
[Digital Ocean api](https://developers.digitalocean.com/documentation/v2/)

# To try it out

To try this out:

1. Install python-digital Install Spin up a test VM

    pip install -U python-digitalocean

2. Login to Digital Ocean and visit the [API page](https://cloud.digitalocean.com/account/api/tokens)

3. Click on `Generate New Token`

4. Add the token to your .bashrc file

   export DIGITALOCEAN_TOKEN="xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"

5. Re-source your .bashrc

   source .bashrc

6. List your droplets:

    ./do.py list

7. Create `Example` droplet:

    ./do.py add

8.  Use the ip from the `./do.py list` and wait for the status to change from 'new' to 'active'
   then interact with your new `Example` droplet:

    export do_ip=138.197.214.33
    pyinfra --user root $do_ip exec -- echo hello

    pyinfra --user root $do_ip ../docker_ce.py
    pyinfra --user root $do_ip ../virtualbox/virtualbox.py
    pyinfra --user root $do_ip ../vagrant/vagrant.py

9. Drop the `Example` droplet:

    ./do.py drop
