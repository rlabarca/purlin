#!/usr/bin/env bash
# Fake external LLM for E2E testing of purlin:init --audit-llm flow.
#
# Usage (matches the pattern purlin:init expects):
#   ./fake_audit_llm.sh -p "{prompt}"
#
# Behavior:
#   - If prompt contains "PURLIN_AUDIT_OK" → respond with that (init ping test)
#   - If prompt contains "PROOF-ID:" → parse proof IDs and return structured
#     STRONG assessments (audit flow)
#   - Otherwise → echo back the prompt (fallback)
#
# This script is NOT a real LLM — it returns deterministic responses so we can
# test the config/plumbing without network calls.

set -euo pipefail

# Parse -p flag (the prompt)
PROMPT=""
while [[ $# -gt 0 ]]; do
  case "$1" in
    -p) PROMPT="$2"; shift 2 ;;
    *)  shift ;;
  esac
done

# If prompt is empty, read from stdin
if [[ -z "$PROMPT" ]]; then
  PROMPT=$(cat)
fi

# --- Init ping test ---
if echo "$PROMPT" | grep -q "PURLIN_AUDIT_OK"; then
  echo "PURLIN_AUDIT_OK"
  exit 0
fi

# --- Audit structured response ---
# Extract PROOF-ID lines and generate STRONG assessments for each
if echo "$PROMPT" | grep -q "PROOF-ID:"; then
  # Find all PROOF-ID patterns in the prompt template
  echo "$PROMPT" | grep "^PROOF-ID:" | while read -r line; do
    proof_id=$(echo "$line" | sed 's/^PROOF-ID:[ \t]*//')
    # Find the corresponding RULE-ID (next line after PROOF-ID in prompt)
    rule_id=$(echo "$PROMPT" | grep -A1 "^PROOF-ID: $proof_id" | grep "^RULE-ID:" | head -1 | sed 's/^RULE-ID:[ \t]*//')
    if [[ -z "$rule_id" ]]; then
      rule_id="RULE-1"
    fi
    cat <<RESP
PROOF-ID: $proof_id
RULE-ID: $rule_id
ASSESSMENT: STRONG
CRITERION: matches rule intent
WHY: test exercises the rule correctly
FIX: none
---
RESP
  done
  exit 0
fi

# --- Fallback ---
echo "FAKE_LLM_ECHO: received prompt of length ${#PROMPT}"
