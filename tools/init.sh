#!/bin/bash
# init.sh — Unified project initialization and refresh for Purlin.
# Usage: Run from any directory. The script resolves paths from its own location.
#
# Modes:
#   Full Init — when .purlin/ does not exist (first run)
#   Refresh   — when .purlin/ already exists (subsequent runs)
#
# Flags:
#   --quiet                 Suppress all non-error output (errors still go to stderr)
set -euo pipefail

###############################################################################
# 0. CLI Flag Parsing
###############################################################################
QUIET=false

for arg in "$@"; do
    case "$arg" in
        --quiet) QUIET=true ;;
        *) echo "Unknown flag: $arg" >&2; exit 1 ;;
    esac
done

# Output helper: prints only when not in quiet mode
say() {
    if [ "$QUIET" = false ]; then
        echo "$@"
    fi
}

###############################################################################
# 1. Path Resolution (symlink-safe)
###############################################################################
# Resolve symlinks so SCRIPT_DIR is always the real tools/ directory,
# even when invoked via the submodule root symlink (purlin/init.sh -> tools/init.sh).
SOURCE="${BASH_SOURCE[0]}"
while [ -L "$SOURCE" ]; do
    LINK_DIR="$(cd "$(dirname "$SOURCE")" && pwd)"
    SOURCE="$(readlink "$SOURCE")"
    [[ "$SOURCE" != /* ]] && SOURCE="$LINK_DIR/$SOURCE"
done
SCRIPT_DIR="$(cd "$(dirname "$SOURCE")" && pwd)"
SUBMODULE_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
SUBMODULE_NAME="$(basename "$SUBMODULE_DIR")"
PROJECT_ROOT="$(cd "$SUBMODULE_DIR/.." && pwd)"

# Source shared Python resolver (python_environment.md §2.2)
export PURLIN_PROJECT_ROOT="$PROJECT_ROOT"
source "$SCRIPT_DIR/resolve_python.sh"

###############################################################################
# 1b. Preflight Checks (init_preflight_checks.md §2.1-2.3)
###############################################################################
# Validate required and recommended tools BEFORE any initialization work.
# Must run before the standalone guard (1c) since that guard uses git.
PREFLIGHT_FAILED=false
PREFLIGHT_WARNINGS=""

# Detect platform for install suggestions
PLATFORM="$(uname -s)"

# Required: git (blocks init)
if ! command -v git >/dev/null 2>&1; then
    PREFLIGHT_FAILED=true
    if [ "$PLATFORM" = "Darwin" ]; then
        INSTALL_CMD="brew install git"
    else
        INSTALL_CMD="sudo apt-get install git"
    fi
    say "  git ........... NOT FOUND"
    say "    Install: $INSTALL_CMD"
    say "    Docs: https://git-scm.com/downloads"
fi

# Recommended: claude CLI (warns, continues)
if ! command -v claude >/dev/null 2>&1; then
    PREFLIGHT_WARNINGS="${PREFLIGHT_WARNINGS}claude,"
    say "  claude ........ NOT FOUND (recommended)"
    say "    Install: npm install -g @anthropic-ai/claude-code"
    say "    Note: MCP servers will not be installed without Claude CLI."
fi

# Optional: node/npx (warns, continues)
if ! command -v node >/dev/null 2>&1; then
    PREFLIGHT_WARNINGS="${PREFLIGHT_WARNINGS}node,"
    if [ "$PLATFORM" = "Darwin" ]; then
        NODE_INSTALL_CMD="brew install node"
    else
        NODE_INSTALL_CMD="sudo apt-get install nodejs npm"
    fi
    say "  node .......... NOT FOUND (optional)"
    say "    Install: $NODE_INSTALL_CMD"
    say "    Note: Playwright web testing will be unavailable without Node.js."
fi

if [ "$PREFLIGHT_FAILED" = true ]; then
    echo "" >&2
    echo "Fix these and re-run: $SUBMODULE_NAME/tools/init.sh" >&2
    exit 1
fi

###############################################################################
# 1c. Standalone Mode Guard (project_init.md §2.13)
###############################################################################
# In a consumer project, $PROJECT_ROOT is the consumer's git repo root.
# In standalone mode (Purlin IS the project), $PROJECT_ROOT is the parent
# directory of the Purlin repo, which is NOT a git repository.
# Note: We cannot check for .purlin/ in $SUBMODULE_DIR because .purlin/ is
# tracked in the Purlin repo and will exist in any submodule clone too.
if ! git -C "$PROJECT_ROOT" rev-parse --is-inside-work-tree >/dev/null 2>&1; then
    echo "ERROR: init.sh is for consumer projects that use Purlin as a submodule." >&2
    echo "  It cannot be run inside the Purlin repository itself." >&2
    echo "  ($PROJECT_ROOT is not a git repository.)" >&2
    exit 1
fi

###############################################################################
# 2. Mode Detection
###############################################################################
if [ -d "$PROJECT_ROOT/.purlin" ]; then
    MODE="refresh"
else
    MODE="full"
fi

###############################################################################
# Shared Helpers
###############################################################################

# Generate the unified Purlin launcher script (pl-run.sh).
# Usage: generate_purlin_launcher <output_file>
generate_purlin_launcher() {
    local OUTPUT_FILE="$1"
    local FRAMEWORK_VAR="\$SCRIPT_DIR/$SUBMODULE_NAME"
    local TOOLS_ROOT="$SUBMODULE_NAME/tools"

    # Part 1: Shebang and SCRIPT_DIR (literal)
    cat > "$OUTPUT_FILE" << 'LAUNCHER_EOF'
#!/bin/bash
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
export PURLIN_PROJECT_ROOT="$SCRIPT_DIR"

# Parse arguments
PURLIN_MODE=""
PURLIN_AUTO_START=""
PURLIN_MODEL_OVERRIDE=""
PURLIN_EFFORT_OVERRIDE=""
PURLIN_WORKTREE=""
PURLIN_FIND_WORK=""
PURLIN_VERIFY_FEATURE=""
PURLIN_YOLO=""
PURLIN_NO_SAVE=""

while [[ $# -gt 0 ]]; do
    case "$1" in
        --model)
            if [[ -n "${2:-}" && ! "$2" =~ ^-- ]]; then
                PURLIN_MODEL_OVERRIDE="$2"
                shift 2
            else
                # Bare --model: trigger interactive selection
                PURLIN_MODEL_OVERRIDE="__interactive__"
                shift
            fi
            ;;
        --effort)
            PURLIN_EFFORT_OVERRIDE="$2"
            shift 2
            ;;
        --yolo) PURLIN_YOLO="true"; shift ;;
        --no-yolo) PURLIN_YOLO="false"; shift ;;
        --find-work)
            PURLIN_FIND_WORK="$2"
            shift 2
            ;;
        --no-save) PURLIN_NO_SAVE="true"; shift ;;
        --mode)
            PURLIN_MODE="$2"
            shift 2
            ;;
        --auto-build)
            PURLIN_MODE="engineer"
            PURLIN_AUTO_START="true"
            shift
            ;;
        --auto-verify)
            PURLIN_MODE="qa"
            PURLIN_AUTO_START="true"
            shift
            ;;
        --pm) PURLIN_MODE="pm"; shift ;;
        --qa) PURLIN_MODE="qa"; shift ;;
        --verify)
            PURLIN_MODE="qa"
            if [[ -n "${2:-}" && ! "$2" =~ ^-- ]]; then
                PURLIN_VERIFY_FEATURE="$2"
                shift 2
            else
                shift
            fi
            ;;
        --auto-start) PURLIN_AUTO_START="true"; shift ;;
        --worktree) PURLIN_WORKTREE="true"; shift ;;
        *) shift ;;
    esac
done
LAUNCHER_EOF

    # Part 2: CORE_DIR with submodule path (expanded)
    cat >> "$OUTPUT_FILE" << LAUNCHER_EOF
CORE_DIR="$FRAMEWORK_VAR"
TOOLS_ROOT="$TOOLS_ROOT"
LAUNCHER_EOF

    # Part 3: CORE_DIR fallback, terminal identity, and first-run detection (literal)
    cat >> "$OUTPUT_FILE" << 'LAUNCHER_EOF'

# Fall back to local instructions/ if not a submodule consumer
if [ ! -d "$CORE_DIR/instructions" ]; then
    CORE_DIR="$SCRIPT_DIR"
fi

# Source terminal identity helper (no-op if missing)
if [ -f "$CORE_DIR/tools/terminal/identity.sh" ]; then
    source "$CORE_DIR/tools/terminal/identity.sh"
fi

# First-run / model selection
AGENT_ROLE="purlin"
export AGENT_ROLE
RESOLVER="$CORE_DIR/tools/config/resolve_config.py"

# Check if purlin config exists
HAS_CONFIG="false"
if [ -f "$RESOLVER" ]; then
    HAS_CONFIG=$(PURLIN_PROJECT_ROOT="$SCRIPT_DIR" python3 "$RESOLVER" has_agent_config purlin 2>/dev/null || echo "false")
fi

if [[ "$PURLIN_MODEL_OVERRIDE" == "__interactive__" ]] || [[ "$HAS_CONFIG" == "false" ]]; then
    echo ""
    echo "Select model:"
    echo "  1. Opus 4.6         (200K context)"
    echo "  2. Sonnet 4.6       (200K context, cost-efficient)"
    echo "  3. Opus 4.6 [1M]    (1M context, extended)"
    echo ""
    read -p "Choice [1]: " MODEL_CHOICE
    MODEL_CHOICE="${MODEL_CHOICE:-1}"

    case "$MODEL_CHOICE" in
        1) SELECTED_MODEL="claude-opus-4-6" ;;
        2) SELECTED_MODEL="claude-sonnet-4-6" ;;
        3) SELECTED_MODEL="claude-opus-4-6[1m]" ;;
        *) SELECTED_MODEL="claude-opus-4-6" ;;
    esac

    echo ""
    echo "Select effort:"
    echo "  1. high   (thorough)"
    echo "  2. medium (balanced)"
    echo ""
    read -p "Choice [1]: " EFFORT_CHOICE
    EFFORT_CHOICE="${EFFORT_CHOICE:-1}"

    case "$EFFORT_CHOICE" in
        1) SELECTED_EFFORT="high" ;;
        2) SELECTED_EFFORT="medium" ;;
        *) SELECTED_EFFORT="high" ;;
    esac

    # Store selection
    if [ -f "$RESOLVER" ]; then
        PURLIN_PROJECT_ROOT="$SCRIPT_DIR" python3 "$RESOLVER" set_agent_config purlin model "$SELECTED_MODEL" 2>/dev/null || true
        PURLIN_PROJECT_ROOT="$SCRIPT_DIR" python3 "$RESOLVER" set_agent_config purlin effort "$SELECTED_EFFORT" 2>/dev/null || true
    fi
    echo ""
    echo "Stored in .purlin/config.local.json. Override with --model/--effort."
    echo ""
fi

# --- Read agent config via resolver ---
AGENT_MODEL=""
AGENT_EFFORT=""
AGENT_BYPASS="false"
AGENT_FIND_WORK="true"
AGENT_AUTO_START="false"
AGENT_MODEL_WARNING=""
AGENT_MODEL_WARNING_DISMISSED="false"

if [ -f "$RESOLVER" ]; then
    eval "$(PURLIN_PROJECT_ROOT="$SCRIPT_DIR" python3 "$RESOLVER" "$AGENT_ROLE" 2>/dev/null)"
fi

# --- Model warning display and auto-acknowledge ---
if [ -n "$AGENT_MODEL_WARNING" ] && [ "$AGENT_MODEL_WARNING_DISMISSED" != "true" ]; then
    echo "============================================================" >&2
    echo "WARNING: $AGENT_MODEL_WARNING" >&2
    echo "By continuing, you are acknowledging this warning." >&2
    echo "============================================================" >&2
    if [ -f "$RESOLVER" ]; then
        PURLIN_PROJECT_ROOT="$SCRIPT_DIR" python3 "$RESOLVER" acknowledge_warning "$AGENT_MODEL" 2>/dev/null
    fi
fi

# CLI overrides (apply sticky + ephemeral flags)
if [[ -n "$PURLIN_MODEL_OVERRIDE" && "$PURLIN_MODEL_OVERRIDE" != "__interactive__" ]]; then
    # Resolve short names
    case "$PURLIN_MODEL_OVERRIDE" in
        opus|Opus*) AGENT_MODEL="claude-opus-4-6" ;;
        sonnet|Sonnet*) AGENT_MODEL="claude-sonnet-4-6" ;;
        haiku|Haiku*) AGENT_MODEL="claude-haiku-4-5-20251001" ;;
        *) AGENT_MODEL="$PURLIN_MODEL_OVERRIDE" ;;
    esac
fi
if [[ -n "$PURLIN_EFFORT_OVERRIDE" ]]; then
    AGENT_EFFORT="$PURLIN_EFFORT_OVERRIDE"
fi
if [[ -n "$PURLIN_YOLO" ]]; then
    AGENT_BYPASS="$PURLIN_YOLO"
fi
if [[ -n "$PURLIN_FIND_WORK" ]]; then
    AGENT_FIND_WORK="$PURLIN_FIND_WORK"
fi
if [[ -n "$PURLIN_AUTO_START" ]]; then
    AGENT_AUTO_START="true"
fi

# --- Validate startup controls ---
if [ "$AGENT_FIND_WORK" = "false" ] && [ "$AGENT_AUTO_START" = "true" ]; then
    echo "Error: find_work=false with auto_start=true is not valid." >&2
    exit 1
fi

# --- Persist sticky flags (after validation, before launch) ---
if [[ "$PURLIN_NO_SAVE" != "true" ]] && [ -f "$RESOLVER" ]; then
    if [[ -n "$PURLIN_MODEL_OVERRIDE" && "$PURLIN_MODEL_OVERRIDE" != "__interactive__" ]]; then
        PURLIN_PROJECT_ROOT="$SCRIPT_DIR" python3 "$RESOLVER" set_agent_config purlin model "$AGENT_MODEL" 2>/dev/null
    fi
    if [[ -n "$PURLIN_EFFORT_OVERRIDE" ]]; then
        PURLIN_PROJECT_ROOT="$SCRIPT_DIR" python3 "$RESOLVER" set_agent_config purlin effort "$AGENT_EFFORT" 2>/dev/null
    fi
    if [[ -n "$PURLIN_YOLO" ]]; then
        PURLIN_PROJECT_ROOT="$SCRIPT_DIR" python3 "$RESOLVER" set_agent_config purlin bypass_permissions "$PURLIN_YOLO" 2>/dev/null
    fi
    if [[ -n "$PURLIN_FIND_WORK" ]]; then
        PURLIN_PROJECT_ROOT="$SCRIPT_DIR" python3 "$RESOLVER" set_agent_config purlin find_work "$PURLIN_FIND_WORK" 2>/dev/null
    fi
fi

# --- Prompt assembly ---
PROMPT_FILE=$(mktemp)
cleanup() {
    type clear_agent_identity >/dev/null 2>&1 && clear_agent_identity
    rm -f "$PROMPT_FILE"
}
trap cleanup EXIT

cat "$CORE_DIR/instructions/HOW_WE_WORK_BASE.md" > "$PROMPT_FILE"
printf "\n\n" >> "$PROMPT_FILE"

if [ -f "$CORE_DIR/instructions/PURLIN_BASE.md" ]; then
    cat "$CORE_DIR/instructions/PURLIN_BASE.md" >> "$PROMPT_FILE"
fi

if [ -f "$SCRIPT_DIR/.purlin/HOW_WE_WORK_OVERRIDES.md" ]; then
    printf "\n\n" >> "$PROMPT_FILE"
    cat "$SCRIPT_DIR/.purlin/HOW_WE_WORK_OVERRIDES.md" >> "$PROMPT_FILE"
fi

if [ -f "$SCRIPT_DIR/.purlin/PURLIN_OVERRIDES.md" ]; then
    printf "\n\n" >> "$PROMPT_FILE"
    cat "$SCRIPT_DIR/.purlin/PURLIN_OVERRIDES.md" >> "$PROMPT_FILE"
fi

# --- Session message construction ---
SESSION_MSG="Begin Purlin session."
if [[ -n "$PURLIN_MODE" ]]; then
    case "$PURLIN_MODE" in
        engineer) SESSION_MSG="Begin Purlin session. Enter Engineer mode. Run /pl-build." ;;
        qa)
            if [[ -n "${PURLIN_VERIFY_FEATURE:-}" ]]; then
                SESSION_MSG="Begin Purlin session. Enter QA mode. Run /pl-verify $PURLIN_VERIFY_FEATURE."
            else
                SESSION_MSG="Begin Purlin session. Enter QA mode. Run /pl-verify."
            fi
            ;;
        pm) SESSION_MSG="Begin Purlin session. Enter PM mode." ;;
    esac
fi

# --- Worktree support ---
if [[ "$PURLIN_WORKTREE" == "true" ]]; then
    WORKTREE_BRANCH="purlin-${PURLIN_MODE:-open}-$(date +%Y%m%d-%H%M%S)"
    WORKTREE_DIR="$SCRIPT_DIR/.purlin/worktrees/$WORKTREE_BRANCH"
    mkdir -p "$SCRIPT_DIR/.purlin/worktrees"
    if git worktree add "$WORKTREE_DIR" -b "$WORKTREE_BRANCH" 2>/dev/null; then
        # Assign worktree label (W1, W2, ...) — gap-filling
        _used_nums=()
        for _lf in "$SCRIPT_DIR/.purlin/worktrees"/*/.purlin_worktree_label; do
            [ -f "$_lf" ] || continue
            _n=$(tr -cd '0-9' < "$_lf")
            [ -n "$_n" ] && _used_nums+=("$_n")
        done
        _next=1
        while printf '%s\n' "${_used_nums[@]}" 2>/dev/null | grep -qx "$_next"; do
            _next=$((_next + 1))
        done
        WORKTREE_LABEL="W${_next}"
        echo "$WORKTREE_LABEL" > "$WORKTREE_DIR/.purlin_worktree_label"

        echo "Working in worktree: $WORKTREE_DIR ($WORKTREE_LABEL)"
        echo "Branch: $WORKTREE_BRANCH"
        echo "Run /pl-merge when done to merge back."
        echo ""
        cd "$WORKTREE_DIR"
        export PURLIN_PROJECT_ROOT="$WORKTREE_DIR"
    else
        echo "ERROR: Failed to create worktree. Continuing without isolation." >&2
    fi
fi

# --- Compute display identity (mode + optional worktree label) ---
case "${PURLIN_MODE:-}" in
    engineer) MODE_NAME="Engineer" ;;
    qa)       MODE_NAME="QA" ;;
    pm)       MODE_NAME="PM" ;;
    *)        MODE_NAME="Purlin" ;;
esac
# Badge includes branch or worktree label for immediate context.
# Worktree label wins over branch when present.
DISPLAY_NAME="$MODE_NAME"
if [[ -f "$PURLIN_PROJECT_ROOT/.purlin_worktree_label" ]]; then
    _wt_label=$(cat "$PURLIN_PROJECT_ROOT/.purlin_worktree_label")
    DISPLAY_NAME="$MODE_NAME ($_wt_label)"
else
    _BRANCH=$(git rev-parse --abbrev-ref HEAD 2>/dev/null)
    if [[ -n "$_BRANCH" ]]; then
        DISPLAY_NAME="$MODE_NAME ($_BRANCH)"
    fi
fi
type set_agent_identity >/dev/null 2>&1 && set_agent_identity "$DISPLAY_NAME"

# --- Build CLI args and dispatch ---
CLI_ARGS=()
CLI_ARGS+=(--model "$AGENT_MODEL")

if [[ -n "$AGENT_EFFORT" && "$AGENT_EFFORT" != "default" ]]; then
    CLI_ARGS+=(--effort "$AGENT_EFFORT")
fi

# Pass --dangerously-skip-permissions when bypass is enabled
if [ "$AGENT_BYPASS" = "true" ]; then
    CLI_ARGS+=(--dangerously-skip-permissions)
fi

PROJECT_NAME="$(basename "$SCRIPT_DIR")"
SESSION_NAME="$PROJECT_NAME | $DISPLAY_NAME"
CLI_ARGS+=(--remote-control "$SESSION_NAME")
CLI_ARGS+=(--name "$SESSION_NAME")

claude "${CLI_ARGS[@]}" --append-system-prompt-file "$PROMPT_FILE" "$SESSION_MSG"
LAUNCHER_EOF

    chmod +x "$OUTPUT_FILE"
}

# Copy/refresh command files from submodule to project root.
# Sets CMD_COPIED and CMD_SKIPPED counters.
copy_command_files() {
    local COMMANDS_SRC="$SUBMODULE_DIR/.claude/commands"
    local COMMANDS_DST="$PROJECT_ROOT/.claude/commands"
    CMD_COPIED=0
    CMD_SKIPPED=0

    if [ -d "$COMMANDS_SRC" ]; then
        mkdir -p "$COMMANDS_DST"
        for src_file in "$COMMANDS_SRC"/*.md; do
            [ -f "$src_file" ] || continue
            local fname
            fname="$(basename "$src_file")"
            # pl-edit-base.md MUST NEVER be copied to consumer projects
            if [ "$fname" = "pl-edit-base.md" ]; then
                continue
            fi
            local dst_file="$COMMANDS_DST/$fname"
            if [ -f "$dst_file" ] && [ "$dst_file" -nt "$src_file" ]; then
                CMD_SKIPPED=$((CMD_SKIPPED + 1))
            else
                cp "$src_file" "$dst_file"
                CMD_COPIED=$((CMD_COPIED + 1))
            fi
        done
    fi
}

# Copy agent definition files from submodule to consumer project.
# Same skip logic as copy_command_files: preserve locally modified (newer) files.
copy_agent_files() {
    local AGENTS_SRC="$SUBMODULE_DIR/.claude/agents"
    local AGENTS_DST="$PROJECT_ROOT/.claude/agents"
    AGENT_COPIED=0
    AGENT_SKIPPED=0

    if [ -d "$AGENTS_SRC" ]; then
        mkdir -p "$AGENTS_DST"
        for src_file in "$AGENTS_SRC"/*.md; do
            [ -f "$src_file" ] || continue
            local fname
            fname="$(basename "$src_file")"
            local dst_file="$AGENTS_DST/$fname"
            if [ -f "$dst_file" ] && [ "$dst_file" -nt "$src_file" ]; then
                AGENT_SKIPPED=$((AGENT_SKIPPED + 1))
            else
                cp "$src_file" "$dst_file"
                AGENT_COPIED=$((AGENT_COPIED + 1))
            fi
        done
    fi
}

# Record the current submodule HEAD SHA.
record_upstream_sha() {
    local sha
    sha="$(git -C "$SUBMODULE_DIR" rev-parse HEAD)"
    echo "$sha" > "$PROJECT_ROOT/.purlin/.upstream_sha"
    echo "$sha"
}

# Generate the project-root shim (pl-init.sh).
generate_shim() {
    local REMOTE_URL
    REMOTE_URL="$(git -C "$SUBMODULE_DIR" remote get-url origin 2>/dev/null || echo "unknown")"
    local PINNED_SHA
    PINNED_SHA="$(git -C "$SUBMODULE_DIR" rev-parse HEAD)"
    local VERSION_TAG
    VERSION_TAG="$(git -C "$SUBMODULE_DIR" describe --tags --abbrev=0 HEAD 2>/dev/null || echo "untagged")"

    cat > "$PROJECT_ROOT/pl-init.sh" << SHIM_EOF
#!/bin/bash
# pl-init.sh — Purlin project initialization shim.
# This file is auto-generated by init.sh. Commit it to your repository.
#
# Repo:    ${REMOTE_URL}
# SHA:     ${PINNED_SHA}
# Version: ${VERSION_TAG}
# Submodule: ${SUBMODULE_NAME}
#
# Run this script to initialize or refresh the Purlin submodule.
# It works even before the submodule is populated (fresh clone).

SCRIPT_DIR="\$(cd "\$(dirname "\${BASH_SOURCE[0]}")" && pwd)"
INIT_SCRIPT="\$SCRIPT_DIR/${SUBMODULE_NAME}/tools/init.sh"

if [ ! -f "\$INIT_SCRIPT" ]; then
    echo "Initializing submodule ${SUBMODULE_NAME}..." >&2
    git -C "\$SCRIPT_DIR" submodule update --init "${SUBMODULE_NAME}"
fi

if [ -f "\$INIT_SCRIPT" ]; then
    exec "\$INIT_SCRIPT" "\$@"
else
    echo "ERROR: Could not find ${SUBMODULE_NAME}/tools/init.sh after submodule init." >&2
    exit 1
fi
SHIM_EOF
    chmod +x "$PROJECT_ROOT/pl-init.sh"
}

# Create CDD convenience symlinks at the project root.
create_cdd_symlinks() {
    local start_target="$SUBMODULE_NAME/tools/cdd/start.sh"
    local stop_target="$SUBMODULE_NAME/tools/cdd/stop.sh"

    # pl-cdd-start.sh
    if [ -L "$PROJECT_ROOT/pl-cdd-start.sh" ]; then
        local current_target
        current_target="$(readlink "$PROJECT_ROOT/pl-cdd-start.sh")"
        if [ "$current_target" != "$start_target" ]; then
            ln -sf "$start_target" "$PROJECT_ROOT/pl-cdd-start.sh"
        fi
    elif [ -e "$PROJECT_ROOT/pl-cdd-start.sh" ]; then
        # Regular file exists where symlink should be — replace it
        rm -f "$PROJECT_ROOT/pl-cdd-start.sh"
        ln -s "$start_target" "$PROJECT_ROOT/pl-cdd-start.sh"
    else
        ln -s "$start_target" "$PROJECT_ROOT/pl-cdd-start.sh"
    fi

    # pl-cdd-stop.sh
    if [ -L "$PROJECT_ROOT/pl-cdd-stop.sh" ]; then
        local current_target
        current_target="$(readlink "$PROJECT_ROOT/pl-cdd-stop.sh")"
        if [ "$current_target" != "$stop_target" ]; then
            ln -sf "$stop_target" "$PROJECT_ROOT/pl-cdd-stop.sh"
        fi
    elif [ -e "$PROJECT_ROOT/pl-cdd-stop.sh" ]; then
        # Regular file exists where symlink should be — replace it
        rm -f "$PROJECT_ROOT/pl-cdd-stop.sh"
        ln -s "$stop_target" "$PROJECT_ROOT/pl-cdd-stop.sh"
    else
        ln -s "$stop_target" "$PROJECT_ROOT/pl-cdd-stop.sh"
    fi
}

# Install the Purlin session-recovery hook into .claude/settings.json (§2.15).
# Idempotent: creates/merges without touching existing hooks or settings.
install_session_hook() {
    local SETTINGS_FILE="$PROJECT_ROOT/.claude/settings.json"
    mkdir -p "$PROJECT_ROOT/.claude"

    "$PYTHON_EXE" -c "
import json, os, sys

settings_path = sys.argv[1]

clear_entry = {
    'matcher': 'clear',
    'hooks': [
        {
            'type': 'command',
            'command': \"echo 'IMPORTANT: Context was cleared. Run /pl-resume immediately to restore session context.'\"
        }
    ]
}

compact_entry = {
    'matcher': 'compact',
    'hooks': [
        {
            'type': 'command',
            'command': \"echo 'IMPORTANT: Context was compacted. This project uses role-restricted Purlin agents. Role boundaries: Architect/PM never write code; Builder never writes specs; QA never writes app code. Run /pl-resume immediately to restore session context.'\"
        }
    ]
}

# Read existing settings or start fresh
settings = {}
if os.path.exists(settings_path):
    try:
        with open(settings_path, 'r') as f:
            settings = json.load(f)
    except (json.JSONDecodeError, IOError, OSError):
        settings = {}

# Ensure hooks.SessionStart exists
if 'hooks' not in settings:
    settings['hooks'] = {}
if 'SessionStart' not in settings['hooks']:
    settings['hooks']['SessionStart'] = []

# Add clear matcher if not present
has_clear = any(
    entry.get('matcher') == 'clear'
    for entry in settings['hooks']['SessionStart']
    if isinstance(entry, dict)
)
if not has_clear:
    settings['hooks']['SessionStart'].append(clear_entry)

# Add compact matcher if not present
has_compact = any(
    entry.get('matcher') == 'compact'
    for entry in settings['hooks']['SessionStart']
    if isinstance(entry, dict)
)
if not has_compact:
    settings['hooks']['SessionStart'].append(compact_entry)

# Remove stale PreToolUse architect hook (legacy tool enforcement, now instruction-based)
if 'PreToolUse' in settings['hooks']:
    settings['hooks']['PreToolUse'] = [
        entry for entry in settings['hooks']['PreToolUse']
        if not (
            isinstance(entry, dict)
            and any('AGENT_ROLE' in h.get('command', '') for h in entry.get('hooks', []) if isinstance(h, dict))
        )
    ]
    # Clean up empty PreToolUse array
    if not settings['hooks']['PreToolUse']:
        del settings['hooks']['PreToolUse']

# Validate and write atomically
result = json.dumps(settings, indent=4)
json.loads(result)  # validate round-trip

tmp_path = settings_path + '.tmp'
with open(tmp_path, 'w') as f:
    f.write(result)
    f.write('\n')
os.replace(tmp_path, settings_path)
" "$SETTINGS_FILE"
}

# Install or update CLAUDE.md at the project root from the purlin template.
# Uses <!-- purlin:start --> / <!-- purlin:end --> markers for safe coexistence
# with user-written content. Idempotent on refresh.
install_claude_md() {
    local CLAUDE_MD="$PROJECT_ROOT/CLAUDE.md"
    local TEMPLATE="$SUBMODULE_DIR/purlin-config-sample/CLAUDE.md.purlin"

    # Guard: skip if template doesn't exist
    if [ ! -f "$TEMPLATE" ]; then
        return 0
    fi

    local TEMPLATE_CONTENT
    TEMPLATE_CONTENT="$(cat "$TEMPLATE")"

    local MARKED_BLOCK
    MARKED_BLOCK="<!-- purlin:start -->
${TEMPLATE_CONTENT}
<!-- purlin:end -->"

    if [ ! -f "$CLAUDE_MD" ]; then
        # No CLAUDE.md exists: create with marked block
        printf '%s\n' "$MARKED_BLOCK" > "$CLAUDE_MD"
    elif grep -q '<!-- purlin:start -->' "$CLAUDE_MD" && grep -q '<!-- purlin:end -->' "$CLAUDE_MD"; then
        # Markers exist: replace content between them
        "$PYTHON_EXE" -c "
import sys

claude_path = sys.argv[1]
marked_block = sys.argv[2]

with open(claude_path, 'r') as f:
    content = f.read()

start_marker = '<!-- purlin:start -->'
end_marker = '<!-- purlin:end -->'

start_idx = content.index(start_marker)
end_idx = content.index(end_marker) + len(end_marker)

new_content = content[:start_idx] + marked_block + content[end_idx:]

with open(claude_path, 'w') as f:
    f.write(new_content)
" "$CLAUDE_MD" "$MARKED_BLOCK"
    else
        # No markers: append marked block
        printf '\n%s\n' "$MARKED_BLOCK" >> "$CLAUDE_MD"
    fi
}

# Install MCP servers from the framework manifest (§2.16).
# Sets MCP_INSTALLED, MCP_SKIPPED, MCP_NOTES, and MCP_ATTEMPTED counters.
install_mcp_servers() {
    MCP_INSTALLED=0
    MCP_SKIPPED=0
    MCP_NOTES=""
    MCP_ATTEMPTED=false

    local MANIFEST="$SUBMODULE_DIR/tools/mcp/manifest.json"

    # CLI guard: skip if claude CLI unavailable
    if ! command -v claude >/dev/null 2>&1; then
        say "  MCP: claude CLI not found, skipping MCP server installation."
        return 0
    fi

    # Manifest guard: skip if manifest missing
    if [ ! -f "$MANIFEST" ]; then
        say "  MCP: manifest not found at $MANIFEST, skipping MCP server installation."
        return 0
    fi

    MCP_ATTEMPTED=true

    # Parse manifest and install servers
    "$PYTHON_EXE" -c "
import json, subprocess, sys, os

manifest_path = sys.argv[1]
quiet = sys.argv[2] == 'true'

with open(manifest_path) as f:
    manifest = json.load(f)

installed = 0
skipped = 0
notes = []
errors = []

# Get list of currently installed MCP servers
try:
    result = subprocess.run(['claude', 'mcp', 'list'], capture_output=True, text=True, timeout=10)
    existing_servers = result.stdout if result.returncode == 0 else ''
except Exception:
    existing_servers = ''

for server in manifest.get('servers', []):
    name = server['name']
    transport = server.get('transport', 'stdio')

    # Check if already installed (name appears in list output)
    if name in existing_servers:
        skipped += 1
        continue

    # Build install command
    cmd = ['claude', 'mcp', 'add']
    if transport == 'http':
        cmd += ['--transport', 'http', name, server['url']]
    else:
        cmd += [name, server['command']] + server.get('args', [])

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        if result.returncode == 0:
            installed += 1
            if server.get('post_install_notes'):
                notes.append(f'  {name}: {server[\"post_install_notes\"]}')
        else:
            errors.append(f'  {name}: install failed ({result.stderr.strip()})')
    except Exception as e:
        errors.append(f'  {name}: install failed ({e})')

# Output results as shell-parseable lines
print(f'MCP_INSTALLED={installed}')
print(f'MCP_SKIPPED={skipped}')
if notes:
    # Escape for shell
    notes_str = '\\n'.join(notes)
    print(f'MCP_NOTES=\"{notes_str}\"')
else:
    print('MCP_NOTES=\"\"')
if errors:
    for err in errors:
        print(f'MCP_ERROR={err}', file=sys.stderr)
" "$MANIFEST" "$QUIET" > /tmp/purlin_mcp_result.sh 2>/tmp/purlin_mcp_errors.txt || true

    # Source results
    if [ -f /tmp/purlin_mcp_result.sh ]; then
        eval "$(cat /tmp/purlin_mcp_result.sh)"
        rm -f /tmp/purlin_mcp_result.sh
    fi

    # Print errors if any
    if [ -f /tmp/purlin_mcp_errors.txt ] && [ -s /tmp/purlin_mcp_errors.txt ]; then
        while IFS= read -r line; do
            say "  $line"
        done < /tmp/purlin_mcp_errors.txt
    fi
    rm -f /tmp/purlin_mcp_errors.txt
}

###############################################################################
# 3. Full Init Mode
###############################################################################
if [ "$MODE" = "full" ]; then

    # 3.1 Override Directory Initialization
    SAMPLE_DIR="$SUBMODULE_DIR/purlin-config-sample"
    if [ ! -d "$SAMPLE_DIR" ]; then
        echo "ERROR: purlin-config-sample/ not found in $SUBMODULE_DIR" >&2
        exit 1
    fi
    cp -R "$SAMPLE_DIR" "$PROJECT_ROOT/.purlin"

    # 3.2 Config Patching (JSON-safe sed per submodule_bootstrap.md §2.10)
    TOOLS_ROOT_VALUE="$SUBMODULE_NAME/tools"
    sed -i.bak "s|\"tools_root\": \"[^\"]*\"|\"tools_root\": \"$TOOLS_ROOT_VALUE\"|" \
        "$PROJECT_ROOT/.purlin/config.json"
    rm -f "$PROJECT_ROOT/.purlin/config.json.bak"

    # Validate JSON after patching
    if ! "$PYTHON_EXE" -c "import json; json.load(open('$PROJECT_ROOT/.purlin/config.json'))"; then
        echo "ERROR: config.json is invalid JSON after patching tools_root." >&2
        exit 1
    fi

    # 3.3 Provider Detection (submodule_bootstrap.md §2.17)
    DETECT_SCRIPT="$SCRIPT_DIR/detect-providers.sh"
    PROVIDER_SUMMARY=""
    if [ -x "$DETECT_SCRIPT" ]; then
        DETECT_OUTPUT=""
        DETECT_OUTPUT="$("$DETECT_SCRIPT" 2>/dev/null)" || true
        if [ -n "$DETECT_OUTPUT" ]; then
            PROVIDER_SUMMARY="$("$PYTHON_EXE" -c "
import json, sys

try:
    detect = json.loads('''$DETECT_OUTPUT''')
except (json.JSONDecodeError, ValueError):
    sys.exit(0)

config_path = '$PROJECT_ROOT/.purlin/config.json'
sample_path = '$SAMPLE_DIR/config.json'

try:
    with open(config_path) as f:
        config = json.load(f)
    with open(sample_path) as f:
        sample = json.load(f)
except (IOError, json.JSONDecodeError):
    sys.exit(0)

sample_providers = sample.get('llm_providers', {})
available = {}
summaries = []
for name, info in detect.get('providers', {}).items():
    if info.get('available', False) and name in sample_providers:
        available[name] = sample_providers[name]
        model_count = len(sample_providers[name].get('models', []))
        summaries.append(f'{name} ({model_count} models)')

if available:
    config['llm_providers'] = available
    with open(config_path, 'w') as f:
        json.dump(config, f, indent=4)

if summaries:
    print('Providers detected and configured: ' + ', '.join(summaries))
else:
    unavail = [n for n, i in detect.get('providers', {}).items() if not i.get('available', False)]
    if unavail:
        print('Providers detected: none available (' + ', '.join(unavail) + ' unavailable)')
" 2>/dev/null)" || true
        fi
    fi

    # 3.4 Upstream SHA Recording
    CURRENT_SHA="$(record_upstream_sha)"

    # 3.5 Launcher Script Generation
    generate_purlin_launcher "$PROJECT_ROOT/pl-run.sh"

    # 3.6 Command File Distribution
    copy_command_files

    # 3.6b Agent File Distribution (project_init.md §2.3 step 6b)
    copy_agent_files

    # 3.7 Features Directory
    if [ ! -d "$PROJECT_ROOT/features" ]; then
        mkdir "$PROJECT_ROOT/features"
    fi

    # 3.8 Gitignore Handling (project_init.md §2.3 step 8)
    GITIGNORE="$PROJECT_ROOT/.gitignore"
    GITIGNORE_TEMPLATE="$SUBMODULE_DIR/purlin-config-sample/gitignore.purlin"

    # Warn if .purlin is gitignored
    if [ -f "$GITIGNORE" ] && grep -qE '^\.purlin/?$' "$GITIGNORE"; then
        say ""
        say "WARNING: .purlin appears in .gitignore."
        say "  .purlin/ contains project-specific overrides and SHOULD be tracked (committed)."
        say "  Remove '.purlin' from .gitignore if it was added by mistake."
    fi

    # Read patterns from gitignore.purlin template
    if [ -f "$GITIGNORE_TEMPLATE" ]; then
        if [ ! -f "$GITIGNORE" ]; then
            cp "$GITIGNORE_TEMPLATE" "$GITIGNORE"
        else
            ADDED=0
            while IFS= read -r LINE || [ -n "$LINE" ]; do
                # Skip blank lines and comments
                if [ -z "$LINE" ] || [[ "$LINE" == \#* ]]; then
                    continue
                fi
                if ! grep -qF "$LINE" "$GITIGNORE"; then
                    if [ "$ADDED" -eq 0 ]; then
                        echo "" >> "$GITIGNORE"
                        echo "# Added by Purlin init" >> "$GITIGNORE"
                        ADDED=1
                    fi
                    echo "$LINE" >> "$GITIGNORE"
                fi
            done < "$GITIGNORE_TEMPLATE"
        fi
    fi

    # 3.9 Shim Generation
    generate_shim

    # 3.10 CDD Convenience Symlinks
    create_cdd_symlinks

    # 3.11 Python Environment Suggestion (submodule_bootstrap.md §2.16)
    VENV_MSG=""
    if [ ! -d "$PROJECT_ROOT/.venv" ]; then
        VENV_MSG="(Optional) python3 -m venv .venv && .venv/bin/pip install -r $SUBMODULE_NAME/requirements-optional.txt"
    fi

    # 3.12 Claude Code Hook Installation (project_init.md §2.15)
    install_session_hook

    # 3.13 CLAUDE.md Installation (context_recovery_hook.md §2.3)
    install_claude_md

    # 3.14 MCP Server Installation (project_init.md §2.16)
    install_mcp_servers

    # 3.15 Post-Init Staging (project_init.md §2.3 step 14)
    # Stage exactly the files created by init — never git add -A or git add .
    git -C "$PROJECT_ROOT" add .purlin/ 2>/dev/null || true
    git -C "$PROJECT_ROOT" add pl-run-architect.sh pl-run-builder.sh pl-run-qa.sh pl-run-pm.sh pl-run.sh 2>/dev/null || true
    git -C "$PROJECT_ROOT" add .claude/commands/ 2>/dev/null || true
    git -C "$PROJECT_ROOT" add .claude/agents/ 2>/dev/null || true
    git -C "$PROJECT_ROOT" add .claude/settings.json 2>/dev/null || true
    git -C "$PROJECT_ROOT" add .gitignore 2>/dev/null || true
    git -C "$PROJECT_ROOT" add pl-init.sh 2>/dev/null || true
    git -C "$PROJECT_ROOT" add pl-cdd-start.sh pl-cdd-stop.sh 2>/dev/null || true
    git -C "$PROJECT_ROOT" add CLAUDE.md 2>/dev/null || true

    # 3.16 Summary Output — "What's Next" Narrative (init_preflight_checks.md §2.4)
    say ""
    say "════════════════════════════════════════════════════════════════"
    say "  Purlin initialized. Files staged."
    say "════════════════════════════════════════════════════════════════"
    say ""
    say "  What's Next"
    say "  ───────────"
    say ""
    say "  1. Commit the scaffolding:"
    say "     git commit -m \"init purlin\""
    say ""
    say "  2. Start your first agent:"
    say "     • Have designs?      → ./pl-run-pm.sh"
    say "       The PM reads your Figma designs and writes feature specs."
    say "     • Have requirements? → ./pl-run-architect.sh"
    say "       The Architect turns requirements into feature specs."
    say ""
    say "  3. Build from specs:"
    say "     The Builder reads your specs and writes the code and tests"
    say "     to match them. → ./pl-run-builder.sh"
    say ""
    say "  4. Watch progress:"
    say "     ./pl-cdd-start.sh  — opens the CDD status dashboard"
    say ""
    if [ -n "$PROVIDER_SUMMARY" ]; then
        say "  $PROVIDER_SUMMARY"
        say ""
    fi
    if [ "$CMD_COPIED" -gt 0 ] || [ "$CMD_SKIPPED" -gt 0 ]; then
        say "  Commands: $CMD_COPIED copied"
        [ "$CMD_SKIPPED" -gt 0 ] && say ", $CMD_SKIPPED skipped (locally modified)"
    fi
    if [ "$MCP_ATTEMPTED" = true ]; then
        say "  MCP servers: $MCP_INSTALLED installed, $MCP_SKIPPED skipped"
        if [ -n "$MCP_NOTES" ]; then
            say "$MCP_NOTES"
        fi
        if [ "$MCP_INSTALLED" -gt 0 ]; then
            say "  Restart Claude Code to load MCP servers."
        fi
    fi
    if [ -n "$VENV_MSG" ]; then
        say ""
        say "  $VENV_MSG"
    fi
    say ""

###############################################################################
# 4. Refresh Mode
###############################################################################
else

    # 4.1 Command File Refresh
    copy_command_files

    # 4.1b Agent File Refresh (project_init.md §2.4 step 1b)
    copy_agent_files

    # 4.2 Upstream SHA Update
    CURRENT_SHA="$(record_upstream_sha)"

    # 4.3 Shim Self-Update (regenerate if SHA changed)
    SHIM_FILE="$PROJECT_ROOT/pl-init.sh"
    NEEDS_SHIM_UPDATE=false
    if [ ! -f "$SHIM_FILE" ]; then
        NEEDS_SHIM_UPDATE=true
    elif ! grep -q "$CURRENT_SHA" "$SHIM_FILE"; then
        NEEDS_SHIM_UPDATE=true
    fi
    SHIM_NOTE=""
    if [ "$NEEDS_SHIM_UPDATE" = true ]; then
        generate_shim
        SHIM_NOTE=" Shim updated."
    fi

    # 4.4 CDD Symlink Repair
    SYMLINK_NOTE=""
    REPAIRED=0
    if [ ! -L "$PROJECT_ROOT/pl-cdd-start.sh" ]; then
        REPAIRED=$((REPAIRED + 1))
    fi
    if [ ! -L "$PROJECT_ROOT/pl-cdd-stop.sh" ]; then
        REPAIRED=$((REPAIRED + 1))
    fi
    create_cdd_symlinks
    if [ "$REPAIRED" -gt 0 ]; then
        SYMLINK_NOTE=" $REPAIRED CDD symlink(s) repaired."
    fi

    # 4.5 Launcher Regeneration (always regenerate on refresh)
    generate_purlin_launcher "$PROJECT_ROOT/pl-run.sh"
    # Remove stale launchers from previous naming conventions
    for stale in run_architect.sh run_builder.sh run_qa.sh; do
        rm -f "$PROJECT_ROOT/$stale"
    done
    # Stale worktrees from previous sessions
    if [ -d "$PROJECT_ROOT/.purlin/worktrees" ]; then
        for wt in "$PROJECT_ROOT"/.purlin/worktrees/*/; do
            if [ -d "$wt" ]; then
                # Check if worktree is still valid
                git worktree list 2>/dev/null | grep -q "$(basename "$wt")" || rm -rf "$wt"
            fi
        done
    fi

    # 4.6 Claude Code Hook Installation (project_init.md §2.15)
    install_session_hook

    # 4.7 CLAUDE.md Installation (context_recovery_hook.md §2.3)
    install_claude_md
    git -C "$PROJECT_ROOT" add CLAUDE.md 2>/dev/null || true

    # 4.8 Gitignore Pattern Sync (project_init.md §2.4 step 7)
    GITIGNORE="$PROJECT_ROOT/.gitignore"
    GITIGNORE_TEMPLATE="$SUBMODULE_DIR/purlin-config-sample/gitignore.purlin"

    if [ -f "$GITIGNORE_TEMPLATE" ] && [ -f "$GITIGNORE" ]; then
        GITIGNORE_ADDED=0
        while IFS= read -r LINE || [ -n "$LINE" ]; do
            # Skip blank lines and comments
            if [ -z "$LINE" ] || [[ "$LINE" == \#* ]]; then
                continue
            fi
            if ! grep -qF "$LINE" "$GITIGNORE"; then
                if [ "$GITIGNORE_ADDED" -eq 0 ]; then
                    echo "" >> "$GITIGNORE"
                    echo "# Added by Purlin refresh" >> "$GITIGNORE"
                    GITIGNORE_ADDED=1
                fi
                echo "$LINE" >> "$GITIGNORE"
            fi
        done < "$GITIGNORE_TEMPLATE"
    elif [ -f "$GITIGNORE_TEMPLATE" ] && [ ! -f "$GITIGNORE" ]; then
        cp "$GITIGNORE_TEMPLATE" "$GITIGNORE"
    fi

    # 4.9 MCP Server Installation (project_init.md §2.16)
    install_mcp_servers

    # 4.10 Refresh Summary (init_preflight_checks.md §2.4 — abbreviated)
    MCP_NOTE=""
    if [ "$MCP_ATTEMPTED" = true ] && [ "$MCP_INSTALLED" -gt 0 ]; then
        MCP_NOTE=" MCP: $MCP_INSTALLED installed."
    fi
    say "Purlin refreshed. ($CMD_COPIED commands updated, $CMD_SKIPPED skipped)${SHIM_NOTE}${SYMLINK_NOTE}${MCP_NOTE}"
    if [ "$MCP_ATTEMPTED" = true ] && [ -n "$MCP_NOTES" ]; then
        say "$MCP_NOTES"
    fi
    if [ "$MCP_ATTEMPTED" = true ] && [ "$MCP_INSTALLED" -gt 0 ]; then
        say "Restart Claude Code to load MCP servers."
    fi
    say "Dashboard: ./pl-cdd-start.sh"
fi
