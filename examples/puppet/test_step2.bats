#!/usr/bin/env bats

@test "step 2 - puppet master and agent on digital ocean inventory" {
  run pyinfra do_inv.py step2.py
  [ "$status" -eq 0 ]
}
