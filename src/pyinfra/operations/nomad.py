"""Run Nomad job and allocation operations using the ``nomad`` CLI."""

from __future__ import annotations

from pyinfra.api import StringCommand, operation


@operation(is_idempotent=False)
def run(job_file: str, detach: bool = False):
    args = ["nomad", "job", "run"]
    if detach:
        args.append("-detach")
    args.append(job_file)
    yield StringCommand(*args)


@operation(is_idempotent=False)
def stop(job: str, purge: bool = False, detach: bool = False):
    args = ["nomad", "job", "stop"]
    if purge:
        args.append("-purge")
    if detach:
        args.append("-detach")
    args.append(job)
    yield StringCommand(*args)


@operation(is_idempotent=False)
def dispatch(job: str, payload_file: str | None = None):
    args = ["nomad", "job", "dispatch", job]
    if payload_file:
        args.append(payload_file)
    yield StringCommand(*args)


@operation(is_idempotent=False)
def scale(job: str, group: str, count: int, detach: bool = False):
    args = ["nomad", "job", "scale"]
    if detach:
        args.append("-detach")
    args.extend([f"{job}[{group}]", str(count)])
    yield StringCommand(*args)
