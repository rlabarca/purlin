#!/bin/bash
# claude.sh — Probe script for the Claude Code CLI provider.
# Outputs JSON to stdout. Always exits 0.

AVAILABLE=false
VERSION=""

if command -v claude >/dev/null 2>&1; then
    AVAILABLE=true
    VERSION=$(claude --version 2>/dev/null | head -1 || echo "unknown")
fi

cat << EOF
{
  "provider": "claude",
  "available": $AVAILABLE,
  "version": "$VERSION",
  "models": [
    {
      "id": "claude-opus-4-6",
      "label": "Opus 4.6",
      "capabilities": { "effort": true, "permissions": true }
    },
    {
      "id": "claude-sonnet-4-6",
      "label": "Sonnet 4.6",
      "capabilities": { "effort": true, "permissions": true }
    },
    {
      "id": "claude-haiku-4-5-20251001",
      "label": "Haiku 4.5",
      "capabilities": { "effort": true, "permissions": true }
    }
  ],
  "setup_hint": "Install Claude Code: https://docs.anthropic.com/en/docs/claude-code"
}
EOF

exit 0
