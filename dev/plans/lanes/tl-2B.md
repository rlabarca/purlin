# Lane 2B: run and scan

Plan: `dev/plans/three-levels.md` (in full). Rules: `dev/plans/lanes/tl-_rules.md` (in full).
Worktree `/Users/richlabarca/LocalCode/purlin-wt/2B`, branch `lane/2B` off `three-levels`.
Phase 1 has landed: `signatures.py`, `states.rule_cells`, the schema 5 payload, `gate.GATES`
with `cfg.breaks` and `cfg.sign_at`. Lane 2A works in parallel on `scripts/review/sign.py`,
`brief.py` and `scripts/ci/gate_check.py`; code against those names (`brief.write_briefs`,
`brief.SCHEMA = 'purlin-brief/2'`, briefs under `.purlin/briefs/<feature>/`,
`scripts/ci/gate_check.py`) and, until 2A lands on `three-levels`, keep your tests of the
CI review arm at the boundary (patch `_ci_review`'s collaborator) rather than importing 2A's
modules. Rebase onto `three-levels` and run the whole acceptance again when 2A is there.

## What you own (Part B3)

- `scripts/run/purlin_run.py`: `--record` skips the breaks when `cfg.breaks` is false (under
  `passed` the record carries `test_strength: null` and prints `strength n/a: the gate is
  passed`); a local `--record` under `strong` or `signed` prints its strength as a preview and
  the line `this record does not count under <gate>: only a CI record counts`; `_ci_review`
  writes briefs only (no signature file, ever; the `.ci.json` path is deleted); the record
  commit carries records and briefs, subject `purlin: record for <commit7>`; `build_record`
  writes the new gate value; `RECORD_SCHEMA = 'purlin-record/2'`, `schema_version` 2;
  `_VALIDATED_PREFIX` → `refs/tags/record/` and `--tag <name>` writes `record/<name>`.
- `scripts/run/records.py` (docstrings and the record body), `scripts/run/ci.py` and
  `scripts/run/remote.py` (words; `remote.py`'s docstring names `purlin:audit --remote`),
  `scripts/run/mutation/__init__.py` (one plain-English swap).
- `scripts/report/scan.py`: prints the bucket lines and the review list per Part A6
  (`<met> of <rules> rules meet the gate <gate> · <failing> failing`, one line per bucket,
  then `<n> rules need a person` and the rows).
- `dev/manual/check_qa_tool.py`, `dev/manual/check_spec.py`, `dev/manual/README.md`: the new
  words and gate values.
- `references/formats/record_format.md` → `> Format-Version: 2` in the same commit as the
  record change: the `gate` enum `passed strong signed`, `"schema": "purlin-record/2"`,
  `test_strength` null under `passed`, the `source` of a record (`ci`, `developer`, `local`)
  and how the payload reads it, the Freshness section saying `code changed`, the record
  commit's contents (records and briefs), the `record/<name>` tag. No `validated/`, no
  auto-approval, no approval.

## Tests

`dev/test_run_script.py` (L312, L668, L693, L719, L805, L826, L853 and the gate-value sites),
`dev/test_records.py` (L454, L515 and the gate-value sites; no `validated/`),
`dev/test_scan_review_list.py`, `dev/test_scan.py` (everything lane 1A did not: 1A rewrote
the state assertions at the old L148 and L173), `dev/test_consumer_ci.py` (L277, L318; the
fixture's gate is `strong` since phase 0, so the consumer run exercises the breaks and a CI
record). Add a test that `--record` under `passed` runs no breaks and writes `test_strength`
null, and one that a local `--record` under `strong` prints the does-not-count line. Every
marker names the spec's feature and RULE id after your renumbering.

## Specs

`specs/run/records.md` RULE-5, RULE-14, RULE-21, RULE-25, PROOF-14, PROOF-20, PROOF-28,
PROOF-29; `specs/run/run_script.md` RULE-17, RULE-20, RULE-42, PROOF-11, PROOF-17, PROOF-20,
PROOF-61, plus one new rule: under `passed` a `--record` runs no breaks and writes strength
null. `specs/run/mutation.md`: word swap.

## Words

`record`, `audit`, `the breaks`, `test strength`, `source`, `current`, `code changed`,
`brief`, `record commit`. Never `verify`, `validated/`, `auto-approval`, `approval`,
`approved`, `recorded` (say "wrote", "the record holds").

## Expected red

`dev/test_init_*` and the e2e shell suites (lane 3), `dev/test_purlin_report.py` (lane 4),
`dev/test_skills.py` (lane 5A), and lane 2A's files until 2A lands. Name every red file in your
report.

## Acceptance

```
pytest dev/test_run_script.py dev/test_records.py dev/test_scan.py dev/test_scan_review_list.py dev/test_consumer_ci.py dev/test_vocabulary.py
python3 scripts/report/scan.py --project-root .   (paste the first ten lines)
bash dev/run_tests.sh --fast   (report the summary and the red list)
```
