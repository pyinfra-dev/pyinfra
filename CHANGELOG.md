# v0.1.4

+ Enable passing of multiple, comma separated hosts, as inventory
+ Use `getpass`, not `raw_input` for collecting key passwords in CLI mode

# v0.1.3

+ Fix issue when removing users that don't exist


# v0.1.2

+ Improve private key error handling
+ Ask for encrypted private key passwords in CLI mode


# v0.1.1

+ Don't generate set groups when `groups` is an empty list in `server.user`.


# v0.1

+ First versioned release, start of changelog
+ Full docs @ pyinfra.readthedocs.io
+ Core API with CLI built on top
+ Two-step deploy (diff state, exec commands)
+ Compatability tested w/Ubuntu/CentOS/Debian/OpenBSD/Fedora
+ Modules/facts implemented:
    * Apt
    * Files
    * Gem
    * Git
    * Init
    * Npm
    * Pip
    * Pkg
    * Python
    * Server
    * Yum
