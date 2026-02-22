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
# 3b. Command File Sync (Section 2.6)
###############################################################################
COMMANDS_SRC="$SUBMODULE_DIR/.claude/commands"
COMMANDS_DST="$PROJECT_ROOT/.claude/commands"

echo "────────────────────────────────────────"
echo "  Command File Updates"
echo "────────────────────────────────────────"
echo ""

if [ -d "$COMMANDS_SRC" ]; then
    CMD_UPDATED=0
    CMD_ADDED=0
    CMD_WARNED=0

    CHANGED_CMDS="$(git -C "$SUBMODULE_DIR" diff --name-only "$OLD_SHA"..HEAD -- .claude/commands/ 2>/dev/null || true)"

    if [ -n "$CHANGED_CMDS" ]; then
        mkdir -p "$COMMANDS_DST"
        while IFS= read -r rel_path; do
            [ -n "$rel_path" ] || continue
            fname="$(basename "$rel_path")"
            src_file="$SUBMODULE_DIR/$rel_path"
            dst_file="$COMMANDS_DST/$fname"

            # File deleted upstream
            if [ ! -f "$src_file" ]; then
                echo "  DELETED upstream: $fname (manual cleanup may be required)"
                continue
            fi

            if [ -f "$dst_file" ]; then
                # Compare consumer copy against what it was at old SHA
                old_content="$(git -C "$SUBMODULE_DIR" show "$OLD_SHA:.claude/commands/$fname" 2>/dev/null || true)"
                dst_content="$(cat "$dst_file")"
                if [ -n "$old_content" ] && [ "$old_content" != "$dst_content" ]; then
                    echo "  WARNING: $fname has local modifications — manual review required"
                    echo "    Updated version at: $SUBMODULE_DIR/.claude/commands/$fname"
                    CMD_WARNED=$((CMD_WARNED + 1))
                    continue
                fi
                cp "$src_file" "$dst_file"
                CMD_UPDATED=$((CMD_UPDATED + 1))
                echo "  Updated: $fname"
            else
                cp "$src_file" "$dst_file"
                CMD_ADDED=$((CMD_ADDED + 1))
                echo "  Added: $fname (new command)"
            fi
        done <<< "$CHANGED_CMDS"

        echo ""
        # Summary line
        summary_parts=()
        [ "$CMD_UPDATED" -gt 0 ] && summary_parts+=("$CMD_UPDATED command file(s) updated")
        [ "$CMD_ADDED" -gt 0 ] && summary_parts+=("$CMD_ADDED new command(s) added")
        [ "$CMD_WARNED" -gt 0 ] && summary_parts+=("$CMD_WARNED require manual review")
        if [ "${#summary_parts[@]}" -gt 0 ]; then
            (IFS=', '; echo "Summary: ${summary_parts[*]}")
        fi
    else
        echo "  (no command file changes)"
    fi
else
    echo "  (no .claude/commands/ found in submodule)"
fi
echo ""

###############################################################################
# 4. SHA Update
###############################################################################
echo "$CURRENT_SHA" > "$SHA_FILE"
echo "=== SHA marker updated to ${CURRENT_SHA:0:12} ==="
