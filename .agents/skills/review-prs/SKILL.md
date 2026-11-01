---
name: review-prs
description: Review open or specified PRs on pyinfra-dev/pyinfra and maintain local review files in .prs/. Use when asked to review pyinfra pull requests or refresh their reviews.
---

Review open PRs on pyinfra-dev/pyinfra and maintain review files in `.prs/`:

## Arguments

Optionally accepts a list of PR numbers (e.g. `$review-prs 1897 1891 1753` in
Codex or `/review-prs 1897 1891 1753` in Claude Code). Anything that isn't a number
is ignored.

- **PR numbers given**: review exactly those PRs, unconditionally — do NOT run the sync
  script, do NOT skip PRs whose review is already up to date, and do NOT delete any
  review files. Skip step 1 entirely and treat the given numbers as the PR list.
- **No PR numbers given**: run the sync script (step 1) and use its output as the PR list.

## Steps

1. **Run sync script** (only when no PR numbers were given): Execute
   `bash .agents/skills/review-prs/sync.sh` to clean up stale reviews and get the list of
   PRs to update/create. The PR list is the Update + New sections only, NOT Unchanged.

2. **For each PR** in the list, launch agents using rolling concurrency (see Parallelism below) to review:
   - Each agent gets: repo name, PR number, whether it's an update (a `.prs/{number}.md`
     already exists) or a new review.
   - Agent fetches the PR diff via `gh pr diff --repo pyinfra-dev/pyinfra {number}`.
   - Agent also fetches `updatedAt` via `gh pr view --repo pyinfra-dev/pyinfra {number} --json updatedAt --jq .updatedAt` and includes it in the review header as `**PR Updated:** {timestamp}`.
   - Agent reads relevant source code files being modified (read and search files, never assume).
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
- **Deep inspection**: Always read the actual source code being modified. Never assume behavior - trace code paths, check callers, verify types. Read and search source files extensively.
- **Verdict options**:
   * **GO** = safe to merge as-is or with trivial nits only
   * **NO-GO** = has bugs, security issues, breaking changes, or significant design problems
   * **NEEDS-DISCUSSION** = requires maintainer input on approach/design

## Parallelism

Use **rolling concurrency**, targeting up to 5 PR reviews at a time within the
host's available agent capacity. Use the host's native agent tools: Codex's
available spawn and completion tools, or Claude Code's background agents with
`run_in_background: true`. If subagents are unavailable, review sequentially.

- **Initial fill**: launch one agent per PR up to the available capacity.
- **On each completion**: release the completed agent's slot if required by the
  host, then immediately launch the next queued PR review.
- Track `queued`, `in_flight`, and `done` (review file written) PRs.
- Do not wait for the full pool to drain before launching replacements.
- Give each agent the repo name, PR number, review format, and instruction to
  deeply inspect code.

## Final Summary

Once all review updates are complete, output a summary table of PRs grouped by verdict. Re-read the PR files to collect updated verdicts for each. When explicit PR numbers were given, only summarise those PRs.
