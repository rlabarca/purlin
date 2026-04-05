# Feature: e2e_external_refs

> Scope: scripts/mcp/purlin_server.py, scripts/report/purlin-report.html, scripts/hooks/pre-push.sh
> Stack: shell/bash, python3 (sync_status, drift), git (bare repos as external sources)
> Description: End-to-end integration test verifying that anchors with external git sources are correctly pinned, tracked for staleness, rendered in reports, and enforced in pre-push hooks. Tests use local bare git repos as mock external sources.

## Rules

- RULE-1: `_scan_specs` extracts `> Pinned:` and `> Path:` fields from anchor specs and stores them as `pinned` and `source_path` in the features dict
- RULE-2: sync_status anchor detail shows Source URL, Path (if present), and Pinned value (SHA truncated to 7 chars) for anchors with `> Source:`
- RULE-3: sync_status anchor detail shows unpinned warning for anchors with `> Source:` but no `> Pinned:`
- RULE-4: report-data.js feature entries include `pinned` and `source_path` fields when the anchor spec has `> Pinned:` and `> Path:` metadata
- RULE-5: Feature requiring an external anchor has its coverage include the anchor's rules — proved/total counts both own and anchor rules
- RULE-6: Feature requiring two external anchors has coverage include both anchors' rules
- RULE-7: Feature requiring one external anchor and one local anchor has both rule sets counted correctly
- RULE-8: Global external anchor rules auto-apply to all non-anchor features
- RULE-9: drift detects staleness when a git-sourced anchor's pinned SHA is behind the remote HEAD, returning an `external_anchor_drift` entry with status `stale` and the remote SHA
- RULE-10: drift detects unpinned state when an anchor has `> Source:` but no `> Pinned:`, returning an `external_anchor_drift` entry with status `unpinned`
- RULE-11: Coverage progression works with external anchors: UNTESTED → PARTIAL (own rules proved, anchor rules unproved) → PASSING (all rules proved)
- RULE-12: Pre-push hook enforces external anchor rule coverage — blocks push when an anchor-required proof is FAIL

## Proof

- PROOF-1 (RULE-1): Create anchor spec with `> Source:`, `> Pinned:`, `> Path:` metadata; run `_scan_specs`; verify features dict has correct `pinned` and `source_path` values @e2e
- PROOF-2 (RULE-2): Create project with external anchor (Source + Pinned + Path); run sync_status; verify output contains "Source:", "Path:", and "Pinned:" lines with correct values @e2e
- PROOF-3 (RULE-3): Create anchor with `> Source:` but no `> Pinned:`; run sync_status; verify output contains unpinned warning @e2e
- PROOF-4 (RULE-4): Create project with external anchor and report=true; run sync_status; parse report-data.js; verify feature entry has `pinned` and `source_path` fields @e2e
- PROOF-5 (RULE-5): Create bare git repo with spec containing 2 rules; create anchor with Source pointing to it; create feature with Requires pointing to anchor and 1 own rule; run sync_status; verify coverage is "0/3" (1 own + 2 anchor) @e2e
- PROOF-6 (RULE-6): Create 2 bare git repos as external sources (2 rules and 1 rule); create 2 anchors; create feature requiring both; verify coverage is "0/5" (2 own + 2 anchor1 + 1 anchor2) @e2e
- PROOF-7 (RULE-7): Create 1 external anchor and 1 local anchor (no Source); create feature requiring both; verify coverage includes rules from both @e2e
- PROOF-8 (RULE-8): Create external anchor with `> Global: true`; create 2 features; verify both features include the global anchor's rules in their coverage @e2e
- PROOF-9 (RULE-9): Create bare git repo; create anchor pinned to initial SHA; advance bare repo with new commit; run drift; verify `external_anchor_drift` contains entry with status="stale" and correct remote_sha @e2e
- PROOF-10 (RULE-10): Create anchor with `> Source:` but no `> Pinned:`; run drift; verify `external_anchor_drift` contains entry with status="unpinned" @e2e
- PROOF-11 (RULE-11): Create external anchor with 2 rules; create feature with 1 own rule + Requires anchor; add proof for own rule only; verify PARTIAL; add proofs for anchor rules; verify PASSING @e2e
- PROOF-12 (RULE-12): Create external anchor with 1 rule; create feature requiring it; create proof file with anchor rule FAIL; run pre-push hook; verify exit 1 (blocked) @e2e
