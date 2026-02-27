#!/usr/bin/env bash
# generate_whats_different.sh — Generate a What's Different? digest.
#
# Usage: generate_whats_different.sh <session_name>
#
# 1. Runs the extraction tool to produce structured JSON.
# 2. Invokes Claude CLI in non-interactive mode to synthesize a plain-English digest.
# 3. Writes the digest to features/digests/whats-different.md.
#
# Exit codes:
#   0 — success
#   1 — missing argument or extraction failure
#   2 — agent synthesis failure (extraction JSON is still available)

set -euo pipefail

SESSION="${1:-}"
if [ -z "$SESSION" ]; then
    echo "Usage: generate_whats_different.sh <session_name>" >&2
    exit 1
fi

# Resolve project root
if [ -n "${PURLIN_PROJECT_ROOT:-}" ] && [ -d "$PURLIN_PROJECT_ROOT" ]; then
    PROJECT_ROOT="$PURLIN_PROJECT_ROOT"
else
    SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
    PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
    # Check for submodule layout
    if [ -d "$PROJECT_ROOT/../.purlin" ]; then
        PROJECT_ROOT="$(cd "$PROJECT_ROOT/.." && pwd)"
    fi
fi

TOOLS_ROOT=$(python3 -c "
import json, os
try:
    with open(os.path.join('${PROJECT_ROOT}', '.purlin', 'config.json')) as f:
        print(json.load(f).get('tools_root', 'tools'))
except Exception:
    print('tools')
")

EXTRACT_TOOL="${PROJECT_ROOT}/${TOOLS_ROOT}/collab/extract_whats_different.py"
DIGEST_DIR="${PROJECT_ROOT}/features/digests"
DIGEST_FILE="${DIGEST_DIR}/whats-different.md"

# Ensure output directory exists
mkdir -p "$DIGEST_DIR"

# Step 1: Run extraction
EXTRACTION_JSON=$(PURLIN_PROJECT_ROOT="$PROJECT_ROOT" python3 "$EXTRACT_TOOL" "$SESSION" 2>&1) || {
    echo "Extraction failed: $EXTRACTION_JSON" >&2
    exit 1
}

# Check if SAME — write a short digest and exit
SYNC_STATE=$(echo "$EXTRACTION_JSON" | python3 -c "import json,sys; print(json.load(sys.stdin).get('sync_state',''))")
if [ "$SYNC_STATE" = "SAME" ]; then
    DATE=$(date -u +"%Y-%m-%d %H:%M UTC")
    cat > "$DIGEST_FILE" <<EOF
# What's Different?

**Generated:** ${DATE}
**Session:** collab/${SESSION}

Local main is in sync with collab/${SESSION}. Nothing to summarize.
EOF
    cat "$DIGEST_FILE"
    exit 0
fi

# Step 2: Invoke Claude CLI to synthesize the digest
# The agent prompt instructs Claude to produce a structured markdown summary.
DATE=$(date -u +"%Y-%m-%d %H:%M UTC")

AGENT_PROMPT="You are a technical writer for the Purlin framework. Given the structured JSON extraction below, produce a clear, concise markdown digest following this exact structure:

# What's Different?

**Generated:** ${DATE}
**Session:** collab/${SESSION}
**Sync State:** ${SYNC_STATE}

Then include these sections as appropriate based on the sync state:

## At a Glance
A summary table with columns: Side, Commits, Spec Changes, Code Changes.

If AHEAD: include only 'Your Local Changes' sections.
If BEHIND: include only 'Collab Changes' sections.
If DIVERGED: include both.

For each direction include these subsections (skip empty ones):

### Spec Changes (\"What Should Change\")
- Feature specs added, modified, or deleted — plain language
- Anchor and policy node changes and their implications
- Visual spec changes
- New discoveries (BUG, SPEC_DISPUTE, etc.)
- Status transitions (TODO->TESTING, TESTING->COMPLETE, etc.)

### Code Changes (\"What Did Change\")
- Implementation files grouped by area
- New or modified tests
- Companion file updates

### Purlin Changes (Framework and Process)
- .purlin/ directory changes (config, overrides)
- Purlin submodule updates
- Explain what changes mean for agent behavior

### Sync Check
- Flag specs that changed without code changes
- Flag code that changed without spec changes
- This is informational, not blocking

Rules:
- Be concise — one line per change, grouped logically
- Use bullet points, not paragraphs
- Reference file paths when useful
- Do not invent information not in the JSON

JSON extraction data:

\`\`\`json
${EXTRACTION_JSON}
\`\`\`"

# Try to invoke claude CLI for synthesis
if command -v claude >/dev/null 2>&1; then
    DIGEST=$(echo "$AGENT_PROMPT" | claude --print 2>/dev/null) || {
        # Fallback: produce a basic digest from extraction data directly
        DIGEST=""
    }
fi

if [ -z "${DIGEST:-}" ]; then
    # Fallback: generate a basic digest without LLM
    DIGEST=$(PURLIN_PROJECT_ROOT="$PROJECT_ROOT" python3 -c "
import json, sys

data = json.loads('''${EXTRACTION_JSON}''')
state = data['sync_state']
lines = []
lines.append('# What\\'s Different?')
lines.append('')
lines.append('**Generated:** ${DATE}')
lines.append('**Session:** collab/${SESSION}')
lines.append('**Sync State:** ${SYNC_STATE}')
lines.append('')

def summarize_direction(label, direction):
    if not direction:
        return []
    out = []
    commits = direction.get('commits', [])
    cats = direction.get('categories', {})
    transitions = direction.get('transitions', [])

    out.append(f'## {label}')
    out.append(f'')
    out.append(f'{len(commits)} commit(s)')
    out.append('')

    specs = cats.get('feature_specs', [])
    anchors = cats.get('anchor_nodes', [])
    policies = cats.get('policy_nodes', [])
    if specs or anchors or policies:
        out.append('### Spec Changes')
        for f in specs:
            out.append(f'- {f[\"status\"]} {f[\"path\"]}')
        for f in anchors:
            out.append(f'- [Anchor] {f[\"status\"]} {f[\"path\"]}')
        for f in policies:
            out.append(f'- [Policy] {f[\"status\"]} {f[\"path\"]}')
        out.append('')

    if transitions:
        out.append('### Status Transitions')
        for t in transitions:
            out.append(f'- {t[\"feature\"]}: {t.get(\"from_state\",\"?\")} -> {t[\"to_state\"]}')
        out.append('')

    code = cats.get('code', [])
    tests = cats.get('tests', [])
    companions = cats.get('companion_files', [])
    if code or tests or companions:
        out.append('### Code Changes')
        for f in code:
            out.append(f'- {f[\"status\"]} {f[\"path\"]}')
        for f in tests:
            out.append(f'- [Test] {f[\"status\"]} {f[\"path\"]}')
        for f in companions:
            out.append(f'- [Notes] {f[\"status\"]} {f[\"path\"]}')
        out.append('')

    purlin = cats.get('purlin_config', [])
    submod = cats.get('submodule', [])
    if purlin or submod:
        out.append('### Purlin Changes')
        for f in purlin:
            out.append(f'- {f[\"status\"]} {f[\"path\"]}')
        for f in submod:
            out.append(f'- [Submodule] {f[\"status\"]} {f[\"path\"]}')
        out.append('')

    return out

if state in ('AHEAD', 'DIVERGED'):
    lines.extend(summarize_direction('Your Local Changes', data.get('local_changes', {})))
if state in ('BEHIND', 'DIVERGED'):
    lines.extend(summarize_direction('Collab Changes', data.get('collab_changes', {})))

print('\\n'.join(lines))
" 2>&1) || {
        echo "Fallback digest generation failed" >&2
        exit 2
    }
fi

# Write the digest file
echo "$DIGEST" > "$DIGEST_FILE"

# Output the digest to stdout
cat "$DIGEST_FILE"
