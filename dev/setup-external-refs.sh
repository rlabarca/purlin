#!/usr/bin/env bash
# Creates the dog-food external reference repo (once).
# This bare git repo acts as a mock "remote" for the security_no_dangerous_patterns anchor.
# Safe to re-run — skips if the repo already exists.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
EXT_DIR="$PROJECT_ROOT/dev/external-refs"
BARE_REPO="$EXT_DIR/security-policy.git"
ANCHOR_FILE="$PROJECT_ROOT/specs/_anchors/security_no_dangerous_patterns.md"

if [[ -d "$BARE_REPO" ]]; then
  SHA=$(git -C "$BARE_REPO" rev-parse HEAD 2>/dev/null || echo "unknown")
  echo "External repo already exists at $BARE_REPO (HEAD: ${SHA:0:7})"
  echo "To reset: rm -rf $BARE_REPO && bash $0"
  exit 0
fi

echo "=== Creating external reference repo ==="

# Create bare repo
mkdir -p "$EXT_DIR"
git init --bare -q "$BARE_REPO"

# Clone, populate, push
WORK="${BARE_REPO}_work"
git clone -q "$BARE_REPO" "$WORK"

# Strip Source/Pinned/Path metadata from the copy going into the external repo
# (the external repo is the source — it shouldn't contain self-referencing metadata)
python3 -c "
with open('$ANCHOR_FILE') as f:
    lines = f.readlines()
filtered = [l for l in lines if not l.startswith('> Source:') and not l.startswith('> Pinned:') and not l.startswith('> Path:')]
with open('$WORK/security_policy.md', 'w') as f:
    f.writelines(filtered)
"

(cd "$WORK" && git add -A && git commit -q -m "initial security policy spec")
(cd "$WORK" && git push -q origin main 2>/dev/null || git push -q origin master 2>/dev/null)

# Get the HEAD SHA
SHA=$(git -C "$BARE_REPO" rev-parse HEAD)

# Clean up working copy
rm -rf "$WORK"

echo "Bare repo: $BARE_REPO"
echo "HEAD SHA:  $SHA"

# Update the anchor to point to the external repo (only if not already pointing)
if ! grep -q '^> Source:' "$ANCHOR_FILE" 2>/dev/null; then
  python3 -c "
with open('$ANCHOR_FILE') as f:
    content = f.read()

lines = content.split('\n')
insert_idx = 1
for i, line in enumerate(lines):
    if line.startswith('# Anchor:'):
        insert_idx = i + 1
        while insert_idx < len(lines) and lines[insert_idx].strip() == '':
            insert_idx += 1
        break

new_lines = [
    '> Source: $BARE_REPO',
    '> Path: security_policy.md',
    '> Pinned: $SHA',
]
for j, nl in enumerate(new_lines):
    lines.insert(insert_idx + j, nl)

with open('$ANCHOR_FILE', 'w') as f:
    f.write('\n'.join(lines))
"
  echo "Updated $ANCHOR_FILE with Source/Path/Pinned"
else
  echo "Anchor already has > Source: metadata — skipping update"
fi

echo ""
echo "Done. Run 'purlin:status' to see the external reference."
echo "To test staleness: add a commit to the bare repo, then run 'purlin:drift'."
