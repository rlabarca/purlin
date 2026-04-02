# Feature: e2e_required_rules

> Scope: scripts/mcp/purlin_server.py
> Stack: shell/bash, python3 (sync_status, _build_coverage_rules)

## What it does

End-to-end test that sync_status correctly merges required rules (via `> Requires:`) and global invariant rules into a feature's coverage totals, and that coverage progresses correctly from 0/N through partial to full READY.

## Rules

- RULE-1: sync_status counts required rules and global invariant rules in the feature's total, not just own rules
- RULE-2: sync_status labels each rule as (own), (required), or (global) in the output
- RULE-3: Partial proofs (own rules proved, required and global not) show correct fraction and NOT READY status
- RULE-4: Full proofs (own + required + global all proved) show correct fraction and READY status

## Proof

- PROOF-1 (RULE-1): Create anchor (2 rules), global invariant (1 rule), feature (2 own rules + Requires anchor); run sync_status; verify feature shows 0/5 total rules @e2e
- PROOF-2 (RULE-2): Run sync_status on same setup; verify output contains (own), (required), and (global) labels on rule lines @e2e
- PROOF-3 (RULE-3): Add proofs for feature's 2 own rules only; run sync_status; verify 2/5 and not READY @e2e
- PROOF-4 (RULE-4): Add proofs for anchor's 2 rules and invariant's 1 rule; run sync_status; verify 5/5 and READY @e2e
