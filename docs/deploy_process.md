# pyinfra's Deploy Process

When you run pyinfra, something very similar to the following happens:

+ pyinfra initiates SSH connections to each of the remote hosts
+ Your `deploy.py` script is executed once for each host
    * When **operations** are called within the deploy script, they might lookup **device facts**
    * These **facts** are gathered in parallel across all hosts at this stage (ie pre-deploy)
+ The generated **operations** are now run according to the command line arguments
