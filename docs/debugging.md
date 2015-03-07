# Debugging pyinfra Deploys

By default pyinfra will surpress most server output. When a command returns a bad exit status, the entire stderr for that operation is printed to allow debugging without having to re-run the entire deploy.

To investigate exactly the commands being run during a deploy, add `-v` to the command line and all SSH input/output will be printed in realtime.
