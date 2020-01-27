# Compatibility

``pyinfra`` aims to be compatible with all Unix-like operating systems and is currently tested against:

+ Ubuntu 16/18
+ Debian 8/9
+ CentOS 6/7/8
+ Fedora 24
+ OpenBSD 6
+ macOS 10.14 (with [`@local` connector](connectors.html#local))
+ Docker (with [`@docker` connector](connectors.html#docker))

In general, the only requirement (beyond a SSH server) on the remote side is shell access. POSIX commands are used where possible for facts and operations, so most of the ``server`` and ``files`` operations should work anywhere POSIX.
