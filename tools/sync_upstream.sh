#!/bin/bash
# sync_upstream.sh — Audit upstream submodule changes and update the sync marker.
# Usage: Run from any directory.  The script resolves paths from its own location.
set -euo pipefail

###############################################################################
# 1. Path Resolution (same approach as bootstrap.sh)
###############################################################################
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SUBMODULE_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
PROJECT_ROOT="$(cd "$SUBMODULE_DIR/.." && pwd)"

###############################################################################
# 2. SHA Comparison
###############################################################################
SHA_FILE="$PROJECT_ROOT/.agentic_devops/.upstream_sha"

if [ ! -f "$SHA_FILE" ]; then
    echo "ERROR: $SHA_FILE not found."
    echo "Has this project been bootstrapped?  Run: $(basename "$SUBMODULE_DIR")/tools/bootstrap.sh"
    exit 1
fi

OLD_SHA="$(cat "$SHA_FILE" | tr -d '[:space:]')"
CURRENT_SHA="$(git -C "$SUBMODULE_DIR" rev-parse HEAD)"

if [ "$OLD_SHA" = "$CURRENT_SHA" ]; then
    echo "Already up to date. (SHA: ${CURRENT_SHA:0:12})"
    exit 0
fi

echo "=== Upstream Sync Report ==="
echo ""
echo "Previous SHA: ${OLD_SHA:0:12}"
echo "Current  SHA: ${CURRENT_SHA:0:12}"
echo ""

###############################################################################
# 3. Changelog Display
###############################################################################

# --- Instruction Changes ---
echo "────────────────────────────────────────"
echo "  Instruction Changes"
echo "────────────────────────────────────────"
echo ""

INSTR_DIFF="$(git -C "$SUBMODULE_DIR" diff --stat --no-color "$OLD_SHA"..HEAD -- instructions/ 2>/dev/null || true)"
if [ -n "$INSTR_DIFF" ]; then
    echo "$INSTR_DIFF"
    echo ""
    echo "NOTE: Base instruction changes are automatic — they are read at launch time"
    echo "      by the launcher scripts. No action is required unless your overrides"
    echo "      depend on specific section structure."
    echo ""

    # Structural change detection: flag modified markdown headers
    HEADER_CHANGES="$(git -C "$SUBMODULE_DIR" diff --no-color "$OLD_SHA"..HEAD -- instructions/ 2>/dev/null \
        | grep -E '^[+-]#{2,} ' | grep -v '^---' | grep -v '^\+\+\+' || true)"
    if [ -n "$HEADER_CHANGES" ]; then
        echo "WARNING: Structural changes detected in instructions (section headers modified)."
        echo "  These may affect your override files.  Review the changes below:"
        echo ""
        echo "$HEADER_CHANGES"
        echo ""
    fi
else
    echo "  (no changes)"
    echo ""
fi

# --- Tool Changes ---
echo "────────────────────────────────────────"
echo "  Tool Changes"
echo "────────────────────────────────────────"
echo ""

TOOL_DIFF="$(git -C "$SUBMODULE_DIR" diff --stat --no-color "$OLD_SHA"..HEAD -- tools/ 2>/dev/null || true)"
if [ -n "$TOOL_DIFF" ]; then
    echo "$TOOL_DIFF"
    echo ""
    echo "NOTE: Tool changes are automatic — tools are used directly from the submodule."
    echo "      No action is required."
    echo ""
else
    echo "  (no changes)"
    echo ""
fi

# --- Full Diff (for detailed review) ---
echo "────────────────────────────────────────"
echo "  Full Diff (instructions/)"
echo "────────────────────────────────────────"
echo ""
git -C "$SUBMODULE_DIR" diff --no-color "$OLD_SHA"..HEAD -- instructions/ 2>/dev/null || true
echo ""

echo "────────────────────────────────────────"
echo "  Full Diff (tools/)"
echo "────────────────────────────────────────"
echo ""
git -C "$SUBMODULE_DIR" diff --no-color "$OLD_SHA"..HEAD -- tools/ 2>/dev/null || true
echo ""

###############################################################################
# 4. SHA Update
###############################################################################
echo "$CURRENT_SHA" > "$SHA_FILE"
echo "=== SHA marker updated to ${CURRENT_SHA:0:12} ==="
