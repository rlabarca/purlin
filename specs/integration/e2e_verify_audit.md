# Feature: e2e_verify_audit

> Scope: scripts/mcp/purlin_server.py
> Stack: shell/bash, python3 (sync_status, vhash computation)
> Description: End-to-end integration test verifying the verify-receipt-audit roundtrip: verification hashes track spec/proof consistency, receipts detect drift when specs change, and structural vs. behavioral specs are distinguished.

## Rules

- RULE-1: Verify writes a receipt.json containing vhash, commit SHA, timestamp, rules list, and proofs list when all rules have passing proofs
- RULE-2: Audit matches when rules and proofs are unchanged since the receipt was written
- RULE-3: Audit detects mismatch when a rule is added to the spec but the receipt is stale
- RULE-4: Re-verify after adding a proof for the new rule produces a different vhash and audit matches again
- RULE-5: --audit mode reports structural-only features separately from behavioral features with correct labeling

## Proof

- PROOF-1 (RULE-1): Create temp repo with spec (3 rules) and proof file (3 pass); compute vhash and write receipt; verify receipt exists with correct vhash, commit SHA, and all 3 rules @e2e
- PROOF-2 (RULE-2): After writing receipt, recompute vhash from same rules+proofs; compare to receipt vhash; verify they match @e2e
- PROOF-3 (RULE-3): Add RULE-4 to spec; recompute vhash; compare to receipt; verify mismatch because receipt is stale @e2e
- PROOF-4 (RULE-4): Add passing proof for RULE-4; recompute vhash and write new receipt; verify new vhash differs from Phase A; audit again and verify match @e2e
- PROOF-5 (RULE-5): Create project with one behavioral spec and one structural-only spec; run sync_status; verify behavioral spec is PASSING and structural-only spec is not PASSING with structural checks reported separately; run check_spec_coverage on both and verify correct structural_only_spec values @e2e
