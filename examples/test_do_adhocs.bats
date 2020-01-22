#!/usr/bin/env bats

@test "adhoc hello digital ocean inventory" {
  run pyinfra do_inv.py exec -- echo hello
  [ "$status" -eq 0 ]
}
