# python webserver
Create a simple python webserver.

Note: This is not intended to be used as a real web server, but merely
to demonstrate various pyinfra operations.

This deploy shows how to add a user, add that user to sudoers,
check that sudoers file is ok, creates a service, and ensures
the service starts.

# To try it out

To try this out:

    pyinfra  --user vagrant --password vagrant 192.168.0.100 myweb.py
