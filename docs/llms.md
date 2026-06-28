# LLM-friendly Docs (`llms.txt`)

pyinfra publishes two plain-text artifacts alongside the rendered HTML, following the [llmstxt.org](https://llmstxt.org) convention. They let AI assistants, agents, and static crawlers consume the docs without scraping the site.

## What's published

- **`llms.txt`**: a small curated index (~15 KB). Lists every hand-written guide, every operation/fact module, and every connector with a one-line summary and an absolute link into the rendered HTML docs.
- **`llms-full.txt`**: a single-file monolith (~290 KB). Contains the raw text of the hand-written guides plus the source docstrings and signatures of every built-in operation, fact, and connector.

Both files are regenerated on every docs build and live at the site root of each versioned doc tree:

- `https://docs.pyinfra.com/en/latest/llms.txt`
- `https://docs.pyinfra.com/en/latest/llms-full.txt`

Swap `latest` for a specific version (for example `3.x` or a tag like `v3.3.2`) to pin against a known release.

## How to use them

### For an AI assistant or code editor

Point the tool at `llms.txt` first. It's small, cheap to keep in context, and links out to whatever section the tool needs. Drop `llms-full.txt` in only when the task needs deep reference content (writing a custom operation, looking up every argument of `files.put`, etc.).

### As context for a chat session

```shell
curl -sS https://docs.pyinfra.com/en/latest/llms-full.txt | pbcopy
```

Paste the result into a new chat. One shot, entire docs.

### From code

```python
import urllib.request

index = urllib.request.urlopen(
    "https://docs.pyinfra.com/en/latest/llms.txt",
).read().decode()
```

## What's inside

`llms.txt` sections:

- Using pyinfra (getting started, CLI, arguments, FAQ)
- Deploy reference (operations index, facts index, connectors)
- One entry per built-in operation module
- One entry per built-in fact module
- One entry per built-in connector
- How pyinfra works (deploy process, API reference)
- Optional pages (install, changelog, compatibility, performance, etc.)

`llms-full.txt` inlines the hand-written guides verbatim and appends per-module sections pulled directly from source docstrings. Signatures, idempotency notes, and usage examples are all preserved.

## Version pinning and freshness

The files are rebuilt on every docs deploy, so they always match the HTML on the same version tree. If an LLM caches them, consider re-fetching when pyinfra releases a new version.
