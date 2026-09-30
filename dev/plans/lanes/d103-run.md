# Lane d103-run

Branch `lane/d103-run` from `d103/base` at `e5f82d0`. Built: `purlin:test --release [<version>]`
(C5's caller), the breaks wherever `cfg.breaks` (C1), the audit's exit 0 on weak and unaudited
rules at every gate, `STRENGTH_LINE = 'Test strength %d%%.'` with no minimum in the reading, the
prompt or the printout, and the review criteria, test skill and audit skill to match.

## Highest lines after the work

| Spec | Highest-Rule | Highest-Proof |
|---|---|---|
| `specs/run/run_script.md` | 94 | 269 |
| `specs/review/ai_audit.md` | 31 | 93 |
| `specs/skills/skill_test.md` | 21 | 50 |
| `specs/skills/skill_audit.md` | 25 | 52 |
| `specs/run/host.md` | 45 (unchanged) | 139 (unchanged) |
| `specs/run/mutation.md` | 37 (unchanged) | 100 (unchanged) |
| `specs/run/evidence_writer.md` | 26 (unchanged) | 89 (unchanged) |
| `specs/run/reports.md` | 31 (unchanged) | 114 (unchanged) |

## Tests

My files whole (`dev/test_{run_script,ai_audit,ai_audit_tests_named,host,mutation_adapters,
evidence_writer,consumer_ci,skill_test,skill_audit}.py`): before 601 passed, 1 skipped; after
590 passed, 13 failed, 1 skipped. Every one of the 13 waits on another lane (below).
`bash dev/run_tests.sh --fast`: 2196 passed, 16 failed, 9 skipped, 1 error. 13 of the failures are
my files' waits below; the other 3 and the error are in files I do not own.

Run with a `PATH` that holds no `claude` (the container has one at `/opt/node22/bin/claude`;
node, npm and npx were linked into a scratch folder instead).

## Rules and proofs

New: run_script RULE-90 (`--release` runs every test, commits, hands on to the release,
PROOF-265), RULE-91 (exits 1 when refused, PROOF-266), RULE-92 (a weak rule does not make
`--audit` exit 1, PROOF-267), RULE-93 (the breaks at `passed`, PROOF-268), RULE-94 (`--release`
beside `--feature`, `--audit`, `--ci` or `--remote` exits 2, PROOF-269); ai_audit RULE-31
(PROOF-93); skill_test RULE-21 (PROOF-50); skill_audit RULE-25 (PROOF-52).

Deleted, with their tests: run_script RULE-45 and PROOF-65 (no breaks at `passed`), PROOF-69
(the audit exits 1 on a weak rule; RULE-92's PROOF-267 is its case now), PROOF-80
(`min_strength` 90), PROOF-174 (the `--ci` case at `strong`, a duplicate of PROOF-102 once the
gate goes); host PROOF-109 (the remote run at `strong`, a duplicate of PROOF-67); skill_audit
PROOF-37 (the `strong` row).

Reworded: run_script RULE-17 (the signature clause goes), RULE-48 (exits on its tests alone),
RULE-52 (exits as its tests do), RULE-73 (no gate, no minimum), RULE-86 (no gate); ai_audit
RULE-8 and RULE-17 (no minimum); skill_audit RULE-5, RULE-6, RULE-9; host RULE-20 (`passed`).
Proofs reworded: run_script 12, 15, 16, 17, 59, 66, 68, 73, 74, 75, 77, 78, 79, 81, 82, 83, 86,
87, 99, 100, 101, 105, 108, 109, 125, 159, 161, 176, 183, 184, 185, 186, 213, 227, 259, 264;
ai_audit 1, 2, 4, 8, 11, 12, 13, 27, 29, 39, 48, 49, 51 to 54, 63, 72, 73, 77, 79, 80, 84 to 89,
91, 92 (the gate `strong` dropped; 8, 11, 89 and 92 lose the minimum); host 84, 87, 128;
mutation 67; evidence_writer 37, 54, 57, 58; skill_audit 5, 6, 38, 39.

## Calls made

- **A proof that named the gate `strong` for no reason of its own now names no gate**; its test
  runs at `signed` where it needs the breaks or the strong cell (both hold there before and
  after lanes `settings` and `counting` merge) and at `passed` or `signed` otherwise. Section 4
  asks for `passed` with `mutation_engine` set in `specs/run/{host,mutation,evidence_writer,
  reports}.md`; RULE-93's PROOF-268 is the one proof of the breaks at `passed`. Where a proof's
  case depends on the gate (PROOF-100, 101, 105, 108, 128) it names the gate.
- **Under `--release` the status table and its last line print before the release's lines**, as
  after any `--test --commit`, so a passing release reads `Nothing left to do. To release a
  version: purlin:test --release` and then `Evidence package committed`, `Tagged ...` and
  `summary.RELEASE`. Printing the status after the release instead would print `RELEASE`
  twice. Left for the owner.
- **`--release` is refused beside `--feature`, `--audit`, `--ci` or `--remote`** (exit 2), and
  accepted beside `--test`, `--all`, `--commit` and `--arm-timeout`.
- run_script RULE-1 (the command line names one of `--test`, `--audit`, `--ci`) is left as
  written; RULE-90 and RULE-94 say what `--release` is.
- PROOF-79 keeps the strong cell's reason `no mutation score measured` with `mutation_engine`
  `none`; C2 does not list that reason. Lane `counting` decides it.
- The test skill's `Exit codes:` line is unchanged (skill_test RULE-8 quotes it word for word);
  the release's exit 1 is said in the sentence after it.
- `dev/fixtures/consumer-ci/tests/test_greeting.py`'s docstring still says a proof "reaches
  `strong`"; no lane owns the file.

## Words chosen that section 7 does not give

- The refusal: `purlin: --release runs every test here and commits it, so it takes no --feature, --audit, --ci or --remote. Run purlin:test --release.`
- The script's usage line: `purlin_run.py --release [VERSION] [--arm-timeout SECONDS] [--project-root DIR]`.
- `references/review_criteria.md`: the section `What the audit holds back`, opening `Nothing.
  The AI audit and the breaks are tools at either gate: purlin:audit runs them when a person
  asks, and neither a gate nor a release waits on them.`; `A weak finding does not stop a
  release.`; the sign-off walk's stop at a weak or unaudited rule, in C8's words.
- The audit skill: `The audit and the breaks are tools at either gate: nothing waits on them,
  and a weak rule never stops a release.`; `What the audit found never sets the code: a weak
  rule, or one the model could not be reached for, is listed, not failed.`; the gate table's
  rows `Runs the tests, the breaks where mutation_engine is not none, and the AI audit; what
  they find holds nothing back` and `The same as passed. Evidence either source wrote counts
  here too; the sign-off walk shows what the audit found`.
- The test skill: the `--release` sentence after `Exit codes:`, and the closing rows
  `→ Run: purlin:test --release`, `A line beginning No release:` → `→ Run: <the command it
  names>, or say what git refused`, and `→ Run: git push origin <tag>`.

## Failures in files I do not own

Each fails the same way with this lane's `scripts/`, `references/` and `skills/` put back to
`e5f82d0`, so none comes from this lane; each reads as a Linux container:

- `dev/test_signatures.py::TestTheMachines::test_a_new_system_ends_nothing` and
  `::test_a_system_it_names_that_is_gone_ends_it`: the machines read `linux` where the test
  expects `macos` (lane `signoff` rewrites the file).
- `dev/test_tag.py::TestTheTag::test_the_tag_is_signed_with_the_key_the_settings_name`: the tag
  object's output differs on this git (lane `release` rewrites the file).
- `dev/test_states.py::TestStatusTable::test_the_table_and_the_dashboard_show_the_same_cells`:
  an error at setup (lane `counting`'s file; the dashboard fixture it needs is a browser's).

## Tests that fail only because another lane has not merged

- Lane `release` (`scripts/export/release.py`): run_script PROOF-265, PROOF-266. Checked against
  an uncommitted stand-in `release.py` that tags and refuses: both pass, and the deliberate
  break (`--release` skipping `run_release`) fails both; restored with
  `git checkout -- scripts/run/purlin_run.py`, stand-in deleted.
- Lane `counting` (C2, C3): run_script PROOF-66 (reason `strength 80%`), PROOF-86, PROOF-87,
  PROOF-100, PROOF-101, PROOF-105, PROOF-107, PROOF-108.
- Lane `settings` (C1, the consumer-ci fixture): run_script PROOF-268 (the breaks at `passed`);
  host PROOF-84 and PROOF-87 in `dev/test_consumer_ci.py` (the fixture's gate `passed`).
