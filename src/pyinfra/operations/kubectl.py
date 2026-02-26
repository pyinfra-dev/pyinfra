"""Run Kubernetes resource operations using the ``kubectl`` CLI."""

from __future__ import annotations

from pyinfra.api import QuoteString, StringCommand, operation


def _base_args(namespace: str | None, context: str | None, kubeconfig: str | None) -> list[str]:
    args = ["kubectl"]
    if context:
        args.extend(["--context", context])
    if kubeconfig:
        args.extend(["--kubeconfig", kubeconfig])
    if namespace:
        args.extend(["-n", namespace])
    return args


@operation(is_idempotent=False)
def apply(
    manifest: str,
    namespace: str | None = None,
    context: str | None = None,
    kubeconfig: str | None = None,
    server_side: bool = False,
    force_conflicts: bool = False,
):
    args = _base_args(namespace, context, kubeconfig)
    args.extend(["apply", "-f", manifest])
    if server_side:
        args.append("--server-side")
    if force_conflicts:
        args.append("--force-conflicts")
    yield StringCommand(*args)


@operation(is_idempotent=False)
def delete(
    resource: str,
    namespace: str | None = None,
    context: str | None = None,
    kubeconfig: str | None = None,
    ignore_not_found: bool = True,
):
    args = _base_args(namespace, context, kubeconfig)
    args.extend(["delete", resource])
    if ignore_not_found:
        args.append("--ignore-not-found")
    yield StringCommand(*args)


@operation(is_idempotent=False)
def patch(
    resource: str,
    patch: str,
    patch_type: str = "strategic",
    namespace: str | None = None,
    context: str | None = None,
    kubeconfig: str | None = None,
):
    args = _base_args(namespace, context, kubeconfig)
    args.extend(["patch", resource, "--type", patch_type, "-p", QuoteString(patch)])
    yield StringCommand(*args)


@operation(is_idempotent=False)
def set_image(
    resource: str,
    container: str,
    image: str,
    namespace: str | None = None,
    context: str | None = None,
    kubeconfig: str | None = None,
):
    args = _base_args(namespace, context, kubeconfig)
    args.extend(["set", "image", resource, f"{container}={image}"])
    yield StringCommand(*args)


@operation(is_idempotent=False)
def rollout_status(
    resource: str,
    timeout: str = "120s",
    namespace: str | None = None,
    context: str | None = None,
    kubeconfig: str | None = None,
):
    args = _base_args(namespace, context, kubeconfig)
    args.extend(["rollout", "status", resource, "--timeout", timeout])
    yield StringCommand(*args)
