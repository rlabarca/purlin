#!/usr/bin/env bash
# Creates the dog-food anchor repo this checkout pins against.
#
# `specs/_anchors/security_no_dangerous_patterns.md` carries
# `> Source: ./dev/external-refs/security-policy.git`. That source is a local
# bare repository, not a network remote, and this script is what creates it.
# The copy it publishes is a 0.10.0 anchor: the consumer tracking fields and
# the retired visual fields are stripped, so the bare repository holds what an
# anchor repo would hold and nothing a consumer added.
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

report_pin() {
  local sha="$1"
  local pinned
  pinned=$(grep '^> Pinned:' "$ANCHOR_FILE" 2>/dev/null | head -1 | awk '{print $3}')
  echo "Bare repository: $BARE_REPO"
  echo "Head:            $sha"
  echo "Anchor pin:      ${pinned:-none}"
  if [[ "$pinned" == "$sha" ]]; then
    echo "The pin is current."
  else
    echo "The pin is not this head, so purlin:status reports the anchor behind."
    echo "To make it current, put $sha on the > Pinned: line of"
    echo "$ANCHOR_FILE."
  fi
}

if [[ -d "$BARE_REPO" ]]; then
  echo "The anchor repo already exists."
  report_pin "$(git -C "$BARE_REPO" rev-parse HEAD 2>/dev/null || echo unknown)"
  echo "To start again: rm -rf $BARE_REPO && bash $0"
  exit 0
fi

echo "=== Creating the dog-food anchor repo ==="

mkdir -p "$EXT_DIR"
git -c init.defaultBranch=main init --bare -q "$BARE_REPO"

WORK="${BARE_REPO}_work"
git clone -q "$BARE_REPO" "$WORK" 2>/dev/null

# Publish the author's file: the tracking fields a consumer adds, and the
# fields 0.10.0 retired, are not part of what an anchor repo holds.
python3 - "$ANCHOR_FILE" "$WORK/$PUBLISHED_NAME" <<'PY'
import sys

source, target = sys.argv[1], sys.argv[2]
# The consumer tracking fields, and the `> Visual-` fields 0.10.0 retired.
drop = ('> Source:', '> Pinned:', '> Path:', '> Note:', '> Visual-')
with open(source, encoding='utf-8') as handle:
    lines = handle.readlines()
with open(target, 'w', encoding='utf-8') as handle:
    handle.writelines(line for line in lines if not line.startswith(drop))
PY

(
  cd "$WORK"
  git config user.email "dev@purlin.local"
  git config user.name "Purlin Dev"
  git add -A
  GIT_AUTHOR_DATE="2026-01-01T00:00:00+0000" \
    GIT_COMMITTER_DATE="2026-01-01T00:00:00+0000" \
    git commit -q -m "publish the security policy anchor"
  git push -q origin HEAD:refs/heads/main
)

SHA=$(git -C "$BARE_REPO" rev-parse HEAD)
rm -rf "$WORK"

report_pin "$SHA"
echo ""
echo "Next: run purlin:status to see the anchor, or"
echo "bash dev/test_e2e_external_refs.sh to run the checks that read it."
echo "To see a pin go behind, add a commit to the bare repository and run"
echo "purlin:drift."
