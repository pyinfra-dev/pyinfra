# PXE Server with NFS
Create a simple PXE server that allows you to boot Ubuntu Server
over nfs.

Used https://linuxhint.com/pxe_boot_ubuntu_server/ as starting point.

# To try it out

To try this out:

1. Review the ip address in Vagrantfile. Look for this line:

    ubuntu.vm.network "public_network", ip: "192.168.0.240"

2. Spin up an Ubuntu18 instance

    vagrant up ubuntu18

3. Modify the network to be "Bridged Networking/Autodetect" after VM has been booted.

4. From this directory, run:

    pyinfra  --user vagrant --password vagrant 192.168.0.240 pxe_with_nfs_infra.py

# Testing

Test that it actually works from VMware by:

1. Create a new custom virtual machine
2. Linux/Other Linux 3.x kernel 64-bit
3. Legacy BIOS
4. Accept defaults for VM
5. Go into Network Adapter, and change to "Bridged Networking/Autodetect"

# Notes
1. This deploy requires two files from templates/ directory:
   default.j2 and dnsmasq.conf.j2
2. For troubleshooting, connect to pxe_server and see /var/log/syslog or
   run "systemctl status dnsmasq" or
   run "systemctl status nfs-kernel-server".
3. The vagrant box does not have ufw (firewall) enabled. You should/may.
