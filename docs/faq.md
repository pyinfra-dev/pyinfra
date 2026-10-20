# Frequently Asked Questions

## How do I get the name of the current host?

The currently executing host can be fetched from the `host` context variable. If you need the hostname the `server.Hostname` fact can be used to get that:

```python
# Get the name of the host as defined in the inventory
from pyinfra import host
name = host.name

# Get the actual current hostname from the host
from pyinfra.facts.server import Hostname
hostname = host.get_fact(Hostname)
print(f"hostname:{hostname}")
```

## How do I use sudo, su or doas in an operation?

Sudo is controlled by one of the [privilege and user escalation arguments](arguments.md#privilege-user-escalation), there are a number of additional arguments to control sudo execution:

```python
from pyinfra.operations import apt
apt.packages(
    packages=["iftop"],
    _sudo=True,
    _sudo_user="someuser",    # sudo to this user
    _use_sudo_login=True,     # use a login shell when sudo-ing
    _preserve_sudo_env=True,  # preserve the environment when sudo-ing
)
```

## How do I chmod or chown a file/directory/link?

Use the `files.file`, `files.directory` or `files.link` operations to set the permissions and ownership of files, directories & links:

```python
from pyinfra.operations import files
files.file(
    path="/etc/default/elasticsearch",
    user="pyinfra",
    group="pyinfra",
    mode=644,
)
```

## How do I handle unreliable operations or network issues?

Use the [retry behavior arguments](arguments.md#retry-behavior) to automatically retry failed operations. This is especially useful for network operations or services that may be temporarily unavailable:

```python
from pyinfra.operations import server
# Retry a network operation up to 3 times
server.shell(
    name="Download file with retries",
    commands=["wget https://example.com/file.zip"],
    _retries=3,
    _retry_delay=5,  # wait 5 seconds between retries
)

# Use custom retry logic for specific error conditions
def should_retry_download(output_data):
    # Retry only on temporary network errors, not permanent failures
    stderr_text = " ".join(output_data["stderr_lines"]).lower()
    temporary_errors = ["timeout", "connection refused", "temporary failure"]
    return any(error in stderr_text for error in temporary_errors)

server.shell(
    name="Download with smart retry logic",
    commands=["wget https://example.com/large-file.zip"],
    _retries=3,
    _retry_until=should_retry_download,
)
```

## Does pyinfra publish an `llms.txt`?

Yes. `llms.txt` is the [llmstxt.org](https://llmstxt.org) convention for exposing documentation in a plain-text format that AI assistants, agents, and crawlers can consume without scraping the rendered HTML site. pyinfra publishes two files on every doc build:

- `llms.txt` (~15 KB): a curated index with one-line summaries and absolute links for every guide, operation, fact and connector.
- `llms-full.txt` (~290 KB): a single-file monolith inlining the hand-written guides and every built-in operation/fact/connector docstring and signature.

Both live at the root of each versioned doc tree:

- [docs.pyinfra.com/en/latest/llms.txt](https://docs.pyinfra.com/en/latest/llms.txt)
- [docs.pyinfra.com/en/latest/llms-full.txt](https://docs.pyinfra.com/en/latest/llms-full.txt)

Swap `latest` for a release tag to pin against a known version. See [LLM-friendly docs](llms.md) for consumption examples.
