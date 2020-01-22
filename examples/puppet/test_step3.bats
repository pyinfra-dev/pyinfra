#!/usr/bin/env bats

@test "step 3 - puppet master and agent on digital ocean inventory" {
  run pyinfra do_inv.py step3.py
  [ "$status" -eq 0 ]
}
