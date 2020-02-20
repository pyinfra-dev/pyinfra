#!/usr/bin/env bats --jobs 2

# using bats for testing - see https://github.com/bats-core/bats-core
# Note: requires parallel and coreutils if using the '--jobs' option
# (e.g. on mac 'brew install coreutils parallel')

@test "adhoc install package using docker [ubuntu]" {
  run pyinfra @docker/ubuntu apt.packages iftop sudo=true update=true
  [ "$status" -eq 0 ]
}

@test "[apk.py] example using docker [alpine]" {
  run pyinfra @docker/alpine apk.py
  [ "$status" -eq 0 ]
}

@test "[apt.py, npm.py] examples using docker [ubuntu]" {
  run pyinfra @docker/ubuntu apt.py npm.py
  [ "$status" -eq 0 ]
}

@test "[git.py, gem.py, pip.py] examples using docker [ubuntu, centos, alpine]" {
  run pyinfra @docker/ubuntu,@docker/centos,@docker/alpine git.py gem.py pip.py
  [ "$status" -eq 0 ]
}

@test "[pacman.py] example using docker [archlinux]" {
  run pyinfra @docker/archlinux pacman.py
  [ "$status" -eq 0 ]
}

@test "[files.py, dnf.py, server.py] example using docker [centos]" {
  run pyinfra @docker/centos files.py dnf.py server.py
  [ "$status" -eq 0 ]
}

@test "[yum.py] example using docker [centos]" {
  run pyinfra @docker/centos yum.py
  [ "$status" -eq 0 ]
}
