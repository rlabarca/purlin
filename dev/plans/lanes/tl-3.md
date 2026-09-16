# Lane 3: init and update

Plan: `dev/plans/three-levels.md` (in full). Rules: `dev/plans/lanes/tl-_rules.md` (in full).
Worktree `/Users/richlabarca/LocalCode/purlin-wt/3`, branch `lane/3` off `three-levels`.
Phase 1 has landed: `gate.GATES = ('passed', 'strong', 'signed')`, `GateConfig.signers`,
`cfg.sign_at`, `cfg.breaks`, the schema 5 payload. Lane 2A renames `scripts/ci/verify_gate.py`
to `scripts/ci/gate_check.py` in parallel; write the new path everywhere you emit it.

## What you own (Part B4)

- `scripts/init/scaffold.py`: `GATE_CHOICES` are the three new answers, each with its one
  sentence from Part A3 (what CI requires before merge) and its derived defaults;
  `SIGNER_QUESTION` replaces the approver question and is asked only under `signed`;
  `write_config` writes `signers` under `signed` and never `approvers`; `_BRANCH_RULES` per
  Part A3 (GitHub: require a pull request and the `purlin` check with the Actions app the
  only bypass; restrict `.purlin/records/**` and `.purlin/briefs/**` to the Actions app; no
  force push, no deletion; under `passed` only the third; Azure: the build service alone
  holds Contribute on the two paths); the readmes it writes (`.purlin/records/README.md`, the
  briefs directory readme if one is written); `print_signed` replaces `print_approved`;
  `--gate` choices from `gate_module.GATES`; the workflow it writes runs
  `purlin_run.py --all --record --ci` as today and names `scripts/ci/gate_check.py`.
- `scripts/init/update.py`: the 0.9.5 → 0.10.0 migration lands a project straight on the new
  layout: gate values `tested`→`passed`, `recorded`→`strong`, `approved`→`signed`;
  `approvers`→`signers`; no approvals directory is created, read or migrated; `GATE_QUESTION`
  in the new words; the retired-spelling table (`# retired` rows) gains every retired name
  from decision 15 (`approvers`, `verify_gate`, `verify-gate.yml`, `validated/`, the old gate
  values). No migration from the intermediate 0.10-dev layout and no test for one.
- `templates/config.json`: `"gate": "passed"`. `templates/gitignore.purlin`: add
  `.purlin/briefs/**/*.brief.txt`.

## Tests

`dev/test_init_scaffold.py` (the gate and signer functions at L196–L492, L587, L695; the
fixture `--gate` arguments), `dev/test_init_update.py` (L333–L420; the 0.9.5 fixture lands on
the new layout; every test that used the deleted `upgrade-0.10-dev` fixture is deleted with
`V010` and `LAYOUTS` reduced to the 0.9.5 layout), `dev/test_init_e2e.sh` (the three-gate walk
in the new words, `set_signers`, `scripts/ci/gate_check.py`),
`dev/test_e2e_required_rules.sh` (L165–L193), and the three e2e shell fixtures that write
`{"gate": "tested"}`, now `passed`: `dev/test_e2e_anchor_authority.sh`,
`dev/test_e2e_external_refs.sh`, `dev/test_e2e_feature_scoped_overwrite.sh`. Every marker
names the spec's feature and RULE id after your renumbering.

## Specs

`specs/init/scaffold.md` RULE-2, RULE-3, RULE-4, RULE-10, RULE-11, RULE-12, RULE-17, RULE-36,
PROOF-35, PROOF-41; `specs/init/update.md` RULE-10, RULE-12, PROOF-10, PROOF-12; and every
other rule in those two specs that names an old gate value, `approvers` or the 0.10-dev
layout.

## Words

Gate values `passed` / `strong` / `signed`; `signers`, `signer list`; `sign_at`;
`min_strength`; `ai_review_at`; `the breaks`; `.purlin/briefs/`; `gate check`. Never
`tested`, `recorded`, `approved`, `approvers`, `verify_gate`, `verify-gate`.

## Expected red

`dev/test_purlin_report.py` (lane 4), `dev/test_skills.py` (lane 5A), lane 2A's and 2B's
files until they land (`dev/test_gate_check.py` or `dev/test_verify_gate.py`,
`dev/test_run_script.py`, `dev/test_records.py`, `dev/test_consumer_ci.py`). The e2e shell
suites drive `purlin_run.py` and the gate check, so they may stay red until 2A and 2B land;
rebase onto `three-levels` when they do and run them again before you report. Name every red
file in your report.

## Acceptance

```
pytest dev/test_init_scaffold.py dev/test_init_update.py dev/test_vocabulary.py
bash dev/test_init_e2e.sh
bash dev/test_e2e_required_rules.sh
bash dev/run_tests.sh   (the full sweep; report the summary and the red list)
```
