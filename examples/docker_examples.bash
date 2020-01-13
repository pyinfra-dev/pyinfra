#!/usr/bin/env bash

# Miscellaneous runs of pyinfra examples
# Primarily for showing different ways of running pyinfra,
# but also helps with testing/validation

pyinfra @docker/ubuntu apt.packages iftop sudo=true update=true

pyinfra @docker/alpine apk.py

pyinfra @docker/ubuntu apt.py npm.py

pyinfra @docker/ubuntu,@docker/centos,@docker/alpine git.py gem.py pip.py

pyinfra @docker/archlinux pacman.py

pyinfra @docker/centos files.py dnf.py server.py

pyinfra @docker/centos yum.py

