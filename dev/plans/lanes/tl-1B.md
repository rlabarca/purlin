# Lane 1B: signatures

Plan: `dev/plans/three-levels.md` (in full). Rules: `dev/plans/lanes/tl-_rules.md` (in full).
Worktree `/Users/richlabarca/LocalCode/purlin-wt/1B`, branch `lane/1B` off `three-levels`.

## What you own

- `scripts/mcp/purlin/approvals.py` → `scripts/mcp/purlin/signatures.py` (`git mv`, then
  rewrite per Part B2): `signatures_dir(project_root, info)` returns `<spec>.signatures`;
  `SIGNATURE_NAME_RE` and `HOLD_NAME_RE` keep today's shape
  (`<RULE-N>.<hash8>.<signer-slug>.json`, `<RULE-N>.<hash8>.<holder-slug>.hold.json`);
  `signer_slug(email)`; `load_signatures` reads the body field `signer`; no legacy body, no
  `is_ci`, no auto-approval of any kind; `is_current`, `counts`, `commit_is_signed`,
  `commit_author`, `is_ancestor`, `test_hash_kind`, `design_hash`, the triple hashing as today
  with the new words. `counts` takes the gate: under `strong` a signature from anyone whose
  hashes match counts; under `signed` the rules of Part A3 apply (signed commit that verifies,
  author on `signers` as of that commit, author did not author the last commit to the test
  file, hashes match, commit on the protected branch).
- `scripts/mcp/purlin/ids.py`: `_approval_paths` becomes `_signature_paths` and reads
  `signatures.signatures_dir`. Touch nothing else in `ids.py`; lane 1A owns the rest.
- The import sites of `approvals` in `scripts/mcp/purlin/payload.py`, `scripts/review/approve.py`,
  `scripts/ci/verify_gate.py`, `scripts/run/purlin_run.py` and `scripts/run/records.py`: change
  only the import line and the attribute names that no longer exist, so the tree still imports.
  Lanes 1A, 2A and 2B rewrite those files after you; leave their logic alone.
- Tests: `dev/test_approvals.py` → `dev/test_signatures.py` (`git mv`): keep `TestTheTriple`,
  `TestStale`, `TestTheFile`, `TestTheSignedCommit`, `TestTheAncestorCheck` rewritten in the new
  words against the new names; delete `TestAutoApproval`. `dev/test_holds.py` rewritten.
- Spec: `specs/review/approvals.md` → `specs/review/signatures.md` through the rename path
  (`tl-_rules.md` "Code"): `git mv` the spec, `git mv specs/review/approvals.approvals` to
  `specs/review/signatures.approvals`, `git mv .purlin/records/approvals .purlin/records/signatures`,
  every marker `("approvals", ...)` becomes `("signatures", ...)`, `# Feature: signatures`, every
  `> Requires: approvals` entry in other specs becomes `signatures`. Then rewrite: RULE-1..10
  (hashing and the file), RULE-17..23 (signing: what a counting signature is, per A3),
  RULE-40 (holds). Delete RULE-11..16, RULE-39, RULE-41 (the CI auto-approval and the legacy
  body) and their proofs. **Leave RULE-24..38 and their proofs in place, untouched**: lane 2A
  moves them into `specs/ci/gate_check.md` and rewrites them there. Because of that,
  `specs/review/signatures.md` stays in `PENDING_REWRITE` (lane 2A deletes the entry); delete
  your other entries (`scripts/mcp/purlin/approvals.py`, `dev/test_approvals.py`,
  `dev/test_holds.py`, `specs/review/approvals.md`).
- `references/formats/approval_format.md` → `references/formats/signature_format.md`
  (`git mv`), rewritten to `> Format-Version: 3` in the same commit as `signatures.py`: the
  directory `<spec>.signatures/`, the filename grammar, `"schema": "purlin-signature/1"`, the
  body fields `signer` (email), `gate` (the gate at signing, one of `passed strong signed`),
  `note` (a string or null; set by `purlin:sign --note`), the hashes as today, no CI variant,
  holds unchanged in shape. State the counting rules of Part A3 as the "When a signature
  counts" section. Grep `docs/`, `skills/` and `agents/purlin.md` for `approval_format` and
  change only the link text and path (the surrounding prose belongs to lanes 5 and 6).

## Words

`signature`, `signer`, `signer list` (`signers` in config), `hold`, `holder`, `note`,
`signature stale`, `the signing commit`, `counting signature`. Never `approval`, `approver`,
`auto-approval`, `approved`.

## Tests to keep green

`dev/test_signatures.py`, `dev/test_holds.py`, `dev/test_vocabulary.py`, and the tree must
import (`python3 -c "import sys; sys.path.insert(0,'scripts/mcp'); from purlin import payload"`).

## Expected red

`dev/test_mcp_server.py`, `dev/test_review_list.py`, `dev/test_purlin_report.py`,
`dev/test_init_update.py` (0.10-dev fixture deleted in phase 0), `dev/test_consumer_ci.py`
(fixture gate is `strong` before the code knows it), `dev/test_verify_gate.py`,
`dev/test_records.py`, `dev/test_run_script.py` and anything else that read the old
`approvals` names: owned by lanes 1A, 2A, 2B, 3 and 4. Name each one you see in your report.

## Acceptance

```
pytest dev/test_signatures.py dev/test_holds.py dev/test_vocabulary.py
bash dev/run_tests.sh --fast   (report the summary and the red list)
```
