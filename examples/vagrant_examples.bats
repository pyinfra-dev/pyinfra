#!/usr/bin/env bats

# using bats for testing - see https://github.com/bats-core/bats-core

@test "vagrant installation using vagrant [ubuntu]" {
  run cd vagrant && vagrant up && pyinfra @vagrant vagrant.py && vagrant destroy -f && cd ..
  [ "$status" -eq 0 ]
}
