#!/usr/bin/env bash
# Gate hook: blocks writes to specs/_invariants/i_* unless bypass lock exists
set -euo pipefail

FILE_PATH="${TOOL_INPUT_FILE_PATH:-${TOOL_INPUT_file_path:-}}"
[[ -z "$FILE_PATH" ]] && exit 0

# Only guard invariant files (handle both absolute and relative paths)
case "$FILE_PATH" in
  */specs/_invariants/i_*|specs/_invariants/i_*) ;;
  *) exit 0 ;;
esac

# Check bypass lock
LOCK_FILE="${PROJECT_ROOT:-.}/.purlin/runtime/invariant_write_lock"
if [[ -f "$LOCK_FILE" ]]; then
  LOCK_TARGET=$(python3 -c "import json,sys; print(json.load(open(sys.argv[1]))['target'])" "$LOCK_FILE" 2>/dev/null || echo "")
  # Allow if lock target matches this file (basename match)
  LOCK_BASE=$(basename "$LOCK_TARGET")
  FILE_BASE=$(basename "$FILE_PATH")
  [[ "$LOCK_BASE" == "$FILE_BASE" ]] && exit 0
fi

echo "BLOCKED: Invariant files are read-only. Use purlin:invariant sync to update from the external source." >&2
exit 2
