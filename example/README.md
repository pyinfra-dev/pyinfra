# pyinfra example

The example requires a recent version of Vagrant to be installed. Usage:

```sh
vagrant up

# Run with example inventory & deploy files
pyinfra -i inventories/example.py deploy.py
```

Key files:

+ [**deploy.py**](deploy.py) contains the operations to run on the remote hosts
+ [**inventories/example.py**](inventories/example.py) example inventory file for the Vagrant VM's


## API Example

+ [**api_deploy.py**](api_deploy.py) API based example
