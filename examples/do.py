#!/usr/bin/env python

import os
import sys

import digitalocean

token = ''
try:
    token = os.environ['DIGITALOCEAN_TOKEN']
except KeyError:
    print('Error: Set the environment variable DIGITALOCEAN_TOKEN')
    sys.exit(1)

ubuntu = ['pyinfra-misc', 'pyinfra-docker']
centos = ['pyinfra-master', 'pyinfra-agent']
names = centos + ubuntu


def arg_check():
    if len(sys.argv) < 2:
        print('Warning: No operation given.')
        print('Usage: do.py [ up | down | list | create ]')
        sys.exit(1)


def create_inventory():
    manager = digitalocean.Manager(token=token)
    my_droplets = manager.get_all_droplets()
    data = "{'ssh_user': 'root'}"

    main_inventory = open('do_inv.py', 'w')
    puppet_inventory = open('puppet/do_inv.py', 'w')

    for droplet in my_droplets:
        if droplet.name.startswith('pyinfra-'):
            ip = droplet.networks['v4'][0]['ip_address']
            parts = droplet.name.split('-')
            line = "{}_servers = [('{}', {})]\n".format(parts[1], ip, data)
            if parts[1] == 'agent' or parts[1] == 'master':
                puppet_inventory.write(line)
            main_inventory.write(line)
    main_inventory.close()
    puppet_inventory.close()


def list():
    manager = digitalocean.Manager(token=token)
    my_droplets = manager.get_all_droplets()
    for droplet in my_droplets:
        if droplet.name.startswith('pyinfra-'):
            # if still booting there will be no ip address yet
            ip = 'none'
            try:
                ip = droplet.networks['v4'][0]['ip_address']
            except digitalocean.NotFoundError:
                pass
            print(droplet.name, droplet.status, ip)


def up():
    manager = digitalocean.Manager(token=token)
    keys = manager.get_all_sshkeys()
    for name in ubuntu:
        droplet = digitalocean.Droplet(token=token,
                                       name=name,
                                       region='sfo2',
                                       image='ubuntu-18-04-x64',
                                       size_slug='s-2vcpu-2gb',
                                       ssh_keys=keys,
                                       backups=False)
        droplet.create()
    for name in centos:
        droplet = digitalocean.Droplet(token=token,
                                       name=name,
                                       region='sfo2',
                                       image='centos-7-x64',
                                       size_slug='s-2vcpu-2gb',
                                       ssh_keys=keys,
                                       backups=False)
        droplet.create()


def down():
    manager = digitalocean.Manager(token=token)
    my_droplets = manager.get_all_droplets()
    for droplet in my_droplets:
        if droplet.name in names:
            print('destroying droplet:{}'.format(droplet.name))
            droplet.destroy()


if __name__ == '__main__':
    arg_check()
    op = sys.argv[1]
    if op == 'list':
        list()
    elif op == 'up':
        up()
    elif op == 'down':
        down()
    elif op == 'create':
        create_inventory()
