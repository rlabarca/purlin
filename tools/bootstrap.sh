#!/bin/bash
# bootstrap.sh — Initialize a consumer project for the agentic-dev-core submodule.
# Usage: Run from any directory.  The script resolves paths from its own location.
set -euo pipefail

###############################################################################
# 1. Path Resolution
###############################################################################
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SUBMODULE_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
SUBMODULE_NAME="$(basename "$SUBMODULE_DIR")"
PROJECT_ROOT="$(cd "$SUBMODULE_DIR/.." && pwd)"

###############################################################################
# 2. Guard: Prevent Re-Initialization
###############################################################################
if [ -d "$PROJECT_ROOT/.agentic_devops" ]; then
    echo "ERROR: .agentic_devops/ already exists at $PROJECT_ROOT"
    echo "If you want to re-initialize, remove it first:  rm -rf $PROJECT_ROOT/.agentic_devops"
    exit 1
fi

###############################################################################
# 3. Override Directory Initialization
###############################################################################
SAMPLE_DIR="$SUBMODULE_DIR/agentic_devops.sample"
if [ ! -d "$SAMPLE_DIR" ]; then
    echo "ERROR: agentic_devops.sample/ not found in $SUBMODULE_DIR"
    exit 1
fi

echo "Copying agentic_devops.sample/ -> .agentic_devops/ ..."
cp -R "$SAMPLE_DIR" "$PROJECT_ROOT/.agentic_devops"

# Patch tools_root in the copied config.json
TOOLS_ROOT_VALUE="$SUBMODULE_NAME/tools"
sed -i.bak "s|\"tools_root\":.*|\"tools_root\": \"$TOOLS_ROOT_VALUE\"|" \
    "$PROJECT_ROOT/.agentic_devops/config.json"
rm -f "$PROJECT_ROOT/.agentic_devops/config.json.bak"

###############################################################################
# 4. Upstream SHA Marker
###############################################################################
CURRENT_SHA="$(git -C "$SUBMODULE_DIR" rev-parse HEAD)"
echo "$CURRENT_SHA" > "$PROJECT_ROOT/.agentic_devops/.upstream_sha"

###############################################################################
# 5. Launcher Script Generation
###############################################################################
FRAMEWORK_VAR="\$SCRIPT_DIR/$SUBMODULE_NAME"

# --- Architect Launcher ---
cat > "$PROJECT_ROOT/run_claude_architect.sh" << 'LAUNCHER_EOF'
#!/bin/bash
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LAUNCHER_EOF

cat >> "$PROJECT_ROOT/run_claude_architect.sh" << LAUNCHER_EOF
CORE_DIR="$FRAMEWORK_VAR"
LAUNCHER_EOF

cat >> "$PROJECT_ROOT/run_claude_architect.sh" << 'LAUNCHER_EOF'

# Fall back to local instructions/ if not a submodule consumer
if [ ! -d "$CORE_DIR/instructions" ]; then
    CORE_DIR="$SCRIPT_DIR"
fi

PROMPT_FILE=$(mktemp)
trap "rm -f '$PROMPT_FILE'" EXIT

cat "$CORE_DIR/instructions/HOW_WE_WORK_BASE.md" > "$PROMPT_FILE"
printf "\n\n" >> "$PROMPT_FILE"
cat "$CORE_DIR/instructions/ARCHITECT_BASE.md" >> "$PROMPT_FILE"

if [ -f "$SCRIPT_DIR/.agentic_devops/HOW_WE_WORK_OVERRIDES.md" ]; then
    printf "\n\n" >> "$PROMPT_FILE"
    cat "$SCRIPT_DIR/.agentic_devops/HOW_WE_WORK_OVERRIDES.md" >> "$PROMPT_FILE"
fi

if [ -f "$SCRIPT_DIR/.agentic_devops/ARCHITECT_OVERRIDES.md" ]; then
    printf "\n\n" >> "$PROMPT_FILE"
    cat "$SCRIPT_DIR/.agentic_devops/ARCHITECT_OVERRIDES.md" >> "$PROMPT_FILE"
fi

claude --append-system-prompt-file "$PROMPT_FILE"
LAUNCHER_EOF

chmod +x "$PROJECT_ROOT/run_claude_architect.sh"

# --- Builder Launcher ---
cat > "$PROJECT_ROOT/run_claude_builder.sh" << 'LAUNCHER_EOF'
#!/bin/bash
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LAUNCHER_EOF

cat >> "$PROJECT_ROOT/run_claude_builder.sh" << LAUNCHER_EOF
CORE_DIR="$FRAMEWORK_VAR"
LAUNCHER_EOF

cat >> "$PROJECT_ROOT/run_claude_builder.sh" << 'LAUNCHER_EOF'

# Fall back to local instructions/ if not a submodule consumer
if [ ! -d "$CORE_DIR/instructions" ]; then
    CORE_DIR="$SCRIPT_DIR"
fi

PROMPT_FILE=$(mktemp)
trap "rm -f '$PROMPT_FILE'" EXIT

cat "$CORE_DIR/instructions/HOW_WE_WORK_BASE.md" > "$PROMPT_FILE"
printf "\n\n" >> "$PROMPT_FILE"
cat "$CORE_DIR/instructions/BUILDER_BASE.md" >> "$PROMPT_FILE"

if [ -f "$SCRIPT_DIR/.agentic_devops/HOW_WE_WORK_OVERRIDES.md" ]; then
    printf "\n\n" >> "$PROMPT_FILE"
    cat "$SCRIPT_DIR/.agentic_devops/HOW_WE_WORK_OVERRIDES.md" >> "$PROMPT_FILE"
fi

if [ -f "$SCRIPT_DIR/.agentic_devops/BUILDER_OVERRIDES.md" ]; then
    printf "\n\n" >> "$PROMPT_FILE"
    cat "$SCRIPT_DIR/.agentic_devops/BUILDER_OVERRIDES.md" >> "$PROMPT_FILE"
fi

claude --append-system-prompt-file "$PROMPT_FILE" --dangerously-skip-permissions
LAUNCHER_EOF

chmod +x "$PROJECT_ROOT/run_claude_builder.sh"

###############################################################################
# 6. Project Scaffolding
###############################################################################
if [ ! -d "$PROJECT_ROOT/features" ]; then
    mkdir "$PROJECT_ROOT/features"
    echo "Created features/"
fi

if [ ! -f "$PROJECT_ROOT/PROCESS_HISTORY.md" ]; then
    cat > "$PROJECT_ROOT/PROCESS_HISTORY.md" << EOF
# Process History

## $(date +%Y-%m-%d) — Project Bootstrapped
- Initialized agentic-dev-core submodule integration.
- Created \`.agentic_devops/\` override directory.
- Generated launcher scripts.
EOF
    echo "Created PROCESS_HISTORY.md"
fi

###############################################################################
# 7. Gitignore Handling
###############################################################################
GITIGNORE="$PROJECT_ROOT/.gitignore"

# Warn if .agentic_devops is gitignored
if [ -f "$GITIGNORE" ] && grep -q '\.agentic_devops' "$GITIGNORE"; then
    echo ""
    echo "WARNING: .agentic_devops appears in .gitignore."
    echo "  .agentic_devops/ contains project-specific overrides and SHOULD be tracked (committed)."
    echo "  Remove '.agentic_devops' from .gitignore if it was added by mistake."
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
    "# Agentic Tool Logs & Artifacts"
    "*.log"
    "*.pid"
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
                echo "# Added by agentic-dev bootstrap" >> "$GITIGNORE"
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
echo "  .agentic_devops/              (override directory)"
echo "  .agentic_devops/config.json   (tools_root: $TOOLS_ROOT_VALUE)"
echo "  .agentic_devops/.upstream_sha (submodule SHA: ${CURRENT_SHA:0:12}...)"
echo "  run_claude_architect.sh       (launcher)"
echo "  run_claude_builder.sh         (launcher)"
[ ! -d "$PROJECT_ROOT/features" ] || echo "  features/                     (feature specs directory)"
[ ! -f "$PROJECT_ROOT/PROCESS_HISTORY.md" ] || echo "  PROCESS_HISTORY.md            (process log)"
echo ""
echo "Next steps:"
echo "  1. Review and customize .agentic_devops/ override files."
echo "  2. Run ./run_claude_architect.sh to start the Architect agent."
echo "  3. Run ./run_claude_builder.sh to start the Builder agent."
echo ""
