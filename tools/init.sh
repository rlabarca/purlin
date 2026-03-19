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
PREFLIGHT_ONLY=false

for arg in "$@"; do
    case "$arg" in
        --quiet) QUIET=true ;;
        --preflight-only) PREFLIGHT_ONLY=true ;;
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

# --preflight-only: exit after checks (used by /pl-update-purlin §2.6)
if [ "$PREFLIGHT_ONLY" = true ]; then
    exit 0
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

# Generate a launcher script.
# Usage: generate_launcher <output_file> <role> <instruction_file> <overrides_file> <session_message>
generate_launcher() {
    local OUTPUT_FILE="$1"
    local ROLE="$2"
    local INSTRUCTION_FILE="$3"
    local OVERRIDES_FILE="$4"
    local SESSION_MSG="$5"
    local FRAMEWORK_VAR="\$SCRIPT_DIR/$SUBMODULE_NAME"
    local DISPLAY_NAME
    case "$ROLE" in
        architect) DISPLAY_NAME="Architect" ;;
        builder) DISPLAY_NAME="Builder" ;;
        qa) DISPLAY_NAME="QA" ;;
        pm) DISPLAY_NAME="PM" ;;
        *) DISPLAY_NAME="$ROLE" ;;
    esac

    # Part 1: Shebang, SCRIPT_DIR, PURLIN_PROJECT_ROOT (literal)
    cat > "$OUTPUT_FILE" << 'LAUNCHER_EOF'
#!/bin/bash
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
export PURLIN_PROJECT_ROOT="$SCRIPT_DIR"
LAUNCHER_EOF

    # Part 2: CORE_DIR with submodule path (expanded)
    cat >> "$OUTPUT_FILE" << LAUNCHER_EOF
CORE_DIR="$FRAMEWORK_VAR"
LAUNCHER_EOF

    # Part 3: Prompt assembly (literal)
    cat >> "$OUTPUT_FILE" << LAUNCHER_EOF

# Fall back to local instructions/ if not a submodule consumer
if [ ! -d "\$CORE_DIR/instructions" ]; then
    CORE_DIR="\$SCRIPT_DIR"
fi

# Source terminal identity helper (no-op if missing)
if [ -f "\$CORE_DIR/tools/terminal/identity.sh" ]; then
    source "\$CORE_DIR/tools/terminal/identity.sh"
fi

PROMPT_FILE=\$(mktemp)
trap "rm -f '\$PROMPT_FILE'; type clear_agent_identity >/dev/null 2>&1 && clear_agent_identity" EXIT

cat "\$CORE_DIR/instructions/HOW_WE_WORK_BASE.md" > "\$PROMPT_FILE"
printf "\n\n" >> "\$PROMPT_FILE"
cat "\$CORE_DIR/instructions/${INSTRUCTION_FILE}" >> "\$PROMPT_FILE"

if [ -f "\$SCRIPT_DIR/.purlin/HOW_WE_WORK_OVERRIDES.md" ]; then
    printf "\n\n" >> "\$PROMPT_FILE"
    cat "\$SCRIPT_DIR/.purlin/HOW_WE_WORK_OVERRIDES.md" >> "\$PROMPT_FILE"
fi

if [ -f "\$SCRIPT_DIR/.purlin/${OVERRIDES_FILE}" ]; then
    printf "\n\n" >> "\$PROMPT_FILE"
    cat "\$SCRIPT_DIR/.purlin/${OVERRIDES_FILE}" >> "\$PROMPT_FILE"
fi
LAUNCHER_EOF

    # Part 4: Config reading via resolver (literal)
    cat >> "$OUTPUT_FILE" << 'LAUNCHER_EOF'

# --- Read agent config via resolver ---
LAUNCHER_EOF

    # Part 4b: Role name and resolver path (expanded)
    cat >> "$OUTPUT_FILE" << LAUNCHER_EOF
AGENT_ROLE="${ROLE}"
export AGENT_ROLE
RESOLVER="\$CORE_DIR/tools/config/resolve_config.py"
LAUNCHER_EOF

    # Part 4c: Config parsing via resolve_config.py (literal)
    cat >> "$OUTPUT_FILE" << 'LAUNCHER_EOF'

AGENT_MODEL=""
AGENT_EFFORT=""
AGENT_BYPASS="false"
AGENT_FIND_WORK="true"
AGENT_AUTO_START="false"

if [ -f "$RESOLVER" ]; then
    eval "$(PURLIN_PROJECT_ROOT="$SCRIPT_DIR" python3 "$RESOLVER" "$AGENT_ROLE" 2>/dev/null)"
fi
LAUNCHER_EOF

    # Part 4c2: Role-specific defaults when config section is absent
    if [ "$ROLE" = "pm" ]; then
        cat >> "$OUTPUT_FILE" << 'LAUNCHER_EOF'

# PM-specific defaults when agents.pm is absent from config
# (resolver returns empty model/effort when role section is missing)
if [ -z "$AGENT_MODEL" ] && [ -z "$AGENT_EFFORT" ]; then
    AGENT_MODEL="claude-sonnet-4-6"
    AGENT_EFFORT="medium"
    AGENT_BYPASS="true"
fi
LAUNCHER_EOF
    fi

    # Part 4d0: Validate startup controls (literal)
    cat >> "$OUTPUT_FILE" << 'LAUNCHER_EOF'

# --- Validate startup controls ---
if [ "$AGENT_FIND_WORK" = "false" ] && [ "$AGENT_AUTO_START" = "true" ]; then
    echo "Error: Invalid startup controls for $AGENT_ROLE: find_work=false with auto_start=true is not a valid combination. Set auto_start to false or enable find_work." >&2
    exit 1
fi

# --- Claude dispatch ---
CLI_ARGS=()
[ -n "$AGENT_MODEL" ] && CLI_ARGS+=(--model "$AGENT_MODEL")
[ -n "$AGENT_EFFORT" ] && CLI_ARGS+=(--effort "$AGENT_EFFORT")
LAUNCHER_EOF

    # Part 4d: Role-specific permission handling (expanded for role)
    if [ "$ROLE" = "builder" ]; then
        cat >> "$OUTPUT_FILE" << 'LAUNCHER_EOF'
if [ "$AGENT_BYPASS" = "true" ]; then
    CLI_ARGS+=(--dangerously-skip-permissions)
fi
LAUNCHER_EOF
    elif [ "$ROLE" = "qa" ]; then
        cat >> "$OUTPUT_FILE" << 'LAUNCHER_EOF'
if [ "$AGENT_BYPASS" = "true" ]; then
    CLI_ARGS+=(--dangerously-skip-permissions)
else
    CLI_ARGS+=(--allowedTools "Bash(git *)" "Bash(bash *)" "Bash(python3 *)" "Read" "Glob" "Grep" "Write" "Edit")
fi
LAUNCHER_EOF
    else
        # architect (default)
        cat >> "$OUTPUT_FILE" << 'LAUNCHER_EOF'
if [ "$AGENT_BYPASS" = "true" ]; then
    CLI_ARGS+=(--dangerously-skip-permissions)
else
    CLI_ARGS+=(--allowedTools "Bash(git *)" "Bash(bash *)" "Bash(python3 *)" "Read" "Glob" "Grep")
fi
LAUNCHER_EOF
    fi

    # Part 4e: Set terminal identity and invoke Claude (expanded for session msg + display name)
    cat >> "$OUTPUT_FILE" << LAUNCHER_EOF
type set_agent_identity >/dev/null 2>&1 && set_agent_identity "${DISPLAY_NAME}"
claude "\${CLI_ARGS[@]}" --append-system-prompt-file "\$PROMPT_FILE" "${SESSION_MSG}"
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

hook_entry = {
    'matcher': 'clear',
    'hooks': [
        {
            'type': 'command',
            'command': \"echo 'IMPORTANT: Context was cleared. Run /pl-resume immediately to restore session context.'\"
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

# Check if a 'clear' matcher already exists
has_clear = any(
    entry.get('matcher') == 'clear'
    for entry in settings['hooks']['SessionStart']
    if isinstance(entry, dict)
)

if not has_clear:
    settings['hooks']['SessionStart'].append(hook_entry)

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
    generate_launcher "$PROJECT_ROOT/pl-run-architect.sh" "architect" "ARCHITECT_BASE.md" "ARCHITECT_OVERRIDES.md" "Begin Architect session."
    generate_launcher "$PROJECT_ROOT/pl-run-builder.sh"  "builder"   "BUILDER_BASE.md"    "BUILDER_OVERRIDES.md"  "Begin Builder session."
    generate_launcher "$PROJECT_ROOT/pl-run-qa.sh"       "qa"        "QA_BASE.md"         "QA_OVERRIDES.md"       "Begin QA verification session."
    generate_launcher "$PROJECT_ROOT/pl-run-pm.sh"       "pm"        "PM_BASE.md"         "PM_OVERRIDES.md"       "Begin PM session."

    # 3.6 Command File Distribution
    copy_command_files

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

    # 3.13 MCP Server Installation (project_init.md §2.16)
    install_mcp_servers

    # 3.14 Post-Init Staging (project_init.md §2.3 step 14)
    # Stage exactly the files created by init — never git add -A or git add .
    git -C "$PROJECT_ROOT" add .purlin/ 2>/dev/null || true
    git -C "$PROJECT_ROOT" add pl-run-architect.sh pl-run-builder.sh pl-run-qa.sh pl-run-pm.sh 2>/dev/null || true
    git -C "$PROJECT_ROOT" add .claude/commands/ 2>/dev/null || true
    git -C "$PROJECT_ROOT" add .claude/settings.json 2>/dev/null || true
    git -C "$PROJECT_ROOT" add .gitignore 2>/dev/null || true
    git -C "$PROJECT_ROOT" add pl-init.sh 2>/dev/null || true
    git -C "$PROJECT_ROOT" add pl-cdd-start.sh pl-cdd-stop.sh 2>/dev/null || true

    # 3.15 Summary Output — "What's Next" Narrative (init_preflight_checks.md §2.4)
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
    generate_launcher "$PROJECT_ROOT/pl-run-architect.sh" "architect" "ARCHITECT_BASE.md" "ARCHITECT_OVERRIDES.md" "Begin Architect session."
    generate_launcher "$PROJECT_ROOT/pl-run-builder.sh"  "builder"   "BUILDER_BASE.md"    "BUILDER_OVERRIDES.md"  "Begin Builder session."
    generate_launcher "$PROJECT_ROOT/pl-run-qa.sh"       "qa"        "QA_BASE.md"         "QA_OVERRIDES.md"       "Begin QA verification session."
    generate_launcher "$PROJECT_ROOT/pl-run-pm.sh"       "pm"        "PM_BASE.md"         "PM_OVERRIDES.md"       "Begin PM session."
    # Remove stale launchers from previous naming conventions
    for stale in run_architect.sh run_builder.sh run_qa.sh; do
        rm -f "$PROJECT_ROOT/$stale"
    done

    # 4.6 Claude Code Hook Installation (project_init.md §2.15)
    install_session_hook

    # 4.7 Gitignore Pattern Sync (project_init.md §2.4 step 7)
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

    # 4.8 MCP Server Installation (project_init.md §2.16)
    install_mcp_servers

    # 4.9 Refresh Summary (init_preflight_checks.md §2.4 — abbreviated)
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
