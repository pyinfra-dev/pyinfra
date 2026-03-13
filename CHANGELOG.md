# v3.7

Thank you to all contributors - particular shout out to @wowi42 for an incredible run of PRs!

Core:

- api.facts: fix `requires_command` shell operator precedence with compound commands (#1579) (@wowi42)

Operations/facts:

- operations.docker: add support for env files (#1572) (@EricDriussi)
- operations.docker: add support for dns (#1590) (@EricDriussi)
- operations.files.sync: support symlinks
- facts.server.Port: add UDP support and multi-platform backends (#1550) (@wowi42)
- facts.hardware.Memory: use LANG=C while calling vmstat (#1553) (@soltysek)
- facts.hardware: add `CpuInfo` fact (#1577) (@soltysek)
- facts.server.Sysctl: fix non-zero exit code causing empty result (#1578) (@wowi42)
- facts.runit.RunitManaged: handle missing service directory gracefully (#1580) (@wowi42)
- facts.hardware.Memory: fix FreeBSD support by summing page categories (#1584) (@wowi42)
- facts.server.SecurityLimits: handle missing limits.conf (#1582) (@wowi42)
- facts.server.Port: fix `ss` command for Alpine/BusyBox compatibility (#1586) (@wowi42)
- facts.iptables: add `requires_command` to all iptables facts (#1587) (@wowi42)
- facts.opkg: add `requires_command` and stop hardcoding /bin/opkg (#1588) (@wowi42)
- facts.choco: add `requires_command` to `ChocoPackages` and `ChocoVersion` (#1589) (@wowi42)

Connectors:

- connectors: `@podmanssh` connector for remote Podman container operations (#1547) (@elazar)
- connectors.ssh: exclude `_chdir` from global arguments used when removing temporary file (fix #1426) (#1429) (@morrison12)
- connectors.ssh: don't include password in SSH exception authentication data (#1538) (@oliverhr)

CLI:

- cli: use gevent for the progress spinner
- cli: add `--ssh-password-prompt` flag for interactive SSH password input (#1585) (@wowi42)

Other:

- global arguments: `_su_password` argument for su password authentication (#1573) (@wowi42)
- operations+facts: `server.timezone` and `server.Timezone` fact (#1575) (@wowi42)
- scripts: add `generate_changelog.py`

# v3.6.1

Thank you to all contributors. A solid bugfix release including some rather old bugs at this point.

Core fixes:

- api: handle/propagate nested operation errors
- api: don't apply stage check in API mode
- api: change `iter_active_hosts` -> `get_active_hosts`

Operation/fact fixes:

- operations.docker.container: add support for `--restart` and `--rm` arguments (@levinion)
- operations.postgres: add idempotency notice on passwords to `postgres.role`
- facts.flatpak.FlatpakPackages: handle headless output correctly
- facts.crontab: don't return non-command cron entries in `get_command`
- facts.files.FileContents: fix return None when no file exists
- facts.files.FindFiles: fix args parameter being ignored (@wowi42)

Connector fixes:

- connectors.ssh: handle multiple known hosts files in SSH config

CLI fixes:

- cli: fix missing config lock
- cli: fix config flags lost on multiple deploy files (@wowi42)
- cli/inventory: support loading host groups directly from module attributes (@wowi42)

Docs/meta:

- docs: fix many minor errors (@romain-dartigues)
- docs: fix typo in inventory-data.rst (@EshemMimi)
- meta: add arguments linter
- meta: fix dev linting scripts

# v3.6

First 2026 release - Happy New Year all! Thank you to all contributors. One big highlight is new metadata spec for plugins, this is the start of better discovery and documentation generation for third party facts and operations:

- add metadata spec for pyinfra plugins (@rod7760)

New and updated operations/facts:

- operations: add `_temp_dir` global argument for configuring temp directory (@wowi42)
- operations: add `files.copy` operation (@EricDriussi)
- operations.crontab: fix modification not properly relying on the `cron_name` parameter (@information-redacted)
- operations.docker.container: add support for setting labels (@spookyvision)
- operations: add import statements on at least one example of every operation (@mkinney)
- operations.docker.image: make operation idempotent (@DonDebonair)
- operations.files.template: allow custom jinja2 template loaders (@DaRasch)
- operations.files.block/connectors.util: use correct temporary directory (@morrison12)
- operations.util.packaging: allow empty package list in `ensure_packages` (@schenker)
- operations: fix tmpdir to properly use all the POSIX environment variables (@wowi42)
- facts.files.FileContents: improve docstring (@adonm)
- facts.apt.update: fix computation of cache_time when host is not UTC (@philippemilink)
- facts: add `FactProcessError` to log, not explode, issues processing facts (@NichtJens)
- facts.npm: check directory exists before cd-ing (wowi42)

Connectors:

- connectors.docker: add platform and architecture option via connector data (@JP-Ellis)
- connectors: close stdin after writing any input
- connectors.ssh: add workaround for paramiko no session error (@dfaerch)

CLI:  

- cli: change color of "No changes" to cyan
- cli: add option `--same-sudo-password` (@philippemilink)

Docs/meta:

- docs: replace `python -m` with `uv run -m` (@JP-Ellis)
- docs: fix URLs in API documentation (@kelno)
- docs/connectors: document command wrapping and parameter filtering best practices (@elazar)
- tests: freeze date for fact tests


# v3.5.3

- another release to fix different doc generation issues 🫠

# v3.5.2

- fix operation & fact docs generation

# v3.5.1

Patch release with a bunch of great fixes. But notably want to call out two major changes for anyone working on the pyinfra code itself (huge thank you Daan for implementing these):

- feat: use ruff for linting and formatting (@DonDebonair)
- feat: use uv for project and dependency management (@DonDebonair)

Core fixes:

- api: correctly set context state+host when calling `get_facts` 
- cli: catch exceptions when testing inventory/operation imports 
- cli: fix/remove datetime timezone warnings (@wowi42)
- operations/files.block: correct behaviour when markers/block not found and no line provided (@morrison12)
- operations.util.packaging: extend PkgInfo for winget (@rod7760)
- facts/server: support negative value in sysctl (@imlonghao)

Docs:

- docs: fix dynamic execution example (@wowi42)
- docs: Specify how the recursive argument to directory() works (@cliffmccarthy)
- docs: change recommended installation methods (@DonDebonair)
- docs: update writing connectors 

Tests:

- op.server.user tests: add exists_noop.json for user existence checks (fix warning) (@maisim)
- op.server.user tests: add noop_description (fix warning) (@maisim)
- fix: add missing command field in test (@maisim)
- tests: clear the host sftp memoization cache before setting up the mock (@wowi42)
- tests: export testgen class to a new package/repo 
- tests: fix missing stage sets on state 

# v3.5

New release with some really awesome new features, brought to you by the fantastic contributions of the community. New stuff:

- add `--diff` argument to show file diffs for potential file changes (@jgelens)
- add `_retries`, `_retry_delay` and `_retry_until` global arguments (@shohamd4)
- parallelize disconnecting from hosts (@gwelch-contegix)
- enable using SCP instead of SFTP for SSH file transfers (@DonDebonair)

New and updated operations/facts:

- facts/server: add `RebootRequired` fact (@wowi42)
- operations/pip: support PEP-508 package versions (@morrison12)
- operations+facts/docker: add Docker plugin support (@DonDebonair)
- operations/files.put: add `atime` and `mtime` arguments (@vram0gh2)
- operations/openrc: support runlevel when enabling services (@sengo4hd)
- facts/yum+dnf+zypper: return `repoid` in repository facts

Operation/fact fixes:

- facts/files.File: add ls fallback support (@mrkbac)
- operations/openrc: add missing noop messages (@sengo4hd)
- operations/server.crontab: fix newline when replacing existing values (@Nananas)
- operations/files.block: fix examples doc (@morrison12)
- operations/files.block: fix case where file exists but line is missing (@morrison12)
- operations/files.block: improve handling of special characters in marker lines (@morrison12)

Internal/meta:

- documentation link fix (@sengo4hd)


# v3.4.1

- fix config context when getting operation arguments

# v3.4

Much delayed 3.4, great collection of additions and improvements. Huge THANK YOU to all contributors as always. New features:

- Add @podman connector (@Griffoen)

New and updated operations/facts:

- operations/docker.network: add support for aux addresses (@DonDebonair)
- operations/files: try multiple hash functions in `files.get` + `files.put` (@mrkbac)
- operations/files.download: add `temp_dir` argument (@scy)
- operations/files.download: add `extra_curl_args` and `extra_wget_args` arguments (@jgelens)
- operations/flatpak: add remote support (@Griffoen)
- operations/git + facts/git: add `GitTag` fact and support tag checkout (@wowi42)
- operations/server.mount: add support for FreeBSD mounts (@DtxdF)
- facts/server: add `server.Port` fact to find process listening on port (@missytake)

Operation/fact fixes:

- operations/docker: handle case where no docker containers/etc exist (@wowi42)
- operations/files + operations/crontab: fix deletion of lines when `present=False` (@bad)
- operations/files.block: avoid use of non-POSIX `chown -n`
- operations/files.put: fix copying of local file mode (@vram0gh2)
- operations/server.user: fix appending of user groups (@aaron-riact)
- facts/server.Mounts: fix whitespace and escaped character parsing (@lemmi)
- facts/systemd: treat mounted units as active

Internal/meta:

- remove unnecessary setuptools runtime dependency (@karlicoss)


# v3.3.1

- connectors/ssh: fix extra `keep_alive` key passing through to paramiko `connect` call (@chipot)
- docs: refine installation guide with updated Python requirements and best practices (@wowi42)

# v3.3

Second release of 2025: loads of adds, fixes and documentation improvements. A huge THANK YOU to all contributors. Slightly changed format for the change list based on commit messages which should speed up releases:

New operations & arguments:

- operations/freebsd: add FreeBSD operations & facts (@DtxdF)
- operations/files.move: new operation (@Pirols)
- operations/server.user: enable adding user to secondary groups (Pirols)
- operations/postgres: enhance role management by adding `ALTER ROLE` support (@wowi42)
- operations/postgres: enable modifying existing postgres databases (@wowi42)
- operations/docker.container: refactor to support container recreation (@minor-fixes)

Operation/fact fixes:

- operations/postgres: fix quoting of locale parameters (@xvello)
- operations/server: remove leftover deprecated parameter (@wowi42)
- operations/pacmen: update PACMAN_REGEX to support additional characters (@wowi42)
- operations/server.sysctl: handle 0 integer values correctly (@lemmi)
- operations/apt: dist-upgrade also supports --autoremove (@bauen1)
- operations/apt: fix parameter name in docs (@bauen1)
- operations/server: fix: lastlog is always null (@ingstem)
- operations/docker: Fixed a typo with the volumes parameter to docker.prune operation (@mpilone)
- facts/xbps.XbpsPackages: allow . in package names (@lemmi)

Connectors, CLI:

- connectors: improve detection of sudo password needed
- connectors/ssh: add support for `ServerAliveInterval` (@chipot)
- cli: enable -h as shorthand for --help (@NichtJens)

Docs:

- docs: Add a section explaining connector flow (@goetzk)
- docs: Add inventory processing note and reference it (@goetzk)
- docs: Add example of logging to using operations docs (@goetzk)
- docs: fix wrong example operation using forbidden argument 'name' (@robertmx)
- docs: Add a note to the docs about using `_inner` when calling operations from other operations (@CSDUMMI)
- docs: Document host, state, inventory in files.template (@mpilone)
- docs: Minor adjustments to wording help docs and help (@goetzk)
- docs: expand connectors documentation (@goetzk)
- docs: correct import path for any_changed, all_changed (@lemmi)
- docs: Add note re: global arguments to operations (@simonhammes)

Internal/meta:

- refactor: update opkg documentation and add requires_command to ZFS and Git tests (@wowi42)
- Update testing and development dependencies in setup.py (@wowi42)
- tests: Load test specs with PyYAML instead of json (@taliaferro)
- typing: Require explicit override decorator (@bauen1)
- api: don't execute callbacks within a greenlet if we're already in one
- ci: Github Actions support for python 3.12 (@wowi42)
- ci: Prevent docs job from running on forks (@simonhammes)


# v3.2

Hello 2025! Here's pyinfra 3.2 - with another incredible round of contributions from the community, THANK YOU ALL. New stuff:

- Add total counts to results summary (@NichtJens)
- Enable passing extra data via `local.include` (@TimothyWillard)
- Validate inventory files and display warnings for unexpected variables (@simonhammes)

New operations/facts:

- Add `pipx` operations (`packages`, `upgrade_all`, `ensure_path`) facts (`PipxPackages`, `PipxEnvironment`) and operations (@maisim)
- Add `server.OsRelease` fact (@wowi42)
- Add `podman.PodmanSystemInfo` and `podman.PodmanPs` facts (@bauen1)
- Add many extra arguments (including generic args) to `files.FindFiles*` facts (@JakkuSakura)
- Add `system` argument to `git.config` operation (@Pirols)
- Add `psql_database` argument to postgres operations & facts (@hamishfagg)
- Add `files.Sha384File` fact and `sha384sum` argument to `files.download` operation (@simonhammes)
- Add `apt.SimulateOperationWillChange` fact (@bauen1)
- Detect changes in `apt.upgrade` and `apt.dist_upgrade` operations (@bauen1)
- Add `fibootmgr.EFIBootMgr` fact (@bauen1)
- Add opkg facts and operations (@morrison12)

Fixes:

- Multiple fixes for `server.crontab` operation and facts (@JakkuSakura)
- Correctly handle `latest` argument with requirements file in `pip.packages` operation (@amiraliakbari)
- Fix regex used to parse installed apk packages (@simonhammes)
- Fix SSH connector overwriting known hosts files (@vo452)

Docs/internal tweaks:

- Add type annotations for many more operations (@simonhammes)
- Add typos CI checking to replace flake8-spellcheck (@simonhammes)
- Bump CI actions and dependencies (@simonhammes)
- Require JSON tests to include all arguments
- Remove unused `configparser` dependency (@bkmgit)
- Many small documentation fixes/tweaks


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
