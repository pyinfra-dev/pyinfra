---
orphan: true
---

# Building and Tagging Container Images

The `@docker` and `@podman` connectors can build images from a deploy instead of a Dockerfile. They start a temporary container from a base image, apply the deploy, commit the result as a new image, and remove the temporary container.

This is useful when you want to use Python, pyinfra facts, and the same operations you use against other hosts. Dockerfiles remain a better fit for standard application builds, build caching, multi-stage builds, and BuildKit features.

## Build a tagged image

Create a deploy in `deploy.py`:

```python
from pyinfra.operations import apt

apt.packages(
    packages=["nginx"],
    update=True,
)
```

Create `inventory.py` with a base image and the optional `docker_tag` data:

```python
hosts = [
    (
        "@docker/ubuntu:24.04",
        {"docker_tag": "registry.example.com/team/my-app:1.0.0"},
    ),
]
```

Run the deploy:

```sh
pyinfra inventory.py deploy.py
```

Pyinfra commits the container, removes it, and then applies the tag:

```sh
docker tag <image-id> registry.example.com/team/my-app:1.0.0
```

The tag is a complete image reference. It can include a registry, namespace, repository, and tag. Pyinfra logs both the image ID and the tag. It does not push the image to a registry.

If `docker_tag` is not set, pyinfra only logs the image ID, as before.

## Podman

The same option works with Podman:

```python
hosts = [
    (
        "@podman/ubuntu:24.04",
        {"docker_tag": "registry.example.com/team/my-app:1.0.0"},
    ),
]
```

The connector uses `podman tag` instead of `docker tag`.

## Existing containers

When you target an existing running container, pyinfra leaves it running and does not commit a new image. `docker_tag` is rejected in this mode because there is no new image to tag.

Only use `docker_tag` when starting from a base image and building a new image.
