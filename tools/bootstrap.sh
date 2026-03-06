#!/bin/bash
# bootstrap.sh — DEPRECATED. Use init.sh instead.
# This shim delegates to tools/init.sh for backward compatibility.
echo "bootstrap.sh is deprecated. Use init.sh instead." >&2
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
exec "$SCRIPT_DIR/init.sh" "$@"
