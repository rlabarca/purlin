#!/bin/bash
# gemini.sh — Probe script for the Gemini CLI/API provider.
# Outputs JSON to stdout. Always exits 0.

AVAILABLE=false

# Check for API key or CLI
if [ -n "$GOOGLE_API_KEY" ] || [ -n "$GEMINI_API_KEY" ]; then
    AVAILABLE=true
elif command -v gemini >/dev/null 2>&1; then
    AVAILABLE=true
fi

cat << EOF
{
  "provider": "gemini",
  "available": $AVAILABLE,
  "models": [
    {
      "id": "gemini-3.0-pro",
      "label": "Gemini 3.0 Pro",
      "capabilities": { "effort": false, "permissions": true }
    },
    {
      "id": "gemini-3.0-flash",
      "label": "Gemini 3.0 Flash",
      "capabilities": { "effort": false, "permissions": true }
    },
    {
      "id": "gemini-2.5-pro",
      "label": "Gemini 2.5 Pro",
      "capabilities": { "effort": false, "permissions": true }
    },
    {
      "id": "gemini-2.5-flash",
      "label": "Gemini 2.5 Flash",
      "capabilities": { "effort": false, "permissions": true }
    }
  ],
  "setup_hint": "Set GOOGLE_API_KEY or install Gemini CLI"
}
EOF

exit 0
