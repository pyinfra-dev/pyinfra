# v3.1.1

- Improve errors with 2.x style `@decorator` (vs `@decorator()`) functions
- Document adding custom connectors (@simonhammes)
- Add basic API example to docs (@pirate)
- Fix sphinx warnings (@simonhammes)
- Fix force & pull arguments in `git.worktree` operation
- Fix `server.reboot` reconnection (@wackou)
- Fix chroot/local connector non-utf file gets (@evoldstad)
- Fix `AptSources` fact to parse components in order & with digits (@rsfzi)

# v3.1

Here's pyinfra 3.1 - a release primarily driven by contributors new and old - a HUGE THANK YOU to all of you who dedicate time to work on pushing pyinfra forward. New stuff:

- Add `zfs` operations (`dataset`, `snapshot`, `volume`, `filesystem`) facts (`Pools`, `Datasets`, `Filesystems`, `Snapshots`, `Volumes`) (@taliaferro)
- Add `flatpak` operations (`packages`) and facts (`FlatpakPackage`, `FlatpakPackages`) (@JustScreaMy)
- Add `jinja_env_kwargs` argument to `files.template` operation (@DonDebonair)
- Add using dictionaries as `@terraform` output (map from group -> hosts)
- Add default `@terraform` output key - `pyinfra_inventory.value`, promote connector to beta
- Add support for multiple keys in each `server.authorized_keys` file (@matthijskooijman)
- Add print all dependency versions with `--support` flag (@kytta)

Fixes:

- Fix when `ssh_hostname` is set as override data, don't do inventory hostname check
- Fix `apt.AptSources` parsing special characters (@CondensedTea)
- Fix `server.reboot` connection detection (@bauen1 + @lemmi)
- Fix systemd flagging of sockets running (@bauen1)
- Fix mysql dump quoting (@simonhammes)
- Fix tilde expansion in files facts (@simonhammes)
- Fix host lookup check with SSH alias config (@simonhammes)
- Fix crontab comparison (@andrew-d)

Docs/internal tweaks:

- Improve operations documentation (@bauen1)
- Default to local machine if `user_name` set in systecmt (@bauen1)
- Improve efficiency of Docker operations (@apecnascimento)
- Shallow copy `host.data` data to mutation

# v3.0.2

- Fix `OperationMeta.did_change`: this is now a function as originally designed
- Add quick test for `host.when` context manager
- Remove extra detected changes note when not relevant

# v3.0.1

- Switch to `command -v` not `which` in `server.Which` fact (@lemmi)
- Fix detection of xbps in `server.packages` operation (@romain-dartigues)
- Fix argument typo in operations doc (@scoufman)
- Add expanded note about detected changes + hidden side effects during execution
- Fix missing global arguments in group data files
- Fix `--group-data` CLI argument behaviour
- Remove unused/dead `--quiet` flag

# v3.0

Welcome to pyinfra v3! This version is the biggest overhaul of pyinfra since it was created back in 2015. Most v2 deployment code should be automatically compatible, but as always be aware. Major changes:

### Runtime operation execution

pyinfra now executes operations at runtime, rather than pre-generating commands. Although the change isn't noticeable this fixes an entire class of bugs and confusion. See the [limitations](https://docs.pyinfra.com/en/2.x/deploy-process.html#limitations) section in the v2 docs. All of those issues are now a thing of the past.

This represents a huge overhaul of pyinfra's internals and should be a huge improvement for users.

Care has been taken to reduce the overhead of this change which still supports the same diffs and change proposal mechanism.

### CLI flow & prompts

The pyinfra CLI will now prompt (instead of ignore, or immediately exit) when problems are encountered, allowing the user to choose to continue. Additionally an approval step is added before executing changes (this can be skipped with `-y` or setting the `PYINFRA_YES` environment variable).

### Extendable connectors API, typing overhaul

v3 of pyinfra includes for the first time a (mostly) typed internal API with proper support for IDE linting. There's a whole new connectors API that provides a framework for building new connectors.

### Breaking changes

- Rename `_use_sudo_password` argument to `_sudo_password`
- Remove `winrm` connector and `windows*` operations/facts, moving to [`pyinfra-windows`](https://github.com/pyinfra-dev/pyinfra-windows)
- The deploy decorator must now be called, ie used as `@deploy()`, and is now typed
- Remove broken Ansible inventory connector

### Operations & Facts

- Add `docker.container`, `docker.image`, `docker.volume`, `docker.network` & `docker.prune` operations (@apecnascimento)
- Add `runit.service` operation and `RunitStatus` fact (@lemmi)
- Add `TmpDir` fact
- Add `services` argument to systemd facts for filtering
- Add type hints for all the operations (@stone-w4tch3r)
- Lowercase pip packages properly (PEP-0426)
- Rename `postgresql` -> `postgres` operations & facts (old ones still work)
- Improve IP/MAC parsing in `NetworkDevices` fact (@sudoBash418)
- Enable getting `Home` fact for other users (@matthijskooijman)
- Use users correct home directory in `server.user_authorized_keys` operation (@matthijskooijman)
- Fix `destination`/`not_destination` arguments in `iptables.rule` operation
- Fix remote dirs when executing from Windows in `files.sync` operation (@Renerick)
- Fix quoting of systemd unit names (@martenlienen)

### Other Changes

- Add new `_if` global argument to control operation execution at runtime
- Add `--debug-all` flag to set debug logging for all packages
- Retry SSH connections on failure (configurable, see [SSH connector](https://docs.pyinfra.com/en/3.x/connectors/ssh.html#available-data)) (@fwiesel)
- Documentation typo fixes (@szepeviktor, @sudoBash418)
- Fix handling of binary files in Docker connector (@matthijskooijman)
- Add `will_change` attribute and `did_change` context manager to `OperationMeta`
- Replace use of `pkg_resources` with `importlib.metadata` (@diazona)
- Fix identifying Python inventory files as modules (@martenlienen)
- Fix typed arguments order (@cdleonard)
- Check that fact commands don't take global arguments (@martenlienen)

# v2.x

[See this file in the `2.x` branch](https://github.com/Fizzadar/pyinfra/blob/2.x/CHANGELOG.md).

# v1.x

[See this file in the `1.x` branch](https://github.com/Fizzadar/pyinfra/blob/1.x/CHANGELOG.md).
