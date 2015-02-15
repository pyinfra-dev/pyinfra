# pyinfra example

The example requires a recent version of Vagrant to be installed (as test machines).

```sh
vagrant up

# An example deploy script
pyinfra -c config.py deploy.py

# Example fact output
pyinfra -c config.py facts.py
```
