#!/usr/bin/env bats

@test "adhoc list rpm_packages" {
  run pyinfra do_inv.py --limit master_servers fact rpm_packages
  [ "$status" -eq 0 ]
}

@test "adhoc ensure vim package is installed" {
  run pyinfra do_inv.py yum.packages vim sudo=True present=True
  [ "$status" -eq 0 ]
}

@test "adhoc stop httpd on agents" {
  run pyinfra do_inv.py --limit agent_servers init.systemd httpd sudo=True running=False
  [ "$status" -eq 0 ]
}

@test "adhoc do puppet run on agents" {
  run pyinfra do_inv.py --limit agent_servers puppet.agent sudo=true use_sudo_login=true success_exit_codes=[0,2]
  [ "$status" -eq 0 ]
}

