# pyinfra example

The example requires a recent version of Vagrant to be installed. Usage:

```sh
vagrant up

# Run with Vagrant inventory & deploy file
pyinfra @vagrant deploy.py
```

Key files:

+ [**deploy.py**](deploy.py) contains the operations to run on the remote hosts


## API Example

+ [**api_deploy.py**](api_deploy.py) API based example
