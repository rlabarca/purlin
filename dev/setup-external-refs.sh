#!/usr/bin/env bash
# Creates the dog-food anchor repo the external-refs checks pull from.
#
# `specs/_anchors/security_no_dangerous_patterns.md` is this repository's own
# local anchor, so it carries no `> Source:` and no `> Pinned:`. This script
# publishes a copy of it to `dev/external-refs/security-policy.git`, a local
# bare repository, so `dev/test_e2e_external_refs.sh` can add it to a fresh
# project the way a consumer pulls an anchor from another repository. The copy
# carries no tracking field, so the bare repository holds what an anchor repo
# would hold.
#
# Safe to re-run: it does nothing when the repository already exists, and it
# never writes to specs/.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
EXT_DIR="$PROJECT_ROOT/dev/external-refs"
BARE_REPO="$EXT_DIR/security-policy.git"
ANCHOR_FILE="$PROJECT_ROOT/specs/_anchors/security_no_dangerous_patterns.md"
PUBLISHED_NAME="security_policy.md"

report_head() {
  echo "Bare repository: $BARE_REPO"
  echo "Head:            $1"
}

if [[ -d "$BARE_REPO" ]]; then
  echo "The anchor repo already exists."
  report_head "$(git -C "$BARE_REPO" rev-parse HEAD 2>/dev/null || echo unknown)"
  echo "To start again: rm -rf $BARE_REPO && bash $0"
  exit 0
fi

echo "=== Creating the dog-food anchor repo ==="

mkdir -p "$EXT_DIR"
git -c init.defaultBranch=main init --bare -q "$BARE_REPO"

WORK="${BARE_REPO}_work"
git clone -q "$BARE_REPO" "$WORK" 2>/dev/null

# Publish the author's file: the tracking fields a consumer adds are not part
# of what an anchor repo holds.
python3 - "$ANCHOR_FILE" "$WORK/$PUBLISHED_NAME" <<'PY'
import sys

source, target = sys.argv[1], sys.argv[2]
# The consumer tracking fields.
drop = ('> Source:', '> Pinned:', '> Path:', '> Note:')
with open(source, encoding='utf-8') as handle:
    lines = handle.readlines()
with open(target, 'w', encoding='utf-8') as handle:
    handle.writelines(line for line in lines if not line.startswith(drop))
PY

(
  cd "$WORK"
  git config user.email "dev@purlin.local"
  git config user.name "Purlin Dev"
  # A signature carries its own time, so a machine that signs by default would
  # publish a different sha. The dates above and no signature keep it fixed.
  git config commit.gpgsign false
  git add -A
  GIT_AUTHOR_DATE="2026-01-01T00:00:00+0000" \
    GIT_COMMITTER_DATE="2026-01-01T00:00:00+0000" \
    git commit -q -m "publish the security policy anchor"
  git push -q origin HEAD:refs/heads/main
)

SHA=$(git -C "$BARE_REPO" rev-parse HEAD)
rm -rf "$WORK"

report_head "$SHA"
echo ""
echo "Next: run bash dev/test_e2e_external_refs.sh to run the checks that"
echo "read it."
