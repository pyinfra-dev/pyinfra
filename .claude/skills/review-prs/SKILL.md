---
name: review-prs
tools: Read, Grep, Glob, Bash
---

Review all open PRs on pyinfra-dev/pyinfra and maintain review files in `.prs/`:

## Steps

1. **Run sync script**: Execute `bash .claude/skills/review-prs/sync.sh` to clean up stale reviews and get the list of PRs to update/create.

2. **For each PR** in the sync output (Update + New only, NOT Unchanged), launch agents using rolling concurrency (see Parallelism below) to review:
   - Each agent gets: repo name, PR number, whether it's an update or new review.
   - Agent fetches the PR diff via `gh pr diff --repo pyinfra-dev/pyinfra {number}`.
   - Agent also fetches `updatedAt` via `gh pr view --repo pyinfra-dev/pyinfra {number} --json updatedAt --jq .updatedAt` and includes it in the review header as `**PR Updated:** {timestamp}`.
   - Agent reads relevant source code files being modified (use Read/Grep, never assume).
   - Agent writes the review file to `.prs/{number}.md`.

3. **Review format** for each PR file (`.prs/{number}.md`):

```markdown
# PR #{number} - {title}

**Author:** {author}
**URL:** https://github.com/pyinfra-dev/pyinfra/pull/{number}
**Review Date:** {YYYY-MM-DD}
**PR Updated:** {updatedAt ISO timestamp from GH API}

## Verdict: {GO | NO-GO | NEEDS-DISCUSSION}

{1-2 sentence summary of what the PR does}

## Issues

{Only if there are problems. Each issue should be a concise bullet with a code snippet if relevant. Skip this section entirely if no issues.}

## Notes

{Optional minor observations, nits, or suggestions. Keep brief.}
```

## Review guidelines

- **Be minimal**: Only highlight actual problems or risks. Don't pad reviews with praise or restatements.
- **Code snippets**: When referencing problematic code, include the relevant snippet (keep short).
- **Deep inspection**: Always read the actual source code being modified. Never assume behavior - trace code paths, check callers, verify types. Use Grep/Read extensively.
- **Verdict options**:
   * **GO** = safe to merge as-is or with trivial nits only
   * **NO-GO** = has bugs, security issues, breaking changes, or significant design problems
   * **NEEDS-DISCUSSION** = requires maintainer input on approach/design

## Parallelism

Use **rolling concurrency**, not fixed batches. The goal is to keep ~5 PR reviews in flight at all times so a slow review never blocks a fast one.

- Spawn each PR-review agent with `run_in_background: true` so completions arrive as individual notifications instead of blocking on a whole batch.
- **Initial fill**: in a single message, launch up to 5 background agents (one per PR) to saturate the in-flight pool.
- **On each completion notification**: if any PRs remain in the queue, immediately launch one new background agent to replace the finished one — keep the in-flight count at 5 until the queue is empty.
- Track three sets in your head (or via TaskCreate if it helps): `queued` (not yet started), `in_flight` (background agents running), `done` (review file written). Move PRs between sets as agents complete.
- Do not wait for the full pool to drain before launching replacements — the whole point is to avoid that.
- Each agent should be given the full context: repo name, PR number, review format, and instruction to deeply inspect code.

## Final Summary

Once all review updates are complete, output a summary table of PRs grouped by verdict. Re-read the PR files to collect updated verdicts for each.
