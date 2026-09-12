#!/usr/bin/env bash
# Regenerate every tools/*/<name>.skill archive from its sibling <name>.md.
#
# A `.skill` file is a zip holding one entry, `<name>/SKILL.md`. The `.md` beside
# it is what a reviewer reads and what the qa_report spec's rules grep; the zip
# is what a user installs. They must carry the same bytes, so this script is the
# only way either is regenerated (qa_report RULE-6, PROOF-6).
#
# Usage: bash dev/pack_tools.sh
#
# This is a Purlin-repository maintenance script (CLAUDE.md, Tool Folder
# Separation): consumer projects never run it.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

command -v zip >/dev/null 2>&1 || {
  echo "pack_tools: 'zip' is not installed" >&2
  exit 1
}

packed=0
for md in tools/*/*.md; do
  [[ -e "$md" ]] || continue
  dir="$(dirname "$md")"
  name="$(basename "$md" .md)"
  skill="$dir/$name.skill"

  # Stage the file under the directory name the archive must carry.
  stage="$(mktemp -d)"
  trap 'rm -rf "$stage"' EXIT
  mkdir -p "$stage/$name"
  cp "$md" "$stage/$name/SKILL.md"

  rm -f "$skill"
  ( cd "$stage" && zip -q -X -r "archive.zip" "$name/SKILL.md" )
  mv "$stage/archive.zip" "$skill"
  rm -rf "$stage"
  trap - EXIT

  echo "packed $skill  <-  $md"
  packed=$((packed + 1))
done

if [[ $packed -eq 0 ]]; then
  echo "pack_tools: no tools/*/*.md found" >&2
  exit 1
fi
echo "$packed archive(s) regenerated"
