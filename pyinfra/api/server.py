# pyinfra
# File: pyinfra/api/server.py
# Desc: used via `pyinfra.server` in modules
#       peeds up gather_facts by doing them for every host when requested on one, in parallel

import pyinfra


def fact(key, **kwargs):
    # Already got this fact?
    if key in pyinfra._facts[pyinfra._current_server]:
        return pyinfra._facts[pyinfra._current_server][key]

    # For each host, spawn a job on the pool to gather the fact

    # Join, cache in _facts
    return True

def fact_list(key, **kwargs):
    # Already got this fact?
    if key in pyinfra._facts[pyinfra._current_server]:
        return pyinfra._facts[pyinfra._current_server][key]

    # For each host, spawn a job on the pool to gather the fact

    # Join, cache in _facts
    return []
