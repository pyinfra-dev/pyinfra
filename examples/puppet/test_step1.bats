#!/usr/bin/env bats

@test "step 1 - puppet master and agent on digital ocean inventory" {
  run pyinfra do_inv.py step1.py
  [ "$status" -eq 0 ]
}
