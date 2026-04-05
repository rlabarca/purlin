# E2E Spec Consolidation — Full Context Prompt

Use this to kick off a fresh session. Copy everything below the line.

---

## Task

Consolidate all 13 `e2e_*` specs in `specs/integration/` into the real Purlin feature specs they validate. These e2e specs are test-only containers that violate a newly established rule: **tests must prove rules in the feature they validate, not in a separate spec.**

The prohibition is already committed in:
- `skills/spec/SKILL.md` — "NEVER Create Test-Only Specs" section
- `skills/spec-from-code/SKILL.md` — step 6 prohibiting test-only specs
- `references/spec_quality_guide.md` — integration/ category marked as legacy

Branch: `dev/0.9.0`. Push to `origin` (bitbucket) branch `test/0.9.0` when done.
Move tag `v0.9.0` to final commit.

## What was already done (previous session)

Commits on `dev/0.9.0` since `22e81cea`:
- `4f1f90bb` — New proof plugins (C, PHP, SQL, TypeScript), cheating detection, test bypass fixes
- `875ce864` — Wired all new tests into Purlin feature proofs, added RULE-22 through RULE-28 to proof_plugins
- `e9aaed57` — Prohibited test-only specs in spec skills and quality guide

## Approach

For each e2e spec:

1. **Read the e2e spec's rules** and the **target feature spec's rules**
2. **Classify each e2e rule** as:
   - **DUPLICATE** — already exists in the target spec (same intent). Just note the mapping.
   - **NEW** — genuinely new behavioral rule not covered by the target spec. Add it.
3. **For NEW rules**: append to the target spec as the next RULE-N, write a PROOF-N description
4. **Update proof markers** in the test file: change `@pytest.mark.proof("e2e_xxx", ...)` or shell `purlin_proof "e2e_xxx" ...` to point at the target feature and correct RULE-N
5. **Delete** the e2e spec `.md`, `.proofs-*.json`, and `.receipt.json` files
6. **Run tests** to regenerate proof files under the correct feature specs

## The 13 e2e specs, their rules, test files, and target features

### 1. e2e_feature_scoped_overwrite (3 rules)
- **Test file:** `dev/test_e2e_feature_scoped_overwrite.sh` (shell proofs)
- **Proof file:** `specs/integration/e2e_feature_scoped_overwrite.proofs-unit.json`
- **Target:** `specs/proof/proof_plugins.md` (28 rules, last=RULE-21 but numbering has gaps — RULE-22 through RULE-28 exist for new plugins)
- **Rules:**
  - RULE-1: Writing proofs for one feature does not affect proof files of other features → **DUPLICATE of proof_plugins RULE-4**
  - RULE-2: Re-writing proofs replaces only that feature's entries → **DUPLICATE of proof_plugins RULE-4**
  - RULE-3: Removed test entries are purged on re-run → **NEW — add as proof_plugins RULE-29**

### 2. e2e_required_rules (4 rules)
- **Test file:** `dev/test_e2e_required_rules.sh`
- **Proof file:** `specs/integration/e2e_required_rules.proofs-unit.json`
- **Target:** `specs/mcp/sync_status.md` (21 rules)
- **Rules:**
  - RULE-1: Counts required + global rules in total → **DUPLICATE of sync_status RULE-4**
  - RULE-2: Labels (own), (required), (global) → **DUPLICATE of sync_status RULE-10**
  - RULE-3: Partial proofs show correct fraction → **DUPLICATE of sync_status RULE-21**
  - RULE-4: Full proofs show PASSING → **DUPLICATE of sync_status RULE-2**

### 3. e2e_manual_staleness (3 rules)
- **Test file:** `dev/test_e2e_manual_staleness.sh`
- **Proof file:** `specs/integration/e2e_manual_staleness.proofs-unit.json`
- **Target:** `specs/mcp/sync_status.md`
- **Rules:**
  - RULE-1: Fresh manual proof shows PASS → **DUPLICATE of sync_status RULE-5**
  - RULE-2: Stale manual proof shows STALE → **DUPLICATE of sync_status RULE-5**
  - RULE-3: Re-stamp clears stale state → **DUPLICATE of sync_status RULE-5**

### 4. e2e_strict_required (2 rules)
- **Test file:** `dev/test_e2e_strict_required.sh`
- **Proof file:** `specs/integration/e2e_strict_required.proofs-unit.json`
- **Target:** `specs/hooks/pre_push_hook.md` (9 rules)
- **Rules:**
  - RULE-1: Strict blocks push when required rules unproved → **Check if pre_push_hook has this**
  - RULE-2: Strict allows push when all proved → **Check if pre_push_hook has this**

### 5. e2e_audit_cache_pipeline (15 rules)
- **Test file:** `dev/test_e2e_audit_cache_pipeline.py` (Python/pytest proofs)
- **Proof file:** `specs/integration/e2e_audit_cache_pipeline.proofs-unit.json`
- **Targets:** Split between `specs/audit/static_checks.md` (16 rules) and `specs/mcp/sync_status.md` (21 rules)
- **Rules:**
  - RULE-1: write_audit_cache writes file → **DUPLICATE of static_checks RULE-12**
  - RULE-2: Cache entry required fields → **NEW for static_checks**
  - RULE-3: sync_status reads cache, shows integrity → **DUPLICATE of sync_status RULE-19**
  - RULE-4: No cache → "run purlin:audit" → **DUPLICATE of sync_status RULE-19**
  - RULE-5: Stale cache → "consider re-auditing" → **NEW for sync_status**
  - RULE-6: report-data.js audit_summary fields → **NEW for purlin_report or report_data**
  - RULE-7: audit_summary null when no cache → **NEW for purlin_report or report_data**
  - RULE-8: Per-feature audit from cache → **NEW for sync_status or report_data**
  - RULE-9: Entries without feature field excluded from per-feature → **NEW for static_checks**
  - RULE-10: Deleting cache reverts to no-audit → **DUPLICATE of RULE-4 scenario**
  - RULE-11: NO_PROOF penalizes own behavioral rules → **NEW for sync_status**
  - RULE-12: Required anchor rules not penalized → **NEW for sync_status**
  - RULE-13: Global integrity includes all features → **NEW for sync_status**
  - RULE-14: Read-side dedup keeps latest per (feature, proof_id) → **DUPLICATE of static_checks RULE-11/12**
  - RULE-15: Write-side pruning → **DUPLICATE of static_checks RULE-12**

### 6. e2e_hybrid_audit (11 rules)
- **Test file:** `dev/test_e2e_hybrid_audit.sh`
- **Proof file:** `specs/integration/e2e_hybrid_audit.proofs-unit.json`
- **Target:** `specs/audit/static_checks.md` (16 rules)
- **Rules:** All 11 are DUPLICATES of static_checks RULE-1 through RULE-14 (assert_true, no_assertions, logic_mirroring, mock_target, bare_except, JSON output, exit codes, spec coverage, shell if/else)

### 7. e2e_verify_audit (5 rules)
- **Test file:** `dev/test_e2e_verify_audit.sh`
- **Proof file:** `specs/integration/e2e_verify_audit.proofs-unit.json`
- **Target:** `specs/mcp/sync_status.md`
- **Rules:**
  - RULE-1: Verify writes receipt.json → **Check if sync_status has this**
  - RULE-2: Audit matches when unchanged → **Related to sync_status RULE-6 (vhash)**
  - RULE-3: Stale receipt when rule added → **DUPLICATE of sync_status RULE-15**
  - RULE-4: Re-verify produces different vhash → **DUPLICATE of sync_status RULE-6**
  - RULE-5: --audit mode structural-only reporting → **NEW for sync_status**

### 8. e2e_anchor_authority (5 rules)
- **Test file:** `dev/test_e2e_anchor_authority.sh`
- **Proof file:** `specs/integration/e2e_anchor_authority.proofs-e2e.json`
- **Targets:** `specs/mcp/drift.md` (11 rules) + `specs/mcp/sync_status.md`
- **Rules:**
  - RULE-1: Drift detects external anchor staleness → **Check drift spec**
  - RULE-2: Drift classifies modified anchor as CHANGED_SPECS → **Check drift spec**
  - RULE-3: Both external stale + local modified surfaced → **NEW for drift**
  - RULE-4: proof_status totals correct despite staleness → **Check sync_status**
  - RULE-5: drift returns anchor name matching spec name → **Check drift spec**

### 9. e2e_external_refs (12 rules)
- **Test file:** `dev/test_e2e_external_refs.sh`
- **Proof file:** `specs/integration/e2e_external_refs.proofs-unit.json`
- **Targets:** `specs/mcp/sync_status.md` + `specs/dashboard/purlin_report.md` (30 rules)
- **Rules:** Mix of sync_status metadata extraction, anchor display, coverage calculation, drift detection, and pre_push_hook enforcement. Read both target specs carefully to classify.

### 10. e2e_cross_model_audit (5 rules)
- **Test file:** `dev/test_e2e_cross_model_audit.sh`
- **Proof file:** `specs/integration/e2e_cross_model_audit.proofs-unit.json`
- **Target:** `specs/audit/static_checks.md`
- **Rules:** External LLM audit behavior, response parsing, two-pass flow. Some may need to go to a new section in static_checks or to skill_audit.

### 11. e2e_spec_migration (9 rules)
- **Test file:** `dev/test_e2e_spec_migration.py` (Python/pytest proofs)
- **Proof file:** `specs/integration/e2e_spec_migration.proofs-e2e.json`
- **Target:** `specs/skills/skill_spec_from_code.md` (9 rules)
- **Rules:** Legacy format conversion, unnumbered rule renumbering, missing section detection, compliance validation, metadata preservation.

### 12. e2e_spec_from_input (13 rules)
- **Test file:** `dev/test_e2e_spec_from_input.py` (Python/pytest proofs)
- **Proof file:** `specs/integration/e2e_spec_from_input.proofs-unit.json`
- **Target:** `specs/skills/skill_spec_from_code.md` (9 rules)
- **Rules:** Spec generation from plain description, PRD, vague input, customer feedback. Sequential numbering, proof generation, metadata extraction, assumed tags.

### 13. e2e_teammate_audit_loop (7 rules)
- **Test file:** `dev/test_e2e_teammate_audit_loop.sh`
- **Proof file:** `specs/integration/e2e_teammate_audit_loop.proofs-unit.json`
- **Targets:** `specs/skills/skill_audit.md` (3 rules) + `specs/skills/skill_build.md` (7 rules)
- **Rules:** Audit→builder loop documentation, independent auditor mode, re-audit cycle, termination condition, anchor rule handling.

## Current rule counts in target specs

| Spec | File | Current rules | Last RULE-N |
|------|------|--------------|-------------|
| sync_status | specs/mcp/sync_status.md | 21 | RULE-21 |
| proof_plugins | specs/proof/proof_plugins.md | 28 | RULE-28 |
| static_checks | specs/audit/static_checks.md | 16 | RULE-16 |
| drift | specs/mcp/drift.md | 11 | RULE-11 |
| pre_push_hook | specs/hooks/pre_push_hook.md | 9 | RULE-9 |
| skill_spec_from_code | specs/skills/skill_spec_from_code.md | 9 | RULE-9 |
| skill_audit | specs/skills/skill_audit.md | 3 | RULE-3 |
| skill_build | specs/skills/skill_build.md | 7 | RULE-7 |
| purlin_report | specs/dashboard/purlin_report.md | 30 | RULE-30 |
| report_data | specs/dashboard/report_data.md | 21 | RULE-21 |

## Process for each e2e spec

1. Read the e2e spec and the target feature spec side by side
2. For each e2e rule, grep the target spec for overlapping intent
3. Mark as DUPLICATE (note mapping) or NEW (assign next RULE-N)
4. For NEW rules: add to target spec's `## Rules` and `## Proof` sections
5. Update proof markers in the test file (`.py` uses `@pytest.mark.proof`, `.sh` uses `purlin_proof`)
6. Delete: `specs/integration/e2e_xxx.md`, `specs/integration/e2e_xxx.proofs-*.json`, `specs/integration/e2e_xxx.receipt.json`
7. Run the test file to regenerate proofs under the target spec's directory

## Order of operations

Start with the simplest (fewest rules, most duplicates):
1. e2e_feature_scoped_overwrite (3 rules, 2 duplicates)
2. e2e_required_rules (4 rules, all duplicates)
3. e2e_manual_staleness (3 rules, all duplicates)
4. e2e_strict_required (2 rules)
5. e2e_hybrid_audit (11 rules, all duplicates of static_checks)
6. e2e_verify_audit (5 rules)
7. e2e_teammate_audit_loop (7 rules)
8. e2e_anchor_authority (5 rules)
9. e2e_cross_model_audit (5 rules)
10. e2e_external_refs (12 rules)
11. e2e_spec_migration (9 rules)
12. e2e_spec_from_input (13 rules)
13. e2e_audit_cache_pipeline (15 rules, split across targets)

After all 13: run full test suite, run `purlin:status`, verify coverage didn't drop.

## Verification

```bash
# Run all tests
python3 -m pytest dev/ -v --timeout=120

# Run shell proof tests
for f in dev/test_e2e_*.sh; do bash "$f"; done

# Check no e2e specs remain
ls specs/integration/e2e_*  # should be empty or directory gone

# Verify coverage
# Use purlin:status to check all features

# Push
git tag -d v0.9.0 && git tag v0.9.0
git push origin dev/0.9.0:test/0.9.0 && git push origin v0.9.0 --force
```
