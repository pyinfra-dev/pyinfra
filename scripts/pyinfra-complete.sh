#!/usr/bin/env bash
#
# bash completion file for pyinfra
#
# This script provides completion of:
#  - commands and their options
#
# To enable the completions ensure that this
# file (pyinfra-complete.sh) is sourced. For example:
# run something like this: (where you change the path)
#    echo "source /full_path_to/pyinfra-complete.sh" >> ~/.bashrc
#
_pyinfra() {
  local cur prev opts base commands
  COMPREPLY=()
  cur="${COMP_WORDS[COMP_CWORD]}"
  prev="${COMP_WORDS[COMP_CWORD-1]}"

  #  Options that will complete
  opts="exec fact all-facts"

  commands="--debug --debug-data --debug-facts --debug-operations --debug-state --dry --facts --fail-percent --key --key-password --limit --no-wait --operations --parallel --password --port --quiet --su --su-user --sudo --sudo-user --support --version --help --user -v"
  COMPREPLY=($(compgen -W "${commands} ${opts}" -- ${cur}))
}

complete -F _pyinfra pyinfra
# vim: ft=bash sw=2 ts=2 et
