#!/usr/bin/env bash
# Syncs .prs/ review files against open GitHub PRs.
# Deletes reviews for merged/closed PRs, outputs a plan for what to update/create.
# Skips re-review when PR hasn't been updated since the last review.
set -euo pipefail

REPO="pyinfra-dev/pyinfra"
PRS_DIR="$(git rev-parse --show-toplevel)/.prs"

mkdir -p "$PRS_DIR"

# Fetch all open PR numbers (updated in last year)
SINCE=$(date -v-1y +%Y-%m-%dT%H:%M:%SZ 2>/dev/null || date -d '1 year ago' +%Y-%m-%dT%H:%M:%SZ)
OPEN_PRS=$(gh pr list --repo "$REPO" --state open --limit 200 --json number,title,author,updatedAt \
  --jq "[.[] | select(.updatedAt >= \"$SINCE\")] | sort_by(.number)")

OPEN_NUMBERS=$(echo "$OPEN_PRS" | jq -r '.[].number')

# Find existing review files
EXISTING=()
for f in "$PRS_DIR"/*.md; do
  [ -f "$f" ] || continue
  num=$(basename "$f" .md)
  [[ "$num" =~ ^[0-9]+$ ]] && EXISTING+=("$num")
done

# Delete stale reviews (merged/closed)
DELETED=()
for num in "${EXISTING[@]}"; do
  if ! echo "$OPEN_NUMBERS" | grep -qx "$num"; then
    rm "$PRS_DIR/$num.md"
    DELETED+=("$num")
  fi
done

# Categorize: update (changed), unchanged (skip), or new
UPDATE=()
UNCHANGED=()
NEW=()
while IFS= read -r num; do
  if [ -f "$PRS_DIR/$num.md" ]; then
    # Compare stored updatedAt with current PR updatedAt
    stored_ts=$(sed -n 's/^\*\*PR Updated:\*\* //p' "$PRS_DIR/$num.md" 2>/dev/null || echo "")
    current_ts=$(echo "$OPEN_PRS" | jq -r ".[] | select(.number == $num) | .updatedAt")
    if [ -n "$stored_ts" ] && [ "$stored_ts" = "$current_ts" ]; then
      UNCHANGED+=("$num")
    else
      UPDATE+=("$num")
    fi
  else
    NEW+=("$num")
  fi
done <<< "$OPEN_NUMBERS"

# Output markdown summary
echo "# PR Review Sync"
echo ""
echo "**Repo:** $REPO"
echo "**Date:** $(date +%Y-%m-%d)"
echo ""

if [ ${#DELETED[@]} -gt 0 ]; then
  echo "## Deleted (merged/closed)"
  for num in "${DELETED[@]}"; do
    echo "- #$num"
  done
  echo ""
fi

if [ ${#UNCHANGED[@]} -gt 0 ]; then
  echo "## Unchanged since last review (${#UNCHANGED[@]})"
  echo "$OPEN_PRS" | jq -r --argjson nums "$(printf '%s\n' "${UNCHANGED[@]}" | jq -R 'tonumber' | jq -s '.')" \
    '.[] | select(.number as $n | $nums | index($n)) | "- #\(.number) \(.title) (@\(.author.login))"'
  echo ""
fi

echo "## Update existing reviews (${#UPDATE[@]})"
if [ ${#UPDATE[@]} -gt 0 ]; then
  echo "$OPEN_PRS" | jq -r --argjson nums "$(printf '%s\n' "${UPDATE[@]}" | jq -R 'tonumber' | jq -s '.')" \
    '.[] | select(.number as $n | $nums | index($n)) | "- #\(.number) \(.title) (@\(.author.login))"'
fi
echo ""

echo "## New reviews needed (${#NEW[@]})"
if [ ${#NEW[@]} -gt 0 ]; then
  echo "$OPEN_PRS" | jq -r --argjson nums "$(printf '%s\n' "${NEW[@]}" | jq -R 'tonumber' | jq -s '.')" \
    '.[] | select(.number as $n | $nums | index($n)) | "- #\(.number) \(.title) (@\(.author.login))"'
fi
