# Facts

Facts in pyinfra are used to read the current state of remote hosts. This is then used to generate the commands needed to alter it's state as defined in the deploy script. They are not cached between deploys to avoid incorrect state, and facts are always run, even when `--dry`.
