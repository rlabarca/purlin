#!/usr/bin/env bash
# Criteria-aware fake external LLM for E2E testing of additive audit criteria.
#
# Usage (matches purlin:init LLM pattern):
#   ./fake_audit_llm_with_criteria.sh -p "{prompt}"
#
# Behavior:
#   - If prompt contains "PURLIN_AUDIT_OK" -> respond with that (init ping)
#   - If prompt contains "sleep()" criterion AND test code contains "sleep":
#     return WEAK with criterion "team-specific: sleep in test"
#   - Otherwise: return STRONG for all proofs
#
# This script proves that additional criteria reach the LLM prompt and
# change the assessment outcome.

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

# --- Check if additional criteria mention "sleep()" ---
HAS_SLEEP_CRITERION=false
if echo "$PROMPT" | grep -qi "sleep()"; then
  HAS_SLEEP_CRITERION=true
fi

# --- Check if test code contains sleep ---
HAS_SLEEP_IN_CODE=false
if echo "$PROMPT" | grep -q "time\.sleep\|sleep("; then
  HAS_SLEEP_IN_CODE=true
fi

# --- Generate assessment based on criteria presence ---
# Extract PROOF-IDs from prompt
PROOF_IDS=$(echo "$PROMPT" | grep -oE "PROOF-[0-9]+" | sort -u)

for pid in $PROOF_IDS; do
  # Find corresponding RULE-ID
  rid=$(echo "$PROMPT" | grep -A2 "$pid" | grep -oE "RULE-[0-9]+" | head -1)
  if [[ -z "$rid" ]]; then
    rid="RULE-1"
  fi

  if [[ "$HAS_SLEEP_CRITERION" == "true" && "$HAS_SLEEP_IN_CODE" == "true" ]]; then
    cat <<RESP
PROOF-ID: $pid
RULE-ID: $rid
ASSESSMENT: WEAK
CRITERION: team-specific: sleep in test — tests must not depend on timing
WHY: test contains time.sleep() which makes it timing-dependent
FIX: remove sleep() and use deterministic waits or mocks
---
RESP
  else
    cat <<RESP
PROOF-ID: $pid
RULE-ID: $rid
ASSESSMENT: STRONG
CRITERION: matches rule intent
WHY: test exercises the rule correctly
FIX: none
---
RESP
  fi
done

exit 0
