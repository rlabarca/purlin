# Feature: e2e_strict_required

> Scope: scripts/hooks/pre-push.sh, scripts/mcp/purlin_server.py
> Stack: shell/bash, python3 (pre-push hook, sync_status with required rules)

## What it does

End-to-end test that strict mode in the pre-push hook correctly accounts for required rules when deciding whether to block. A feature is not READY until both its own rules and all required rules have passing proofs.

## Rules

- RULE-1: Strict mode blocks push when own rules are proved but required rules have no proof (feature is not READY)
- RULE-2: Strict mode allows push when both own rules and required rules all have passing proofs (feature is READY)

## Proof

- PROOF-1 (RULE-1): Create anchor (2 rules) and feature (2 own rules + Requires anchor); set strict mode; create proofs for own rules only; run pre-push hook; verify exit 1 with strict mode block @e2e
- PROOF-2 (RULE-2): Add proofs for anchor's 2 rules; run pre-push hook; verify exit 0 @e2e
