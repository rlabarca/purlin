# Lane 2A: sign, brief, gate check

Plan: `dev/plans/three-levels.md` (in full). Rules: `dev/plans/lanes/tl-_rules.md` (in full).
Worktree `/Users/richlabarca/LocalCode/purlin-wt/2A`, branch `lane/2A` off `three-levels`.
Phase 1 has landed: `signatures.py`, `states.rule_cells`, the schema 5 payload with `cells`,
`bucket`, `meets_gate`, `blocked_by`, `review_list[].why`, and `gate.GATES`.

## What you own (Part B3)

- `scripts/review/approve.py` → `scripts/review/sign.py` (`git mv`, rewrite): `SCHEMA =
  'purlin-signature/1'`, `HOLD_SCHEMA` unchanged; body field `signer`; `gate` at signing;
  `note` null unless `--note`; `--note` allowed on a rule whose strong cell reads `needs a
  person`; `signable()` lists the rules whose signed cell is `unsigned` or `stale`, or whose
  strong cell is `needs a person`; `auto_approve` deleted; the walk (from
  `skills/review/SKILL.md`: read the review list, render each brief, take one of the answers
  sign / add a case / hold / skip) is the no-argument path, `purlin:sign`; `--batch` signs
  everything signable; `<feature> RULE-N --hold "<case>"` writes the hold; messages `sign:
  signer list missing: run purlin:init --gate signed` and `sign: <email> is not on the signer
  list`; under `passed` prints what the gate lacks and what `purlin:init --gate strong` would
  add, exits 2; under `strong` a bare signature prints that signatures are required only under
  `signed`, then writes it when asked. Commit subjects per Part A4: `sign(<feature>): RULE-N
  ...`, `sign(batch): <feature> RULE-N, ...`, `hold(<feature>): RULE-N ...`. Signature files go
  to `specs/<category>/<feature>.signatures/<RULE-N>.<hash8>.<signer-slug>.json`, holds to
  `<RULE-N>.<hash8>.<holder-slug>.hold.json`; the body follows
  `references/formats/signature_format.md` version 3 (lane 1B wrote it; if the code needs a
  field the format lacks, add it there and bump to 4 in the same commit).
- `scripts/review/brief.py`: path `.purlin/briefs/<feature>/<RULE-N>.<hash8>.brief.json`;
  `SCHEMA = 'purlin-brief/2'`; `state`, `verdict`, `reasons` dropped; `observations` (a list
  of sentences, each naming the proofs it concerns) and `settled` (bool) added; `verdict_for`
  and `model_verdict` deleted; `model_prompt` asks the model to state what the test observes
  against what the proof names, one sentence per observation, and to say when it cannot tell;
  it never recommends and never grades; `write_briefs` iterates the rules whose risk is at or
  above `ai_review_at` and whose passed cell counts; `render_brief` prints strength beside
  the minimum, the free-check findings, the observations, and whether it settled. The
  `.brief.txt` rendering, if kept, sits beside the JSON and is gitignored (lane 3 adds
  `.purlin/briefs/**/*.brief.txt` to the template; add it to this repository's `.gitignore`).
- `scripts/review/static_checks.py`: the internal `verdict` names become `result`; plain
  English swaps.
- `scripts/ci/verify_gate.py` → `scripts/ci/gate_check.py` (`git mv`, rewrite):
  `_REQUIRED_STATE` and `_rank` deleted; the check is `rule['meets_gate']` with `blocked_by`
  choosing the section; `--check` prints `Not passed (n)`, `Weak (n)`, `Not signed (n)`, each
  rule with its blocking reason, then the result line; JSON `{gate, min_strength, commit,
  rules, met, not_passed, weak, not_signed, result, exit, signer_list?}`; `PREFIX = 'gate:'`;
  `_SIGNER_LIST_MISSING = '→ signer list missing: run purlin:init --gate signed'`. Every
  caller of the old path (`scripts/run/`, `scripts/init/scaffold.py`'s workflow template,
  `.github/workflows/purlin.yml`, `dev/test_init_e2e.sh`) must still run: change the path
  string where you find it and name the file in your report; lanes 2B and 3 rewrite the rest.
- `.gitignore` of this repository: `.purlin/briefs/**/*.brief.txt`.

## Tests

`dev/test_verify_gate.py` → `dev/test_gate_check.py` (`git mv`; all 29 rewritten to the three
sections and the JSON), `dev/test_brief.py` (L271–296 the model layer, L391, L403, L412,
L448), `dev/test_brief_files.py`, `dev/test_brief_tests_named.py` (L98),
`dev/test_static_checks.py`. Add tests for the walk's four answers, `--note`, `--hold`,
`--batch`, the `passed` exit 2, and the `strong` bare-signature message. Every marker names
the spec's feature and RULE id after your renumbering.

## Specs

- New `specs/ci/gate_check.md` (`# Feature: gate_check`, category `ci`): cut RULE-24..38 and
  their proofs out of `specs/review/signatures.md` (lane 1B left them there for you), renumber
  from RULE-1 and PROOF-1 with `ids.renumber`, rewrite them as the three sections and the
  JSON, the log prefix, the exit codes, the signer-list message. Retarget the markers in
  `dev/test_gate_check.py` to `("gate_check", ...)`. Then delete `specs/review/signatures.md`
  from `PENDING_REWRITE`.
- `specs/review/brief.md`: RULE-12, RULE-13 (verdicts become observations and settled),
  RULE-19, RULE-20 (deleted), PROOF-27, PROOF-28, PROOF-34, PROOF-42; the brief's path.
- `specs/review/static_checks.md`: word swap.
- `specs/skills/skill_review.md` and `skills/review/` are lane 5A's to delete; read the skill,
  do not edit it.

## Words

`sign`, `signature`, `signer`, `hold`, `note`, `the walk`, `brief`, `observation`,
`settled`, `finding`, `gate check`, `Not passed`, `Weak`, `Not signed`, `result`. Never
`verdict`, `approve`, `approval`, `approver`, `verify_gate`, `verify-gate:`.

## Expected red

`dev/test_run_script.py`, `dev/test_records.py`, `dev/test_scan*.py`, `dev/test_consumer_ci.py`
(lane 2B), `dev/test_init_*` and the e2e shell suites (lane 3), `dev/test_purlin_report.py`
(lane 4), `dev/test_skills.py` (lane 5A). Name every red file in your report.

## Acceptance

```
pytest dev/test_gate_check.py dev/test_brief.py dev/test_brief_files.py dev/test_brief_tests_named.py dev/test_static_checks.py dev/test_vocabulary.py
python3 scripts/ci/gate_check.py --check --project-root .   (paste the three sections' headers and the result line)
bash dev/run_tests.sh --fast   (report the summary and the red list)
```
