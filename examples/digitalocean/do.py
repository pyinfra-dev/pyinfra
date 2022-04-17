#!/usr/bin/env python

# Simple script to show interactions with digitalocean
# using python-digitalocean

import os
import sys

import digitalocean

token = ""
try:
    token = os.environ["DIGITALOCEAN_TOKEN"]
except KeyError:
    print("Error: Set the environment variable DIGITALOCEAN_TOKEN")
    sys.exit(1)


def arg_check():
    if len(sys.argv) < 2:
        print("Warning: No operation given.")
        print("Usage: do.py [ add | drop | list ]")
        sys.exit(1)


def list():
    manager = digitalocean.Manager(token=token)
    my_droplets = manager.get_all_droplets()
    for droplet in my_droplets:
        ip = ""
        try:
            ip = droplet.networks["v4"][0]["ip_address"]
        except IndexError:
            pass
        print(droplet.name, droplet.status, ip)


def add():
    manager = digitalocean.Manager(token=token)
    keys = manager.get_all_sshkeys()
    droplet = digitalocean.Droplet(
        token=token,
        name="Example",
        region="sfo2",
        image="ubuntu-18-04-x64",
        size_slug="512mb",
        ssh_keys=keys,
        private_networking="",
        backups=False,
    )
    droplet.create()


def drop():
    manager = digitalocean.Manager(token=token)
    my_droplets = manager.get_all_droplets()
    for droplet in my_droplets:
        if droplet.name == "Example":
            print("destroying droplet:{}".format(droplet.name))
            droplet.destroy()


if __name__ == "__main__":
    arg_check()
    op = sys.argv[1]
    if op == "list":
        list()
    elif op == "add":
        add()
    elif op == "drop":
        drop()
    else:
        print("invalid arg")
