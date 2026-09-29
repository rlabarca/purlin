# Phase 1 interfaces, as P0b left them

Written by P0b `summary` on 2026-09-28, for the 13 fan-out lanes. This is what the tree holds
after P0b, name by name. Where it differs from `phase1-plan.md` section 2, this file says so
and why, and this file is what the code does. "Today's behaviour" means the behaviour `main`
had before P0b; the lane named owns the change to the final behaviour.

## The summary: `scripts/mcp/purlin/summary.py` (L1 owns it from here)

Constants:

- `KINDS`: a tuple of `(kind, one, many, command)`, in this order. `one` is the words after a
  count of 1, `many` after any other count; `%s` in `to_test_remote` is the systems.

  | kind | one | many | command |
  |---|---|---|---|
  | `no_proof` | `rule to write a proof for` | `rules to write a proof for` | `purlin:spec` |
  | `to_fix` | `rule to fix` | `rules to fix` | `purlin:build` |
  | `no_test` | `rule to write a test for` | `rules to write a test for` | `purlin:build` |
  | `to_test` | `rule to test` | `rules to test` | `purlin:test` |
  | `to_test_remote` | `rule to test on %s` | `rules to test on %s` | `purlin:test --remote` |
  | `to_test_by_hand` | `rule to test by hand` | `rules to test by hand` | `purlin:sign` |
  | `to_audit` | `rule to audit` | `rules to audit` | `purlin:audit` |
  | `to_strengthen` | `rule to strengthen` | `rules to strengthen` | `purlin:build` |
  | `no_scope` | `rule to tie to its files` | `rules to tie to their files` | `purlin:spec` |
  | `to_sign` | `rule to sign` | `rules to sign` | `purlin:sign` |
  | `to_tag` | `the version to tag` | `the version to tag` | `purlin:sign` |

- `KIND_NAMES`: the eleven kind names in that order.
- `FOR_A_PERSON = ('to_test_by_hand', 'to_sign')`: the two kinds the sign walk and drift's QA
  view print.
- `LEFT_TO_DO = 'Left to do:'`, `NOTHING_LEFT = 'Nothing left to do.'`,
  `RELEASE = 'Nothing left to do. Push the tag to release it: git push origin %s'` (`%s` is the
  tag's full name, `signed/<version>`).
- `SYSTEM_ORDER = ('linux', 'macos', 'windows')`.

Functions:

- `rule_kind(rule, gate, here_os, incomplete=None)` -> a kind name or `None`. `rule` is a
  payload rule entry; it reads `cells`, `proofs` and `hand_checked`. `here_os` is `windows`,
  `macos` or `linux`. `incomplete` is truthy when the owning spec names no files. First match
  wins, in the order of the contract table; `out of date` and `not run` with no `missing_env`,
  or with `here_os` among `missing_env`, are `to_test`; `not run` whose `missing_env` is
  non-empty and excludes `here_os` is `to_test_remote`; a strong cell reading neither `strong`
  nor `weak` is `to_audit`.
- `steps(own_rules, gate)` -> `{'passed': p}`, `{'passed': p, 'strong': s}` or
  `{'passed': p, 'strong': s, 'signed': g}`; only the steps up to the gate.
- `sentence(summary, gate)` -> the sentence; reads `summary['rules']` and `summary['steps']`.
- `systems_text(systems)` -> `Linux/Unix`, `macOS`, `Windows` in that order, joined `, ` and
  ` and `. (Not in the contract; `left` uses it.)
- `left(features, gate, here_os, tag=None)` -> `[{'kind', 'count', 'text', 'command'}]`.
  `features` is the payload's feature entries; only rules with `label` `own` are counted (a
  rule with no `label` counts as own). `tag` is the payload's `tag`. `text` carries the count
  and excludes the command: `5 rules to audit`, `1 rule to test on Windows`,
  `the version to tag`. `to_tag` has `count` 1. `to_test_remote` names the union of the
  `missing_env` of the rules counted under it.
- `last_line(left_items, gate, tag=None)` -> `None` while `left_items` is non-empty; else
  `Nothing left to do.`, or at `signed` with a tag, `RELEASE % tag['name']`. (Not in the
  contract; the payload's `last_line` comes from it.)
- `left_lines(payload, kinds=None)` -> `['<text>: <command>', ...]` in the order of
  `payload['left']`, only `kinds` when given. **No indent and no heading.**
- `ending(payload)` -> one string: `summary.sentence`, then `Left to do:` and each
  `left_lines` line indented two spaces, or the `last_line`.

Who calls what today: `payload.build_payload` calls `rule_kind`, `steps`, `sentence`, `left`
and `last_line`. `status.sync_status` ends on `ending(payload)`. Nothing else calls the module
yet: `sign.py` (L5), `drift.py` (L11) and `package.py` (L6) are to call
`ending(payload)` and `left_lines(payload, summary.FOR_A_PERSON)` as the contract says.

The spec is `specs/mcp/summary.md`, eleven rules, 27 proofs; the tests are `dev/test_summary.py`
(26 tests) plus one integration test in `dev/test_states.py` tied to summary PROOF-26.

## The payload: `scripts/mcp/purlin/payload.py`, schema 10

`SCHEMA_VERSION = 10`. Nothing was removed; every schema 9 key is still written.

Top-level keys added:

- `left`: `summary.left(...)` over the feature entries, with `here_os = evidence.host_os()`.
- `finished`: `not left`.
- `last_line`: `summary.last_line(left, gate, tag)`.
- `os_words`: `{'windows': {'word': 'Windows', 'short': 'Win'}, 'macos': {'word': 'macOS',
  'short': 'Mac'}, 'linux': {'word': 'Linux/Unix', 'short': 'Lin'}}`, built from
  `evidence.os_word` and `os_short` over `evidence.PLATFORMS`.

`summary` keys added: `steps` (`summary.steps` over the rules labelled `own`) and `sentence`.

Per-rule keys added (on every entry, `own`, `required` and `global` alike):

- `left`: `summary.rule_kind(entry, gate, here_os, incomplete of the owner)`.
- `hand_checked`: true when any of the rule's signatures has `counts` true, a non-empty
  `note`, and `signatures.is_current(signature, {rule_hash, proof_hash, test_hash,
  audit_hash})`. It does not look at whether a proof is `@manual`.
- `applies_to`: the name of the feature the entry is listed under.
- `code_hash`: `fingerprint.code_hash(project_root, features[applies_to]['scope'] or [])`,
  once per listing feature.
- `machines`: `{os: section['machine']}` over the owner's **current** sections that list a
  result for one of the rule's non-manual proof ids (a proof with `env` only from that
  system's sections), or for the rule's own id when it has no such proof; a section with no
  `machine` is left out, and of two sources for one system the newer `at` wins. Today no
  section carries `machine` (L2 adds it), so every rule reads `{}`.
- `audit.notes`: `[str, ...]` from the audit entry's `notes`, `[]` when it has none; `audit`
  itself is still `null` where no entry answers.

The payload spec is `specs/mcp/states.md` RULE-27 (top level and `summary`) and a new RULE-74
(the per-rule keys); RULE-61 now names `notes`.

## Status and the run

- `status.sync_status(project_root)` prints the header, the table, then (when any spec names
  no files) `incomplete_line`, the anchors lines, the uncommitted spec lines and the warnings,
  then a blank line, then `→ Run: purlin:init --update` when an upgrade is pending, then
  `summary.ending(payload)` as its last lines. Deleted from `status.py`: the headline,
  `bucket_line`, the features/proof-lines line, the queue line, `marked_above_the_gate`,
  `above_the_gate_line`, `_blocking`, `_unaudited`, `next_step`, `_said`, `_summary`,
  `_directives` and the `→ Next:` and `→ Queue:` lines. Kept: `NO_SPECS`, `columns_for`,
  `incomplete_names`, `incomplete_line`, `ARROW`, `DOT`. The table still sorts rows by
  `rollup['met'] - rollup['rules']` (L1 changes this when `met` goes).
- `board.py` is untouched: `headline`, `bucket_line`, `queue_line` and `needs_a_person` still
  exist for their other readers until R.
- `scripts/run/purlin_run.py`: `tests_line`, `gate_line`, `last_lines`, `AUDIT_LINE`,
  `NOTHING_BLOCKS`, `_strength_line`, `NOT_MEASURED_OFF` and `NOT_MEASURED_PASSED` are
  deleted. `project_counts(project_root)` returns only `{'failed', 'short_of_audit'}`, the two
  counts an exit code reads. `--test`, a run that selects nothing and `--ci` end on
  `sync_status`. `--audit` prints, in order: the stale-signature line when there is one
  (`WENT_STALE`, kept for L3 to delete), `Evidence written to ...`, `Evidence committed.` or
  `Evidence unchanged.` under `--commit`, `AI audit: <n> rules read, <s> strong, <w> weak.`
  with its skipped sentence, one line per cause the model could not be reached, a blank line,
  then `sync_status`. Exit codes are unchanged.
- `specs/run/run_script.md`: RULE-11, RULE-45, RULE-48, RULE-54 and RULE-57 are rewritten.

## Signatures: `scripts/mcp/purlin/signatures.py` (L5 owns the final behaviour)

- `BOUND_FIELDS = ('rule_hash', 'proof_hash', 'test_hash', 'audit_hash')`.
- `signed_hash(entry)` -> hex sha256 over seven lines joined by `\n`: `applies_to`,
  `rule_hash`, `proof_hash`, `test_hash`, `code_hash`, `audit_hash`, and `machines` as
  `os=machine` pairs sorted and joined with `,` (a missing field reads as the empty string, a
  `None` machine as the empty string). This is the final hash of contract 2.4; nothing calls it
  yet.
- `is_current(signature, entry)` -> today's behaviour: false for no signature or `entry is
  None`; compares `rule_hash`, `proof_hash`, `test_hash` exactly, and `audit_hash` as strings
  only where `entry.get('audit_hash') is not None`. It does **not** yet compare `signed_hash`
  or machines; L5 replaces it with section 7 item 3.
- `counts(project_root, signature)` -> `(bool, reason)`, today's behaviour: `(False, 'no
  signature')`, `(False, 'the signature is not committed')` with no `path`; below the gate
  `signed` `(True, '')`; at `signed` `(False, 'the signing commit is not signed')` unless the
  last commit touching the file reads `%G?` `G`. The gate is now read inside, from
  `.purlin/config.json` through `config_engine.resolve_config` and `gate.resolve_gate`; the
  `gate` parameter is gone. L5 replaces the body with the `gpgsig` check at every gate.
- `commit_is_signed` is unchanged and still used by `counts` and by `package._signatures`.
- Callers moved to the new shapes: `states._binds` and `states._what_moved` (which passes the
  signature's own `audit_hash` to ask whether only the audit moved), `payload._counted` (its
  cache is keyed on the path alone), `payload._rule_entry` (for `hand_checked`),
  `gate_check.verify`, `purlin_run._audit` (the stale count) and `package._signatures`, and in
  `dev/test_signatures.py` (`TestStale._current`, and PROOF-25's test, which now sets the gate
  with `Project.config(gate=...)` before each `counts` call).
- `key_fingerprint(project_root)` is not written; L5 adds it.

## The rest of the shared interfaces

- `scripts/mcp/purlin/evidence.py`: `OS_WORDS = {'windows': ('Windows', 'Win'), 'macos':
  ('macOS', 'Mac'), 'linux': ('Linux/Unix', 'Lin')}`; `os_word(key)` and `os_short(key)` read
  it, and any key that is not one of the three reads as `linux`. `host_os()` is unchanged: it
  still returns `sys.platform` for an unknown system (L2 changes it to `linux`).
- `scripts/init/update.py`: `SET_UP_BY_095_KEYS = ('test_framework', 'spec_dir', 'pre_push',
  'report', 'digest')` and `set_up_by_095(project_root)` -> bool. False when
  `.purlin/config.json` does not exist (that is the missing-settings case, which a run names on
  its own); true when the file lacks `tests`, carries one of those keys, or a `*.proofs-*.json`
  or `*.receipt.json` sits anywhere under `specs/`. A file that cannot be parsed reads as `{}`
  and so as lacking `tests`. It reads neither the page nor the version stamp. Nothing calls it
  yet (L3 does). This repository reads false; `dev/fixtures/upgrade-0.9.5` reads true.
- `dev/skill_checks.py`: `NOTHING_LEFT = 'Nothing left to do.'`; `undirected_outcome_problems`
  lets exactly one closing outcome without `→` through, the first one containing
  `Nothing left to do.`; a second undirected outcome, that text or not, is still reported.
- `scripts/report/src/app.js`: `var SCHEMA = 10;`. Nothing else in the dashboard changed. The
  built pages are not committed (integration rebuilds them); a locally built page loads a
  schema 10 payload with no notice and no console error, dark, at 1500 and 390 pixels.
- `dev/fixtures/report/{solo,team,regulated}.json`: `schema_version` 10, plus every added key
  above, computed with `summary.py` as if `here_os` were `macos`; each rule's `machines` is `{}`,
  `code_hash` is a stand-in sha256, and `hand_checked` is true only for a rule with a `@manual`
  proof whose strong cell reads `strong`. `dev/test_states.py` (PROOF-82's key-path test) now
  reads `.features[].rules[].machines` as a map keyed by system.

## Test helper modules, frozen for the fan-out

None carries a marker; pytest collects nothing from them. After P0b no test file imports from
a test file another lane owns. The three imports left between test files are within one lane:
`test_upstream_notes` and `test_upstream` from `test_upstream` and `test_drift` (L11), and
`test_purlin_report_board_layout` from `test_purlin_report` (L10).

- `dev/skill_checks.py`: as before, with the exemption above.
- `dev/mcp_project.py`: as before, plus `LEVELS_SPEC`, `ONE_PASSED_SPEC` and
  `_levels_project(gate='signed')`, moved from `dev/test_states.py` (used by it and by
  `dev/test_purlin_report.py`).
- `dev/sign_project.py` (new): moved from `dev/test_signatures.py`: `SIGN_PY`, `FIRST_GATE`,
  `REVIEW_GATE`, `SIGNING_GATE`, `SPEC`, `TEST_FILE`, `TEST_NAMES`, `sha256`, `git`, `write`,
  `Project`, `signing_key`, `CI_COMMITTER`, `CI_EMAIL`, `ci_signing_key`, `commit_as_ci`,
  `sign_one`, `EVERY_RULE_SIGNED`, `signing_project`, `MODEL`, `CRITERIA`, `status`,
  `name_the_model`, `signed_project`, `sign_the_queue`, and the fixtures `signed` and `tagged`;
  and from `dev/test_tag.py`: `_read`, `_Out` (one copy now serves both files) and
  `_signed_project`. `test_tag._sign_every_rule` was the same function as `sign_the_queue`;
  `dev/test_tag.py` and `dev/test_gate_check.py` import it as
  `sign_the_queue as _sign_every_rule`. Importers: `test_signatures`, `test_tag`,
  `test_gate_check`, `test_export`, `test_ai_audit`, `test_ai_audit_tests_named`,
  `test_backing_tests`, `test_failing`, `test_provenance`, `test_report_refresh`.
- `dev/run_project.py` (new): moved from `dev/test_run_script.py`: `REPO`, `RUN_SCRIPT`,
  `_project`, `_spec`, `_pytest_project`, `_run` and the fixture `claude`. Importers:
  `test_run_script`, `test_report_refresh`.
- `dev/reports_project.py` (new): moved from `dev/test_reports.py`: `REPO`, `RUN_SCRIPT`,
  `FIXTURES`, `_write`, `_run`, `_evidence`, `_fixture`, `GO_SPECS`. Its `_run` and `_evidence`
  differ from `run_project`'s, which is why they are two modules. Importers: `test_reports`,
  `test_init_scaffold`.

## Section 2 names P0b did not write

These stay as the plan gives them, for the lane named: 2.4 `key_fingerprint`,
`write_signature`, `signature_path`, format 11 and the final `is_current`/`counts` (L5); 2.5
the evidence `machine` and `hostname` fields, `notes` in the evidence file, the package keys
(L2, L6); 2.6 every run, sign, near-miss and host line and exit code not listed above (L3, L5,
L7, L11); 2.7 the settings keys and `sign.project_version`/`tag_name` (L5, L8, L9); 2.8 the
spec format (L13).

## Where P0b departs from the plan, and why

1. **A cell a rule does not carry counts as reached.** The prompt asked for kinds and steps
   that are right both now, while `[level: ...]` still limits a rule's cells, and after L1.
   `rule_kind` and `steps` read a missing strong or signed cell as reached, so a rule marked
   lower is counted at every step and under no kind, as it meets the gate today, and `purlin:status`
   never sends such a rule to `purlin:audit`, which does not read it. After L1 every rule carries
   every cell up to the gate and the clause never applies. `specs/mcp/summary.md` RULE-8 and
   RULE-9 say so in level-free words ("a cell the rule is not asked for, which it does not
   carry"), and PROOF-27 proves it; **L1 deletes those two clauses and PROOF-27 when it removes
   the marking.** Consequence today: this repository reads `93 are strong. 93 are signed.`,
   which are the 93 rules still marked `[level: passed]`.
2. `left_lines` returns lines with no indent; `ending` adds the two spaces and the heading.
3. `last_line` and `systems_text` are two more public functions in `summary.py`.
4. The per-rule keys went into a new states RULE-74 rather than into RULE-27, which carries the
   top-level and `summary` keys.
5. RULE-48 and RULE-54 were not made one text. RULE-54 carries the audit's line order (one
   `AI audit:` line, then the could-not-audit lines, then the status); RULE-48 keeps only the
   audit's exit code. The line about signatures that went stale still prints, before the
   evidence lines, because RULE-53 is L3's to delete.
6. The test-strength line's deletion made RULE-45 quote lines no longer printed; RULE-45 and
   its proofs PROOF-65, PROOF-66 (split, the `--ci` half is now PROOF-102), PROOF-79 and
   PROOF-80 were rewritten without it.
7. Rules and proofs outside the plan's list quoted lines P0b removed and were rewritten, each
   proof to one case: states RULE-41 (the update line now sits above the summary sentence) with
   PROOF-48, 104, 105; RULE-64 (its next-step half is now summary's `no_scope` kind) with
   PROOF-76, 109, 110; RULE-36's PROOF-43 split into 43, 100 to 103, and PROOF-49 shortened;
   RULE-40's PROOF-47 (no queue line to read); RULE-61's PROOF-73 split into 73, 106, 107 with a
   new PROOF-108 for `notes`; run_script PROOF-5, 7 and 9; reports PROOF-19 split into 19 and a
   new PROOF-25. The old next-step test of states PROOF-76 is now the integration test of summary
   PROOF-26.
8. `counts` keeps today's gate dependence by reading the gate from the settings file, since the
   final shape has no `gate` parameter.
9. `dev/test_init_update.py` PROOF-11's source check asserted that `'report'` never appears in
   `update.py`; contract 2.7 has `set_up_by_095` read that key. The check now asserts the one
   occurrence is in `SET_UP_BY_095_KEYS`; the assertion that the upgrade writes no `report`
   key is unchanged. L9 owns both.
10. `hand_checked` follows L1's definition, which needs a note. The handoff records that the
    owner chose to allow a hand check to be signed with no note. Today such a rule's strong
    cell reads `strong` while its kind is `to_test_by_hand` and it is not counted in
    `pass their tests`. L1 and L5 should settle this against the owner's choice.
11. The two shell suites that read the removed lines, `dev/test_e2e_required_rules.sh` (L3) and
    `dev/init_e2e_walk.sh` (L8), now read the summary sentence and `Nothing left to do.`; their
    lanes rewrite them in full.
12. The status report still prints the line naming specs with no files, which the plan did not
    list for deletion.

## What the lanes should know that the plan does not say

- **L1**: the transitional clause of departure 1; `hand_checked` lives in `payload._rule_entry`;
  the table's sort still reads `met`; `states._what_moved` now builds a copy of the input with
  the signature's own `audit_hash` (it goes with `stale`).
- **L2**: `payload._machines` reads `section['machine']`; once sections carry it, the fixtures
  need `machines` entries, or PROOF-82's key-path test sees `.features[].rules[].machines.*` in
  the builder and not in the fixtures (L10 owns the fixtures).
- **L3**: `project_counts` now returns only `failed` and `short_of_audit`; the audit's line order
  is as above; `set_up_by_095` is ready to call before anything else.
- **L5**: `signed_hash` is the final hash; `is_current` and `counts` are today's behaviour
  behind the final shapes. The PROOF-25 test in `dev/test_signatures.py` switches the gate with
  `Project.config` around each `counts` call.
- **L6**: `package._signatures` calls `is_current(signature, rule)` with the payload rule.
- **L7**: `gate_check.verify` calls `is_current(signature, entry)`; nothing else in it changed.
- **L10**: the fixtures carry every schema 10 key the builder writes today; `left` in the three
  fixtures reads `2 rules to write a test for` (solo); `1 rule to write a test for`,
  `2 rules to strengthen` (team); and six kinds in regulated.
- **L11**: `summary.left_lines(payload, summary.FOR_A_PERSON)` gives drift's QA lines.
- The helper modules above are frozen. A lane that needs more puts it in its own test file.
- The committed built page, `scripts/report/purlin-report.html`, still reads schema 9 until
  integration rebuilds it, so the browser suites (`dev/test_purlin_report*.py`) fail against it:
  run `python3 dev/build_report.py` before them, and `git checkout --
  scripts/report/purlin-report.html` before committing.

## Acceptance numbers at P0b

- `bash dev/run_tests.sh`: 7 suites passed, 0 failed; pytest 1271 passed (1241 before). Added
  53 test ids, removed 23. Removed: the 11 tests of the retired rules (states PROOF-44 twice,
  45 twice, 67, 69, 79, 80, 87, 88, and PROOF-64 in `dev/test_queue.py`), and 12 rewritten under
  new names (run_script's 10 ending and audit tests, now 12; states' schema test, now two; the
  next-step test of states PROOF-76, now summary PROOF-26). Added: `dev/test_summary.py`'s 26;
  14 in `dev/test_states.py` (11 payload tests, the update-line test split off, the `notes`
  test and the summary PROOF-26 integration test); 12 in `dev/test_run_script.py`; reports
  PROOF-25's one.
- `purlin_run.py --test --all`: `Markers: 1169 tied to a test, 0 not tied.`, 35 features,
  exit 0, ending `570 rules. 570 pass their tests. 93 are strong. 93 are signed.`,
  `Left to do:`, `  477 rules to audit: purlin:audit`.
