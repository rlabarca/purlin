# Feature: e2e_anchor_authority

> Scope: scripts/mcp/purlin_server.py
> Stack: shell/bash, python3 (drift), git (bare repos as external sources)
> Description: End-to-end test verifying that drift correctly detects when an
> externally-referenced anchor with local rules has its external source advance.
> The external reference is authoritative — local rules can be added but don't
> change the source. When the source updates, drift surfaces the staleness so
> the PM can resolve any conflicts between local rules and new external rules.

## Rules

- RULE-1: When an externally-referenced anchor has both external and local rules, drift detects staleness when the external source advances — returning an `external_anchor_drift` entry with status `stale` and the remote SHA
- RULE-2: When a local anchor file is modified (e.g. a new local rule added) and committed, drift classifies the anchor file under `CHANGED_SPECS` in its files list
- RULE-3: When the external source advances AND the local anchor file is modified, drift surfaces both: an `external_anchor_drift` entry with status `stale` AND a `spec_changes` entry showing the new rule added to the anchor
- RULE-4: proof_status for a feature requiring a stale mixed-rules anchor reports correct totals — own rules plus all anchor rules (external and local) — regardless of staleness
- RULE-5: drift returns the anchor name in `external_anchor_drift` matching the anchor's spec name, not the external repo name or path

## Proof

- PROOF-1 (RULE-1): Create bare git repo; create anchor pinned to initial SHA with 2 external rules + 1 local rule; advance bare repo; run drift; verify external_anchor_drift entry has status=stale and remote_sha @e2e
- PROOF-2 (RULE-2): Create externally-referenced anchor; commit; add a new local rule to the anchor and commit; run drift; verify anchor file appears in files with category CHANGED_SPECS @e2e
- PROOF-3 (RULE-3): Create externally-referenced anchor with local rules; commit; advance external repo AND add new local rule to anchor, commit; run drift; verify both external_anchor_drift stale entry AND spec_changes entry with new_rules for the anchor @e2e
- PROOF-4 (RULE-4): Create anchor with 2 external + 1 local rule; create feature with 1 own rule requiring the anchor; add proofs for all 4 rules; advance external repo (making anchor stale); run drift; verify proof_status total=4 and proved=4 for the feature @e2e
- PROOF-5 (RULE-5): Create anchor named "local_security" sourced from bare repo at /tmp path; advance repo; run drift; verify external_anchor_drift entry anchor field is "local_security" @e2e
