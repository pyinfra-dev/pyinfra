#!/usr/bin/env bats

@test "step 0 - remove 10. floating ip stuff on digital ocean " {
  run pyinfra do_inv.py step0.py
  [ "$status" -eq 0 ]
}
