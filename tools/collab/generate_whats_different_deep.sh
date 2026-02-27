#!/usr/bin/env bash
# generate_whats_different_deep.sh — Generate a deep semantic analysis digest.
#
# Usage: generate_whats_different_deep.sh <session_name>
#
# 1. Runs the extraction tool to produce structured JSON.
# 2. Invokes Claude CLI in non-interactive mode with a deep-analysis prompt.
# 3. Writes the analysis to features/digests/whats-different-analysis.md.
#
# Exit codes:
#   0 — success
#   1 — missing argument or extraction failure
#   2 — agent synthesis failure

set -euo pipefail

SESSION="${1:-}"
if [ -z "$SESSION" ]; then
    echo "Usage: generate_whats_different_deep.sh <session_name>" >&2
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
ANALYSIS_FILE="${DIGEST_DIR}/whats-different-analysis.md"

# Ensure output directory exists
mkdir -p "$DIGEST_DIR"

# Step 1: Run extraction
EXTRACTION_JSON=$(PURLIN_PROJECT_ROOT="$PROJECT_ROOT" python3 "$EXTRACT_TOOL" "$SESSION" 2>&1) || {
    echo "Extraction failed: $EXTRACTION_JSON" >&2
    exit 1
}

# Check if SAME — write a short analysis and exit
SYNC_STATE=$(echo "$EXTRACTION_JSON" | python3 -c "import json,sys; print(json.load(sys.stdin).get('sync_state',''))")
if [ "$SYNC_STATE" = "SAME" ]; then
    DATE=$(date -u +"%Y-%m-%d %H:%M UTC")
    cat > "$ANALYSIS_FILE" <<EOF
# Impact Summary

**Generated:** ${DATE}
**Session:** collab/${SESSION}

Local main is in sync with collab/${SESSION}. No impact to summarize.
EOF
    cat "$ANALYSIS_FILE"
    exit 0
fi

# Step 2: Invoke Claude CLI for deep semantic analysis
DATE=$(date -u +"%Y-%m-%d %H:%M UTC")

AGENT_PROMPT="You are a senior technical analyst for the Purlin framework. Given the structured JSON extraction below, produce a concise impact analysis that helps a collaborator quickly understand:

1. **What functionality changed and why it matters** — not just file lists, but what capabilities were added, modified, or removed.
2. **Which workflows or user experiences are affected** — what will feel different to users or agents.
3. **What specification shifts mean for product direction** — are there new architectural patterns, policy changes, or design shifts?
4. **What the collaborator should pay attention to** — priority items, potential conflicts, things that need testing.

Format as markdown with these sections:
- **Key Changes** — 3-5 bullet points, most important first
- **Workflow Impact** — how day-to-day usage is affected
- **Architecture Notes** — any structural or pattern changes (skip if none)
- **Action Items** — what the reader should do next

Rules:
- Be concise and actionable — one paragraph per section max
- Focus on impact, not inventory — 'added user auth' not 'added auth.py, auth_test.py, ...'
- Do not invent information not in the JSON
- If changes are minor, say so briefly

JSON extraction data:

\`\`\`json
${EXTRACTION_JSON}
\`\`\`"

# Try to invoke claude CLI for synthesis
ANALYSIS=""
if command -v claude >/dev/null 2>&1; then
    ANALYSIS=$(echo "$AGENT_PROMPT" | claude --print 2>/dev/null) || {
        ANALYSIS=""
    }
fi

if [ -z "${ANALYSIS:-}" ]; then
    # Fallback: generate a basic analysis without LLM
    ANALYSIS=$(PURLIN_PROJECT_ROOT="$PROJECT_ROOT" python3 -c "
import json, sys

data = json.loads('''${EXTRACTION_JSON}''')
state = data['sync_state']
lines = []
lines.append('# Impact Summary')
lines.append('')
lines.append('**Generated:** ${DATE}')
lines.append('**Session:** collab/${SESSION}')
lines.append('**Sync State:** ${SYNC_STATE}')
lines.append('')

total_commits = data.get('commits_ahead', 0) + data.get('commits_behind', 0)

def count_changes(direction):
    if not direction or isinstance(direction, list):
        return {'specs': 0, 'code': 0, 'tests': 0}
    cats = direction.get('categories', {})
    return {
        'specs': len(cats.get('feature_specs', [])) + len(cats.get('anchor_nodes', [])) + len(cats.get('policy_nodes', [])),
        'code': len(cats.get('code', [])),
        'tests': len(cats.get('tests', [])),
    }

local = count_changes(data.get('local_changes', {}))
collab = count_changes(data.get('collab_changes', {}))
specs = local['specs'] + collab['specs']
code = local['code'] + collab['code']
tests = local['tests'] + collab['tests']

lines.append('## Key Changes')
lines.append(f'- {total_commits} commit(s) across {specs} spec(s), {code} code file(s), and {tests} test file(s)')
if specs > 0:
    lines.append('- Specification changes detected — review feature specs for updated requirements')
if code > 3:
    lines.append('- Significant code changes — recommend running full test suite')
lines.append('')
lines.append('## Action Items')
lines.append('- Review the file-level What\\'s Different digest for details')
if specs > 0:
    lines.append('- Check feature specs for updated scenarios or requirements')
lines.append('')

print('\\n'.join(lines))
" 2>&1) || {
        echo "Fallback analysis generation failed" >&2
        exit 2
    }
fi

# Write the analysis file
echo "$ANALYSIS" > "$ANALYSIS_FILE"

# Output the analysis to stdout
cat "$ANALYSIS_FILE"
