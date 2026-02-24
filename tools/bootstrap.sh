#!/bin/bash
# bootstrap.sh — Initialize a consumer project for the Purlin submodule.
# Usage: Run from any directory.  The script resolves paths from its own location.
set -euo pipefail

###############################################################################
# 1. Path Resolution
###############################################################################
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SUBMODULE_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
SUBMODULE_NAME="$(basename "$SUBMODULE_DIR")"
PROJECT_ROOT="$(cd "$SUBMODULE_DIR/.." && pwd)"

# Source shared Python resolver (python_environment.md §2.2)
export PURLIN_PROJECT_ROOT="$PROJECT_ROOT"
source "$SCRIPT_DIR/resolve_python.sh"

###############################################################################
# 2. Guard: Prevent Re-Initialization
###############################################################################
if [ -d "$PROJECT_ROOT/.purlin" ]; then
    echo "ERROR: .purlin/ already exists at $PROJECT_ROOT"
    echo "If you want to re-initialize, remove it first:  rm -rf $PROJECT_ROOT/.purlin"
    exit 1
fi

###############################################################################
# 3. Override Directory Initialization
###############################################################################
SAMPLE_DIR="$SUBMODULE_DIR/purlin-config-sample"
if [ ! -d "$SAMPLE_DIR" ]; then
    echo "ERROR: purlin-config-sample/ not found in $SUBMODULE_DIR"
    exit 1
fi

echo "Copying purlin-config-sample/ -> .purlin/ ..."
cp -R "$SAMPLE_DIR" "$PROJECT_ROOT/.purlin"

# Patch tools_root in the copied config.json (Section 2.10: JSON-safe sed)
TOOLS_ROOT_VALUE="$SUBMODULE_NAME/tools"
sed -i.bak "s|\"tools_root\": \"[^\"]*\"|\"tools_root\": \"$TOOLS_ROOT_VALUE\"|" \
    "$PROJECT_ROOT/.purlin/config.json"
rm -f "$PROJECT_ROOT/.purlin/config.json.bak"

# Validate JSON after patching (Section 2.10)
if ! "$PYTHON_EXE" -c "import json; json.load(open('$PROJECT_ROOT/.purlin/config.json'))"; then
    echo "ERROR: config.json is invalid JSON after patching tools_root."
    echo "  File: $PROJECT_ROOT/.purlin/config.json"
    exit 1
fi

###############################################################################
# 3b. Provider Detection Integration (Section 2.17)
###############################################################################
DETECT_SCRIPT="$SCRIPT_DIR/detect-providers.sh"
if [ -x "$DETECT_SCRIPT" ]; then
    DETECT_OUTPUT=""
    DETECT_OUTPUT="$("$DETECT_SCRIPT" 2>/dev/null)" || true
    if [ -n "$DETECT_OUTPUT" ]; then
        # Merge available providers into installed config.json
        "$PYTHON_EXE" -c "
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

# Merge available providers from sample definitions
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

# Report
if summaries:
    print('Providers detected and configured: ' + ', '.join(summaries))
else:
    unavail = [n for n, i in detect.get('providers', {}).items() if not i.get('available', False)]
    if unavail:
        print('Providers detected: none available (' + ', '.join(unavail) + ' unavailable)')
" 2>/dev/null || true
    fi
fi

###############################################################################
# 4. Upstream SHA Marker
###############################################################################
CURRENT_SHA="$(git -C "$SUBMODULE_DIR" rev-parse HEAD)"
echo "$CURRENT_SHA" > "$PROJECT_ROOT/.purlin/.upstream_sha"

###############################################################################
# 5. Launcher Script Generation
###############################################################################
FRAMEWORK_VAR="\$SCRIPT_DIR/$SUBMODULE_NAME"

# Helper: generate a config-driven launcher script.
# Usage: generate_launcher <output_file> <role> <instruction_file> <overrides_file> <session_message>
generate_launcher() {
    local OUTPUT_FILE="$1"
    local ROLE="$2"
    local INSTRUCTION_FILE="$3"
    local OVERRIDES_FILE="$4"
    local SESSION_MSG="$5"

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

PROMPT_FILE=\$(mktemp)
trap "rm -f '\$PROMPT_FILE'" EXIT

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

    # Part 4: Config reading (literal)
    cat >> "$OUTPUT_FILE" << 'LAUNCHER_EOF'

# --- Read agent config from config.json ---
CONFIG_FILE="$SCRIPT_DIR/.purlin/config.json"
LAUNCHER_EOF

    # Part 4b: Role name (expanded)
    cat >> "$OUTPUT_FILE" << LAUNCHER_EOF
AGENT_ROLE="${ROLE}"
LAUNCHER_EOF

    # Part 4c: Config parsing (literal)
    cat >> "$OUTPUT_FILE" << 'LAUNCHER_EOF'

AGENT_MODEL=""
AGENT_EFFORT=""
AGENT_BYPASS="false"
AGENT_STARTUP="true"
AGENT_RECOMMEND="true"

if [ -f "$CONFIG_FILE" ]; then
    eval "$(python3 -c "
import json
try:
    c = json.load(open('$CONFIG_FILE'))
    a = c.get('agents', {}).get('$AGENT_ROLE', {})
    print(f'AGENT_MODEL=\"{a.get(\"model\", \"\")}\"')
    print(f'AGENT_EFFORT=\"{a.get(\"effort\", \"\")}\"')
    bp = 'true' if a.get('bypass_permissions', False) else 'false'
    print(f'AGENT_BYPASS=\"{bp}\"')
    ss = 'true' if a.get('startup_sequence', True) else 'false'
    print(f'AGENT_STARTUP=\"{ss}\"')
    rn = 'true' if a.get('recommend_next_actions', True) else 'false'
    print(f'AGENT_RECOMMEND=\"{rn}\"')
except: pass
" 2>/dev/null)"
fi

# --- Validate startup controls ---
if [ "$AGENT_STARTUP" = "false" ] && [ "$AGENT_RECOMMEND" = "true" ]; then
    echo "Error: Invalid startup controls for $AGENT_ROLE: startup_sequence=false with recommend_next_actions=true is not a valid combination. Set recommend_next_actions to false or enable startup_sequence." >&2
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

    # Part 4e: Claude invocation (expanded for session msg)
    cat >> "$OUTPUT_FILE" << LAUNCHER_EOF
claude "\${CLI_ARGS[@]}" --append-system-prompt-file "\$PROMPT_FILE" "${SESSION_MSG}"
LAUNCHER_EOF

    chmod +x "$OUTPUT_FILE"
}

generate_launcher "$PROJECT_ROOT/run_architect.sh" "architect" "ARCHITECT_BASE.md" "ARCHITECT_OVERRIDES.md" "Begin Architect session."
generate_launcher "$PROJECT_ROOT/run_builder.sh"  "builder"   "BUILDER_BASE.md"    "BUILDER_OVERRIDES.md"  "Begin Builder session."
generate_launcher "$PROJECT_ROOT/run_qa.sh"       "qa"        "QA_BASE.md"         "QA_OVERRIDES.md"       "Begin QA verification session."

###############################################################################
# 5b. Command File Distribution (Section 2.18)
###############################################################################
COMMANDS_SRC="$SUBMODULE_DIR/.claude/commands"
COMMANDS_DST="$PROJECT_ROOT/.claude/commands"

CMD_COPIED=0
CMD_SKIPPED=0

if [ -d "$COMMANDS_SRC" ]; then
    mkdir -p "$COMMANDS_DST"
    for src_file in "$COMMANDS_SRC"/*.md; do
        [ -f "$src_file" ] || continue
        fname="$(basename "$src_file")"
        # Section 2.18: pl-edit-base.md MUST NEVER be copied to consumer projects
        if [ "$fname" = "pl-edit-base.md" ]; then
            continue
        fi
        dst_file="$COMMANDS_DST/$fname"
        if [ -f "$dst_file" ] && [ "$dst_file" -nt "$src_file" ]; then
            CMD_SKIPPED=$((CMD_SKIPPED + 1))
        else
            cp "$src_file" "$dst_file"
            CMD_COPIED=$((CMD_COPIED + 1))
        fi
    done
fi

###############################################################################
# 6. Project Scaffolding
###############################################################################
if [ ! -d "$PROJECT_ROOT/features" ]; then
    mkdir "$PROJECT_ROOT/features"
    echo "Created features/"
fi

###############################################################################
# 7. Gitignore Handling
###############################################################################
GITIGNORE="$PROJECT_ROOT/.gitignore"

# Warn if .purlin is gitignored
if [ -f "$GITIGNORE" ] && grep -q '\.purlin' "$GITIGNORE"; then
    echo ""
    echo "WARNING: .purlin appears in .gitignore."
    echo "  .purlin/ contains project-specific overrides and SHOULD be tracked (committed)."
    echo "  Remove '.purlin' from .gitignore if it was added by mistake."
fi

# Recommended ignores
RECOMMENDED_IGNORES=(
    "# OS & Editors"
    ".DS_Store"
    ".vscode/"
    ".idea/"
    ""
    "# Python"
    "__pycache__/"
    "*.py[cod]"
    ".venv/"
    "env/"
    "venv/"
    ""
    "# Purlin Tool Logs & Artifacts"
    "*.log"
    "*.pid"
    ".purlin/runtime/"
    ".purlin/cache/"
)

if [ ! -f "$GITIGNORE" ]; then
    # Create .gitignore with recommended ignores
    printf "%s\n" "${RECOMMENDED_IGNORES[@]}" > "$GITIGNORE"
    echo "Created .gitignore with recommended ignores."
else
    # Append missing recommended ignores
    ADDED=0
    for LINE in "${RECOMMENDED_IGNORES[@]}"; do
        # Skip empty lines and comments for the uniqueness check
        if [ -z "$LINE" ] || [[ "$LINE" == \#* ]]; then
            continue
        fi
        if ! grep -qF "$LINE" "$GITIGNORE"; then
            if [ "$ADDED" -eq 0 ]; then
                echo "" >> "$GITIGNORE"
                echo "# Added by Purlin bootstrap" >> "$GITIGNORE"
                ADDED=1
            fi
            echo "$LINE" >> "$GITIGNORE"
        fi
    done
    if [ "$ADDED" -eq 1 ]; then
        echo "Appended missing recommended ignores to .gitignore."
    fi
fi

###############################################################################
# 8. Summary
###############################################################################
echo ""
echo "=== Bootstrap Complete ==="
echo ""
echo "Created:"
echo "  .purlin/              (override directory)"
echo "  .purlin/config.json   (tools_root: $TOOLS_ROOT_VALUE)"
echo "  .purlin/.upstream_sha (submodule SHA: ${CURRENT_SHA:0:12}...)"
echo "  run_architect.sh              (launcher)"
echo "  run_builder.sh               (launcher)"
echo "  run_qa.sh                    (launcher)"
[ "$CMD_COPIED" -gt 0 ] && echo "  .claude/commands/             ($CMD_COPIED pl-* command file(s))"
[ "$CMD_SKIPPED" -gt 0 ] && echo "  .claude/commands/             ($CMD_SKIPPED file(s) skipped — consumer version newer)"
[ ! -d "$PROJECT_ROOT/features" ] || echo "  features/                     (feature specs directory)"
echo ""
echo "Next steps:"
echo "  1. Review and customize .purlin/ override files."
echo "  2. Run ./run_architect.sh to start the Architect agent."
echo "  3. Run ./run_builder.sh to start the Builder agent."
echo "  4. Run ./run_qa.sh to start the QA agent."
echo ""

###############################################################################
# 9. Python Environment Suggestion (Section 2.16)
###############################################################################
if [ ! -d "$PROJECT_ROOT/.venv" ]; then
    echo "(Optional) Set up a Python virtual environment for optional dependencies:"
    echo "  python3 -m venv .venv"
    echo "  .venv/bin/pip install -r $SUBMODULE_NAME/requirements-optional.txt"
    echo ""
fi
