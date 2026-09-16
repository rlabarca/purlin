# Lane 5B: references, formats, tools, root

Plan: `dev/plans/three-levels.md` (in full). Rules: `dev/plans/lanes/tl-_rules.md` (in full).
Worktree `/Users/richlabarca/LocalCode/purlin-wt/5B`, branch `lane/5B` off `three-levels`.

You start from the phase 0 commit and draft from Part A. Phases 1 to 4 land on `three-levels`
while you work; when the orchestrator tells you phase 4 is merged, `git rebase three-levels`,
check every path, field and message you cite against the code as it then is, run the
acceptance again, then report. Two format files are not yours: lane 1B owns
`references/formats/signature_format.md` (from `approval_format.md`, version 3) and lane 2B
owns `references/formats/record_format.md` (version 2). Do not edit either; link to them.

## What you own (Part C2, phase 5B)

- `references/glossary.md`: the words of Part A1 as the live table; the chain of Part A2; the
  retired table gains every word and phrase of decision 15 with what replaced each
  (`tested`→`passed`, `recorded`→`strong`, `approved`→`signed`, `approve`→`sign`,
  `approval`→`signature`, `approver`/`approvers`→`signer`/`signers`, `verified`→the cell
  word, `verdict`→`observations` and `settled`, `Reviewed`→retired with no replacement,
  `re-verify`→`code changed`, `Proof ready`→`ready`, `lowest state`→`blocked by`, `seven
  states`→`three levels`, `auto-approval`→retired, `review queue`→`review list`,
  `purlin:verify`→`purlin:audit`, `purlin:review`→`purlin:sign`, `purlin:approve`→
  `purlin:sign`, `verify_gate`→`gate_check`, `verify-gate:`→`gate:`, `validated/`→`record/`);
  the `audit` row leaves the retired table. The glossary is the one file excluded from the
  vocabulary check, so it is the only place those spellings are written.
- `references/hard_gates.md`: rewrite: the level table of Part A3, source, the signer list,
  holds, what a counting signature is; the "Auto-approval" section deleted.
- `references/review_criteria.md`: the free checks stay; "The three risk levels" rewritten
  (risk read only at `strong` and above; `ai_review_at`; `sign_at`); "Verdicts" replaced by
  "What the brief reports" (strength beside the minimum, findings, observations, settled; it
  recommends nothing).
- `references/purlin_commands.md`: twelve skills (anchor, audit, build, drift, find, init,
  rename, sign, spec, spec-from-code, status, test); the three tables and the syntax block
  per Part A4; each command's one purpose sentence and what it writes.
- `references/commit_conventions.md`: prefix rows `sign(<feature>):`, `sign(batch):`,
  `hold(<feature>):`, `purlin: record for <commit7>`; the signature commit section; the record
  commit paragraphs (records and briefs).
- `references/drift_criteria.md`: role table with `qa.signatures_stale`,
  `qa.review_list_size`, `qa.needs_person`, `eng.code_changed`, `design.design_rules_stale`
  reading the signed cell, `unproved` as `spec == 'drafted'` (lane 1A emits these names; after
  the rebase check them against `scripts/mcp/purlin/drift.py`); config table with `signers`
  and `sign_at`; `> Criteria-Version:` 3 → 4.
- `references/spec_quality_guide.md`: rule tags (risk read at `strong` and above), `@manual`
  (reads `needs a person`; a signer's `--note` clears it), "When a rule is stuck" rewritten as
  one row per cell word with the command that moves it.
- `references/rule_examples.md`: the two "mode" lines rewritten (say "view" or "the loan
  officer flag"), then the file leaves `PENDING_REWRITE`.
- `references/supported_frameworks.md`: word swaps.
- `references/formats/spec_format.md` (wording: the risk tag's meaning, `@manual`, the `@env`
  sentence; the two lines under "Retired tags" that must spell `@on(` end with
  `<!-- retired -->`; no version bump), `proofs_format.md` (wording: `@manual`; no bump),
  `anchor_format.md` (wording: "stales the signatures"; no bump).
- `CLAUDE.md`: the format table (`signature_format.md` row, `record_format.md` row, what
  reads each: `sync_status`, `purlin:sign`, the gate check), the one-home table, the
  `purlin:build`/`purlin:test`/`purlin:audit` delegation sentence, the "Releasing" section
  unchanged.
- `README.md`: the vocabulary paragraph, the gate table (three rows, each with its one
  sentence), the command table (twelve).
- `tools/QA/purlin-qa-report.md` (Steps 2, 3, 5: the summary keys, the buckets, the cells,
  the review list), `tools/PM/purlin-anchor-userstories.md` (L39, L43, L69, L134–144), then
  `bash dev/pack_tools.sh` and commit what it writes.

## Tests and specs

`specs/tools/qa_report.md` RULE-3, RULE-4, RULE-5, PROOF-3; `specs/tools/pm_anchor_userstories.md`
RULE-4, PROOF-4; `specs/mcp/specs.md` PROOF-4; `specs/anchor/upstream.md` RULE-7 wording and
`dev/test_upstream.py`'s matching strings. The tests that prove those specs live in
`dev/test_tools*.py`, `dev/test_upstream.py` and `dev/test_mcp_server.py` (PROOF-4 of specs):
change only the assertions that read your wording; keep every marker aligned.

## Words

Part A1 in full. Never a retired word outside the glossary's retired table.

## Expected red

Anything outside your tests may be red while phases 1 to 4 land. After the rebase only files
another lane names may stay red; name each in your report.

## Acceptance

```
pytest dev/test_vocabulary.py dev/test_upstream.py $(ls dev/test_tools*.py 2>/dev/null)
grep -rn "dev/\|specs/" references/ CLAUDE.md README.md | grep -v "specs/<\|specs/_anchors\|\.purlin\|dev/bump_version\|dev/plans\|dev/run_tests\|dev/test_\|dev/build_report\|dev/capture\|dev/pack_tools\|dev/screenshots"   (CLAUDE.md may name dev/ scripts; references/ may not)
```
