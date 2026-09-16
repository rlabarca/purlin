# Lane 1A: states and payload

Plan: `dev/plans/three-levels.md` (in full). Rules: `dev/plans/lanes/tl-_rules.md` (in full,
especially "The chain, as the fixtures pin it"). Worktree
`/Users/richlabarca/LocalCode/purlin-wt/1A`, branch `lane/1A` off `three-levels`. Lane 1B has
landed on `three-levels`: `scripts/mcp/purlin/signatures.py` exists with `signatures_dir`,
`load_signatures`, `is_current`, `counts`, `signer_slug`, `test_hash_kind`, `design_hash`.

## What you own (Part B2)

- `gate.py`: `GATES = ('passed', 'strong', 'signed')`, `DEFAULT_GATE = 'passed'`; `_DERIVED`
  per Part A3 with `sign_at` (`None`, `None`, `'medium'`) and `breaks` (`False`, `True`,
  `True`); `GateConfig` slot `signers` replaces `approvers`; `tags_required` dropped;
  `RETIRED_KEYS` gains `approvers`; an unrecognised `gate` falls back to `passed` with the
  existing warning shape. `min_strength` is `None` under `passed` (unused), 70 at `strong`,
  80 at `signed`; `ai_review_at` `never` / `high` / `medium`.
- `states.py`: rewrite. `rule_cells(inp, cfg)` returns `{spec, cells, bucket, meets_gate,
  blocked_by, flags}` exactly as the fixtures shape them (`tl-_rules.md` items 1 to 12).
  `feature_rollup` and `project_rollup` count buckets, flags and `met`. No `STATE_ORDER`, no
  `_rank`, no `lowest`, no brief-as-state, no state constants. Inputs are today's plus
  `sign_at`, the brief's `settled` and `observations`. Keep `_record_verdict` renamed
  `_record_passes`, `_failing_where`, `_local_passes`. The module docstring is the chain of
  Part A2 in prose.
- `payload.py`: schema 5 per Part B1; `SCHEMA_VERSION = 5`; the docstring shows the new
  shape; `_counting` keyed on the new gate names; review entries only when
  `cfg.gate != 'passed'`; briefs read from `.purlin/briefs/<feature>/<RULE-N>.<hash8>.brief.json`
  (schema `purlin-brief/2`, fields `observations` and `settled`; lane 2A writes them, you read
  them, and a brief missing or for other hashes is null); `signatures` (paths) replaces
  `approvals` on a feature; `summary` replaces `states` and `project_rollup`. Gone: everything
  Part B1 lists under "Gone".
- `records.py` (mcp): `counts_under(gate, label)` keyed on the new values only: under
  `passed` every label counts; under `strong` and `signed` only `ci`.
- `checks.py`: `blocks_proof_ready` becomes `blocks_ready`; wording.
- `status.py`: the status table per Part A6: columns `Feature | Rules | Spec | Tests | Run`,
  then `| Strength | Strong` at `strong`, then `| Signed` at `signed`; summary line
  `<met> of <rules> meet the gate <gate>`; one `→ Next:` line from `_directives` per Part B2.
- `drift.py`: `qa.signatures_stale`, `qa.review_list_size`, `qa.needs_person`,
  `eng.code_changed`; `design.design_rules_stale` reads the signed cell; `unproved` is
  `spec == 'drafted'`. Lane 5B rewrites `references/drift_criteria.md` to the same names;
  put the row names you emit in your report.
- `server.py`: tool descriptions say "the spec status and the cells of every rule".
- `ids.py`: everything except `_signature_paths` (lane 1B's).
- `frameworks.py` and `specs.py`: word swaps only (`recorded` in plain English; the `@on(`
  detection lines in `specs.py` end with `  # retired`, see `MARKED` in
  `dev/test_vocabulary.py`).

## Tests

`dev/test_mcp_server.py` (the 41 state functions, the status-table test near L1075, the
gate-defaults test near L580, the counts-under test near L652; the `@on(` lines near L230 and
L238 end with `  # retired`), `dev/test_review_list.py`, `dev/test_backing_tests.py`,
`dev/test_failing.py`, `dev/test_drift.py` (near L638, L847), `dev/test_scan.py` (L148, L173
only; lane 2B owns the rest and its `PENDING_REWRITE` entry), `dev/test_schema_spec_format.py`
and `dev/test_schema_proof_format.py` (the lines that feed `@on(` or `platform` to the parser
end with `  # retired`). Add a test that loads each of the three fixtures and asserts the
payload builder's output for an equivalent project has the same key set per rule, per cell,
per rollup and per summary (the fixtures are the contract; a key you add must be added to the
fixtures too, and you say so in your report).

## Specs

Rewrite `specs/mcp/states.md` in full: subject "the spec status and the three evidence
levels of a rule"; one rule per cell word and its reasons, one per bucket, the flags, the
review list membership, `meets_gate` and `blocked_by`. Section-rewrite `specs/mcp/drift.md`
RULE-7 and RULE-14; `specs/mcp/server.md` PROOF-9; `specs/_anchors/schema_proof_format.md`
RULE-1 and RULE-3; `specs/_anchors/schema_spec_format.md` RULE-4. Every marker in the tests
follows the renumbering.

## Words

Spec status `drafted` / `ready`; cells `passed` / `strong` / `signed`; the words each cell can
read (Part A2); `source` `ci` / `developer` / `local`; `current`; `counts`; `bucket`; `met`;
`meets the gate`; `blocked by`. Never a state name from the old ladder.

## Expected red

`dev/test_purlin_report.py` (lane 4), `dev/test_init_scaffold.py`, `dev/test_init_update.py`,
`dev/test_init_e2e.sh`, `dev/test_e2e_required_rules.sh` (lane 3), `dev/test_verify_gate.py`,
`dev/test_brief*.py` (lane 2A), `dev/test_run_script.py`, `dev/test_records.py`,
`dev/test_scan*.py`, `dev/test_consumer_ci.py` (lane 2B), `dev/test_skills.py` (lane 5A).
Keep those files importable where your renames touch them (change an import line, not the
logic). Name every red file in your report.

## Acceptance

```
pytest dev/test_mcp_server.py dev/test_review_list.py dev/test_backing_tests.py dev/test_failing.py dev/test_drift.py dev/test_schema_spec_format.py dev/test_schema_proof_format.py dev/test_vocabulary.py
python3 scripts/mcp/purlin/status.py --project-root .   (prints the new table; paste it)
bash dev/run_tests.sh --fast   (report the summary and the red list)
```
