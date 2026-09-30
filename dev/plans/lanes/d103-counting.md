# Lane `counting`, decision 103

Built C2, C3 and C4 on `lane/d103-counting`, from `d103/base` at `e5f82d0`, and deleted C12's parts in
the files this lane owns. I ran it on Linux in a cloud session, with no real `claude` on `PATH`
and no network service.

## Highest lines after the work

| Spec | `> Highest-Rule:` | `> Highest-Proof:` |
|---|---|---|
| `specs/mcp/states.md` | 109 (was 105) | 264 (was 259) |
| `specs/mcp/summary.md` | 19 (was 16) | 47 (was 41) |
| `specs/skills/skill_status.md` | 12 (was 11) | 36 (was 35) |
| `specs/instructions/purlin_output.md` | 3 (unchanged) | 6 (unchanged) |

New, with the numbers section 4 gives:

- states RULE-106 (PROOF-260, PROOF-261), RULE-107 (PROOF-262), RULE-108 (PROOF-263), RULE-109
  (PROOF-264).
- summary RULE-17 (PROOF-42, PROOF-43), RULE-18 (PROOF-44, PROOF-45, PROOF-46), RULE-19
  (PROOF-47).
- skill_status RULE-12 (PROOF-36).

Every proof written or rewritten holds one case in at most 60 words and has a marked test of its
own. No number is reused.

## Deleted and reworded

### `specs/mcp/states.md`

- Rules deleted (18): 12, 18, 19, 20, 21, 22, 47, 63, 73, 74, 75, 83, 86, 88, 100, 101, 103,
  104. Their proofs and tests went with them.
- Proofs deleted (57): 6, 14, 22, 23, 24, 25, 26, 56, 72, 75, 78, 83, 93, 94, 111, 114, 115, 124,
  125, 127, 131, 132, 133, 137, 138, 143, 144, 145, 146, 147, 157, 174, 183, 184, 188, 190, 192,
  194, 197, 198, 200, 202, 217, 222, 226, 227, 237, 244, 245, 246, 247, 251, 252, 253, 254, 255,
  256.
  - Each proof held at the gate `strong` whose twin at `passed` or `signed` already stood was
    deleted rather than moved: 6, 78, 83, 174, 183, 184, 188, 190, 192, 194, 198, 200, 202.
- Rules reworded (17): 4, 11, 13, 15, 16, 23, 25, 27, 28, 36, 59, 66, 77, 78, 81, 93, 102.
- Proofs reworded (51): 13, 15, 17, 18, 19, 27, 29, 31, 32, 43, 50, 51, 52, 53, 54, 68, 70, 71,
  82, 91, 96, 97, 103, 116, 120, 121, 122, 123, 139, 140, 142, 158, 159, 160, 161, 165, 166, 171,
  172, 196, 208, 209, 210, 211, 212, 213, 215, 224, 235, 240, 241.
  - Most of these only move a proof from the gate `strong` to `passed`.
- The description no longer names signatures.

### `specs/mcp/summary.md`

- Rules deleted (2): 11 (`the version to tag`), 15 (`to_confirm`).
- Rules reworded (8): 1, 2, 3, 4, 5, 7, 8, 9.
- Proofs deleted (15): 1, 3, 9, 13, 14, 19, 21, 24, 25, 26, 30, 31, 32, 38, 39.
  - summary PROOF-26's test lived in `dev/test_states.py` and went with it.
- Proofs reworded (11): 5, 6, 7, 8, 10, 11, 12, 15, 16, 18, 20.
- The description no longer names the sign walk.

### `specs/skills/skill_status.md`

- RULE-8, PROOF-23 and PROOF-24 were reworded, beyond the RULE-12 section 4 names. They quoted
  the closing table's bare `Nothing left to do.` row and `the version to tag`, which C3 retires.
  The table now has no row without a directive.

### `specs/instructions/purlin_output.md`

- Unchanged. No proof quoted a deleted line.

## Tests

- My own files, run whole (`dev/test_states.py`, `dev/test_summary.py`,
  `dev/test_backing_tests.py`, `dev/test_failing.py`, `dev/test_purlin_output.py`,
  `dev/test_skill_status.py`):
  - Before, on `d103/base`: 279 tests, 276 passed and 3 skipped.
  - After: 221 tests, 214 passed, 4 failed and 3 skipped.
  - Each of the 4 failures waits for another lane (listed below).
  - The 3 skips are the Python 3.9 proofs of `purlin_output`; the container has no 3.9.
- `bash dev/run_tests.sh --fast`: 1954 passed, 179 failed, 20 errors, 9 skipped.
  - 4 of the failures are in my files and wait for other lanes (below).
  - Every other failure and error is in a file I do not own (next-to-last section).
- The browser test needs `playwright==1.56.0` in the `.venv` to match
  `/opt/pw-browsers/chromium-1194`. It was installed only in the local `.venv`; nothing about it
  is committed.

## Deliberate break

- I added `to_strengthen` to `summary.BLOCKING`, with `/opt/node22/bin` (where the container's
  `claude` sits) taken off `PATH`.
- Two tests failed:
  - summary PROOF-47, `test_a_weak_rule_is_to_strengthen_and_blocks_no_release`.
  - states PROOF-262, `test_a_weak_audit_stops_neither_the_passed_cell_nor_a_release`.
- I restored the file with `git checkout -- scripts/mcp/purlin/summary.py`, and both tests pass
  again.

## Tests that fail only because another lane has not merged

- **Lane `dashboard`**: `dev/fixtures/report/*.json` still read schema 12, carry `cells.signed`,
  `signatures`, `min_strength` and the team fixture at the gate `strong`, and `board.js` still
  shows `Strong` by gate. These wait for it:
  - states PROOF-82, `test_the_fixtures_carry_exactly_the_keys_the_builder_writes`.
  - states PROOF-96, `test_every_fixture_has_the_key_set_the_builder_writes`.
  - states PROOF-58, `test_the_table_and_the_dashboard_show_the_same_cells`.
  - The fixture tests now read each fixture's own gate instead of a fixed list of three, so they
    hold whichever gate the dashboard lane gives the team sample.
- **Lane `settings`**: `NOT_A_GATE` still reads `passed, strong or signed`. This test waits for it:
  - states PROOF-224, `test_a_gate_not_accepted_is_read_as_passed_with_its_fix`.

## Calls left, and calls made where the contract is silent

1. **Rule entry keys.** The payload rule entry drops `applies_to`, `code_hash` and `audit_hash` as
   well as C4's list.
   - A signature was made over them and nothing else reads them.
   - `audit_hash` came from `signatures.audit_hash`, which C6 deletes.
   - C4 names them neither kept nor gone.
   - `scripts/export/package.py` still names `code_hash` and `audit_hash` in `LOCKED`, the
     signature's hashes, which lane `release` deletes.
2. **The summary's counts.** `summary` keeps the counts it already carried beside C4's
   `{rules, steps, audit, sentence}`: `features`, the four buckets, `strong`, `weak`,
   `not_audited`, `manual`, `incomplete`, `proofs`, `proofs_without_test` and
   `proofs_without_test_ids`. C4 reads as the keys it adds, not as the whole object.
3. **Where a strength shows.** The strong cell shows `strength <p>%` only while `mutation_engine`
   is not `none`, as states RULE-13 already said for a strength left behind. A verdict of
   `undecided` still reads `weak` (RULE-89 kept).
4. **Board and rollup signatures.**
   - `board.columns_for(gate, proofs, audited)` and `board.row_cells(name, rollup, gate, proofs,
     audited)` take `audited`, `board.shows_strong(summary.audit)`'s answer.
   - The `Strong` column shows at either gate where the audit found a rule strong or weak.
   - `board.signed_cell`, `signed_met` and `SIGNED_COLUMNS` are deleted.
   - `scripts/report/src/board.js` mirrors these (lane `dashboard`).
   - `states.feature_rollup(rule_results, test_strength)` and `states.project_rollup(rollups)`
     take no gate, as `cells_for` and `bucket_keys` do.
5. **The tag reader.** `payload.signed_tag` is now `payload.release_tag`. It lists
   `passed/*` and `signed/*` on HEAD together; at the same version `signed/` sorts after `passed/`
   and wins.
6. **`test_hash_kind`.** It moved into `payload.py` as `payload.test_hash_kind(proofs)` with
   `payload.TEST_HASH_KINDS`, as C6 asks.
7. **The unreadable-settings proof.** states PROOF-212 now writes `{"gate": "passed",` where it
   wrote `{"gate": "strong",`. The error line it proves is unchanged.

## Words chosen that section 7 does not give

- The status skill, Step 2: `` `Strong` only where the audit found a rule strong or weak. It is the
  dashboard's board as text. ``
- The status skill, Step 2: `` `Strong` reads `<n> of <rules>` the audit found strong, then
  `· <strength>%` where measured. ``
- The status skill, Step 3: `The sentence counts the rules that pass their tests, then what the
  audit found where it read any.` and `When nothing is left, one line naming the release step
  follows the sentence instead.`
- The status skill, renumbering (RULE-12):
  ``Where a warning says a number is written twice, follow `Renumbering` in `skills/spec/SKILL.md`.``
- The status skill's closing table, the signed row: `` `... purlin:test --release, then
  purlin:sign` `` with `` `→ Run: purlin:test --release`, then `purlin:sign` ``.
- The status skill's closing table, the release row: `` `→ Run: git push origin <tag>` ``.
- `states.py` keeps `no mutation score measured` as the one reason of a strong cell with nothing
  measured and the breaks off.

## Failures in files I do not own

Every one of these is something another lane's contract removes or rewrites. None is a fault
in the contracts C2 to C4 as built.

- **`summary.ended_lines` / `summary.FOR_A_PERSON` are gone (C3), still called by other files.**
  - `scripts/mcp/purlin/drift.py` (lane `drift`) still calls both.
  - Failing through it: `dev/test_drift.py` (74), `dev/test_security.py` (4, its git argv
    checks run drift), `dev/test_mcp_server.py` `test_drift_answers_json` (1).
  - `scripts/review/sign.py` (lane `signoff`) still calls `FOR_A_PERSON`.
  - Failing through it: `dev/test_signatures.py` (55), `dev/test_tag.py` (7 failed, 20 errors),
    `dev/test_report_refresh.py` `test_a_signature_writes_the_data_file` (1).
  - A few in these files also read `cells.signed` or a deleted kind.
- **Retired kinds, the signed cell, `min_strength` or the old sentence.**
  - `dev/test_export.py` (12, lane `release`).
  - `dev/test_run_script.py` (13, lane `run`; for example a strength under the minimum).
  - `dev/test_init_scaffold.py` (7, lane `settings`; the three-gates end-to-end tests).
- **Quoted lines.** `dev/test_purlin_docs.py` `test_the_confirmed_runs_lines_are_printed_by_it`
  (1, lane `docs` and `words`). `README.md:69` and `docs/getting-started.md:125` quote the run
  ending on `Nothing left to do.` alone. It now reads
  `Nothing left to do. To release a version: purlin:test --release`.
