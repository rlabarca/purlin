#!/usr/bin/env bash
# Single entry point for changing the Purlin version string.
#
# `VERSION` at the project root is the source of truth. Every other location
# that carries a literal version is DERIVED from it, and this script is the only
# thing that sets a new number: setup and the upgrade copy it from VERSION into a
# project's settings. A human edits nothing by hand:
#
#   bash dev/bump_version.sh 0.10.1     # set VERSION, propagate everywhere
#   bash dev/bump_version.sh --check    # verify, exit 1 on drift (run by CI)
#
# DERIVED LOCATIONS: the complete list. Add a row here when a new file starts
# carrying a version literal, and `--check` starts guarding it in the same edit.
#
#   .claude-plugin/plugin.json   .version   what the Claude plugin loader reports
#   .purlin/config.json          .version   this repo's own project stamp (optional)
#   docs/running-and-evidence.md   the tag `signed/<version>` its example clones at
#
# NOT derived, and deliberately absent from that list:
#   scripts/mcp/purlin/__init__.py  reads VERSION at runtime via _read_version()
#   skills/init/SKILL.md          documents the field, never restates a number
#
# Governed by specs/instructions/purlin_version.md (RULE-5, 6, 12 and 14).
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
VERSION_FILE="$ROOT/VERSION"

# Derived locations. A `.json` file's `version` key is rewritten; a `.md` page's
# `--branch signed/<version>` is.
DERIVED=(
  ".claude-plugin/plugin.json"
  ".purlin/config.json"
  "docs/running-and-evidence.md"
)

usage() {
  cat <<'EOF'
Usage: bash dev/bump_version.sh <semver>   Set VERSION and propagate to derived locations
       bash dev/bump_version.sh --check    Verify derived locations match VERSION

Derived locations (see the header comment for the authoritative list):
  .claude-plugin/plugin.json   .version
  .purlin/config.json          .version   (optional: only if the repo is itself a Purlin project)
  docs/running-and-evidence.md   the tag signed/<version> its example clones at
EOF
}

# Read the `version` key of a JSON file, or the version of the tag a page's
# example clones at; print nothing if absent.
read_json_version() {
  python3 -c '
import json, re, sys
try:
    with open(sys.argv[1], encoding="utf-8") as f:
        if sys.argv[1].endswith(".md"):
            found = re.search(r"--branch signed/(\S+)", f.read())
            print(found.group(1) if found else "")
        else:
            print(json.load(f).get("version", ""))
except FileNotFoundError:
    pass
' "$1"
}

# Rewrite the `version` key in place, preserving 2-space indent, key order, and
# the ASCII-escaped non-ASCII characters already in these files.
write_json_version() {
  python3 -c '
import json, os, re, sys
path, new = sys.argv[1], sys.argv[2]
if path.endswith(".md"):
    with open(path, encoding="utf-8", newline="") as f:
        text = f.read()
    moved = re.sub(r"(--branch signed/)\S+", lambda m: m.group(1) + new, text)
    if moved != text:
        with open(path, "w", encoding="utf-8", newline="") as f:
            f.write(moved)
    sys.exit(0)
with open(path, encoding="utf-8") as f:
    data = json.load(f)
if data.get("version") == new:
    sys.exit(0)
data["version"] = new
tmp = path + ".tmp"
with open(tmp, "w", encoding="utf-8") as f:
    json.dump(data, f, indent=2)
    f.write("\n")
os.replace(tmp, path)
' "$1" "$2"
}

if [[ $# -ne 1 ]]; then
  usage
  exit 2
fi

if [[ ! -f "$VERSION_FILE" ]]; then
  echo "ERROR: VERSION file not found at $VERSION_FILE" >&2
  exit 1
fi
CURRENT="$(tr -d '[:space:]' < "$VERSION_FILE")"

case "$1" in
  --check)
    DRIFT=0
    echo "VERSION = $CURRENT"
    for rel in "${DERIVED[@]}"; do
      abs="$ROOT/$rel"
      if [[ ! -f "$abs" ]]; then
        # .purlin/config.json only exists when the repo is itself a Purlin
        # project. A consumer checkout of the framework has no such file.
        printf '  %-30s absent (this repository only)\n' "$rel"
        continue
      fi
      got="$(read_json_version "$abs")"
      if [[ -z "$got" ]]; then
        printf '  %-30s FAIL  no version found\n' "$rel"
        DRIFT=1
      elif [[ "$got" == "$CURRENT" ]]; then
        printf '  %-30s ok    %s\n' "$rel" "$got"
      else
        printf '  %-30s DRIFT %s (expected %s)\n' "$rel" "$got" "$CURRENT"
        DRIFT=1
      fi
    done
    if [[ $DRIFT -ne 0 ]]; then
      echo ""
      echo "Version drift detected. Fix with: bash dev/bump_version.sh $CURRENT" >&2
      exit 1
    fi
    echo ""
    echo "All derived locations match VERSION."
    ;;

  -h|--help)
    usage
    ;;

  *)
    NEW="$1"
    if [[ ! "$NEW" =~ ^[0-9]+\.[0-9]+\.[0-9]+$ ]]; then
      echo "ERROR: '$NEW' is not a semver string like 1.2.3" >&2
      exit 2
    fi
    printf '%s\n' "$NEW" > "$VERSION_FILE"
    echo "VERSION = $NEW"
    for rel in "${DERIVED[@]}"; do
      abs="$ROOT/$rel"
      if [[ ! -f "$abs" ]]; then
        printf '  %-30s skipped (absent)\n' "$rel"
        continue
      fi
      before="$(read_json_version "$abs")"
      write_json_version "$abs" "$NEW"
      if [[ "$before" == "$NEW" ]]; then
        printf '  %-30s already %s\n' "$rel" "$NEW"
      else
        printf '  %-30s %s -> %s\n' "$rel" "$before" "$NEW"
      fi
    done
    echo ""
    echo "Next: commit VERSION and every file above in one commit."
    ;;
esac
