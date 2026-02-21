#!/bin/bash
# detect-providers.sh — Aggregate all provider probe scripts into a single JSON array.
# Usage: bash tools/detect-providers.sh
# Outputs a JSON array to stdout. Always exits 0.
set -uo pipefail

# Resolve script directory and providers path
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROVIDERS_DIR="$SCRIPT_DIR/providers"

if [ ! -d "$PROVIDERS_DIR" ]; then
    echo "[]"
    exit 0
fi

# Collect probe results into a temp directory (one file per probe)
TMPDIR_PROBES=$(mktemp -d)
trap "rm -rf '$TMPDIR_PROBES'" EXIT

COUNT=0
for probe in "$PROVIDERS_DIR"/*.sh; do
    [ -f "$probe" ] || continue

    # Run probe, capture output to temp file, skip on failure
    OUTFILE="$TMPDIR_PROBES/$COUNT.json"
    if bash "$probe" > "$OUTFILE" 2>/dev/null; then
        # Validate JSON
        if python3 -c "import json; json.load(open('$OUTFILE'))" 2>/dev/null; then
            COUNT=$((COUNT + 1))
        else
            rm -f "$OUTFILE"
        fi
    else
        rm -f "$OUTFILE"
    fi
done

# Build JSON array from collected files
if [ "$COUNT" -eq 0 ]; then
    echo "[]"
else
    python3 -c "
import json, glob, os
items = []
for f in sorted(glob.glob(os.path.join('$TMPDIR_PROBES', '*.json'))):
    try:
        items.append(json.load(open(f)))
    except (json.JSONDecodeError, IOError):
        pass
print(json.dumps(items, indent=2))
"
fi

exit 0
