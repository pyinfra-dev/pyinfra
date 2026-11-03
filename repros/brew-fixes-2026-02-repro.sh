#! /bin/bash
pyinfra --version
brew list --versions | grep openssl
pyinfra @local fact brew.BrewPackages |& grep openssl -A 3
pyinfra --dry @local brew.packages openssl@3.6.1
