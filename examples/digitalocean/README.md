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

8. Interact with your new `Example` droplet:

    pyinfra --user root 138.68.59.39 exec -- echo hello

9. Drop the `Example` droplet:

    ./do.py drop
