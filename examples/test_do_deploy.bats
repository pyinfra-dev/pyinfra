#!/usr/bin/env bats

@test "test do_deploy.py digital ocean inventory" {
  run pyinfra do_inv.py do_deploy.py
  [ "$status" -eq 0 ]
}
