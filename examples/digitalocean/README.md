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

8. Interact with your new `Example` droplet (be sure to change ip):

    pyinfra --user root 138.68.59.39 exec -- echo hello

    # TODO: Why do I have to to specify `--key` for this next example? 
    # (when I didn't have to create it for the line above)
    pyinfra --user root 64.225.38.33 --key ~/.ssh/id_rsa ../docker_ce.py
    pyinfra --user root 64.225.38.33 --key ~/.ssh/id_rsa ../virtualbox/virtualbox.py
    pyinfra --user root 64.225.38.33 --key ~/.ssh/id_rsa ../vagrant/vagrant.py

9. Drop the `Example` droplet:

    ./do.py drop
