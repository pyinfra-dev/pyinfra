#!/usr/bin/env bats --jobs 3

# using bats for testing - see https://github.com/bats-core/bats-core
# Note: requires parallel and coreutils if using the '--jobs' option
# (e.g. on mac 'brew install coreutils parallel')

@test "install package using docker [ubuntu]" {
  run pyinfra @docker/ubuntu apt.packages iftop sudo=true update=true
  [ "$status" -eq 0 ]
}

@test "single fact using docker [ubuntu]" {
  run pyinfra @docker/ubuntu,@docker/centos fact os
  [ "$status" -eq 0 ]
}

@test "all facts using docker [ubuntu]" {
  run pyinfra @docker/ubuntu,@docker/centos all-facts
  [ "$status" -eq 0 ]
}
