# Lane `settings`, decision 103

Built C1, C15, C16 and the settings tool on `lane/d103-settings`, from `d103/base` at `e5f82d0`.
I ran it on Linux in a cloud session, with no real `claude` and no network service.

## Highest lines after the work

| Spec | `> Highest-Rule:` | `> Highest-Proof:` |
|---|---|---|
| `specs/mcp/config_engine.md` | 18 (was 15) | 44 (was 40) |
| `specs/mcp/server.md` | 32 (was 31) | 163 (was 162) |
| `specs/mcp/specs.md` | 21 (unchanged) | 43 (unchanged) |
| `specs/init/scaffold.md` | 78 (was 75) | 170 (was 166) |
| `specs/init/update.md` | 49 (was 46) | 161 (was 158) |
| `specs/skills/skill_init.md` | 85 (unchanged) | 96 (unchanged) |

New, with the numbers section 4 gives: config_engine RULE-16 (PROOF-41), RULE-17 (PROOF-42,
PROOF-43), RULE-18 (PROOF-44); server RULE-32 (PROOF-163); scaffold RULE-76 (PROOF-167),
RULE-77 (PROOF-168, PROOF-169), RULE-78 (PROOF-170); update RULE-47 (PROOF-159), RULE-48
(PROOF-160), RULE-49 (PROOF-161). Each proof written or reworded holds one case in at most 60
words and has a marked test of its own. `specs/mcp/specs.md` needed no change: none of its proofs
names `strong` or `min_strength`.

## Tests

- My own files, run whole (`dev/test_config_engine.py`, `dev/test_mcp_server.py`,
  `dev/test_specs_reader.py`, `dev/test_init_scaffold.py`, `dev/test_init_update.py`,
  `dev/test_skill_init.py`):
  - Before, on `d103/base`: 415 passed, 3 skipped.
  - After: 406 passed, 8 failed, 3 skipped. Each failure waits for another lane (below).
- `bash dev/run_tests.sh --fast`: 1932 passed, 179 failed, 99 errors, 9 skipped. 8 failures are
  mine and wait for other lanes (below); the rest are in files I do not own (next section). I
  did not run `--fast` on `d103/base`, to save the session's credits.

## Deliberate break

I left `'strong'` in `GATES`. The test for config_engine PROOF-41 failed (`assert 'strong' ==
'passed'`). I restored the file with `git checkout -- scripts/mcp/purlin/gate.py` and the test
passed again. The first try did not fail: `resolve_gate` checked for `strong` before it checked
`GATES`. I moved the check inside the `not in GATES` branch, where C1 puts it ("in place of
`NOT_A_GATE`"), and the break then failed as planned.

## Rules and proofs deleted

- **scaffold RULE-2** (the minimum by gate) and its PROOF-2, PROOF-99, PROOF-100, PROOF-101,
  PROOF-102, PROOF-103, with their tests and the `_minimum` helper.
- **scaffold RULE-66** (three choices) and PROOF-152, replaced by RULE-76 and PROOF-167.
- **server PROOF-149** (`min_strength` 101 refused) and **PROOF-153** (`min_strength` null
  written).
- **update PROOF-37** (the gate question answered `strong`) and **PROOF-45** (`strict` gives
  `strong`; RULE-49 and PROOF-161 carry the case now).
- Unmarked tests in `dev/test_specs_reader.py` `TestGate`: the per-gate `min_strength`, the
  named-minimum override and the empty minimum. The other three were rewritten to two gates.

## Rules and proofs reworded

- **server** RULE-28 and RULE-29 lose `min_strength`, and `gate` takes `passed or signed`.
  PROOF-134, PROOF-144, PROOF-131, PROOF-141 write `signed` in place of `strong`. PROOF-143 reads
  `ci` stored as null in place of `min_strength`. PROOF-147 and PROOF-154 read
  `passed or signed`.
- **config_engine** PROOF-12 and PROOF-35 write `signed`. Its `> Scope:` gains
  `scripts/mcp/purlin/gate.py` (states.md also scopes it) and its description one sentence.
- **scaffold** the description, RULE-1, RULE-4, RULE-64, RULE-5, RULE-52, RULE-45 (the gate
  clause moves to RULE-77), RULE-61, RULE-46 (`--mutation` at either gate) and RULE-36 (the walk
  of the two gates). Proofs: PROOF-1, PROOF-4, PROOF-5, PROOF-54, PROOF-12, PROOF-62 (now from
  `passed` to `signed`), PROOF-63, PROOF-104, PROOF-45, PROOF-81, PROOF-46, PROOF-86 (now at
  `--gate passed`), PROOF-138. Every other proof that set a project up at `--gate strong` now sets
  it up at `--gate signed`, and `Gate strong.` reads `Gate signed.`: PROOF-14, 15, 18, 20, 21, 22,
  23, 42, 44, 48, 51, 65, 66, 67, 68, 69, 70, 71, 72, 73, 74, 75, 76, 77, 78, 79, 82, 84, 87, 89,
  105, 106, 107, 108, 113, 114, 127, 128, 131, 132, 133, 134, 135, 139, 140, 142, 143, 144, 145,
  146, 147, 163, 164, 165, 166 and PROOF-13 (their tests follow).
- **scaffold RULE-36's walk**, rewritten to one case each of the new contract: PROOF-36 and
  PROOF-117 end on `Nothing left to do. To release a version: purlin:test --release` (PROOF-117
  audits at `passed`, with the sentence `... The audit found 1 strong and 0 weak.`); PROOF-90 is
  the release at `passed` writing `passed/0.1.0`; PROOF-92 the release at `signed` printing
  `READY_TO_SIGN` and writing no tag; PROOF-119 the sign-off through `sign.py --answers`; PROOF-93
  the first sign-off writing `signed/0.1.0`. PROOF-37, PROOF-94 and PROOF-95 end on the same
  `TO_RELEASE` line.
- **update** RULE-10, RULE-12 (two choices, the default `passed` where the gate named is not one
  of the two), RULE-25 (every key dropped but `min_strength`, which RULE-48 names), RULE-26,
  RULE-37. Proofs: PROOF-69, PROOF-10, PROOF-38, PROOF-47, PROOF-130, PROOF-26, PROOF-54,
  PROOF-55, PROOF-114, PROOF-56, PROOF-58, PROOF-142.
- **skill_init** RULE-5 and RULE-6; PROOF-30, PROOF-31, PROOF-32, PROOF-34, PROOF-35, PROOF-6.
  `skills/init/SKILL.md` is 187 lines (was 190), under 250.

## Words chosen that section 7 does not give

- The init skill's gate table: `| Gate | What a release asks | The tag |`, rows
  `every rule's tests pass` / `purlin:test --release writes passed/<version>, unsigned` and
  `every rule's tests pass, and a person signs each release` / `the first purlin:sign over the
  evidence package writes signed/<version>`; then `A person pushes the tag.` and `At either gate
  the AI audit and mutation testing are tools a person runs with purlin:audit; nothing waits on
  them.`
- The init skill: `Under signed, a release needs a sign-off over its evidence package`, and the
  update paragraph's `reading a gate of strong as passed and taking out min_strength`.
- `gate.py` names the retired-keys line `RETIRED_LINE`; its text is decision 102's, unchanged.

## Calls left

- **`states.py` reads `cfg.min_strength`** (line 857). C1 removes the slot, so every status of a
  project with a rule raises `AttributeError` until lane `counting` merges and deletes that read
  (C2 deletes `strength <p>% under <m>%`). This is the bulk of the `--fast` failures below.
- The upgrade prints `The gate strong is now passed; ...` only when the gate chosen is `passed`:
  a person who answers `signed` to the gate question is not told the old gate became `passed`.
- RULE-77 overlaps RULE-1 and PROOF-5 (the mutation question at `signed`), and RULE-78 overlaps
  RULE-5 (the keys written); section 4 asked for each, so each stands.

## Failures in files I do not own

Almost all come from one read: `scripts/mcp/purlin/states.py:857` reads `cfg.min_strength`,
which C1 removes, so any status of a project with a rule raises `AttributeError` (lane
`counting` deletes the read under C2). To separate the causes I put a temporary
`getattr(cfg, 'min_strength', None)` there, reran the eleven failing files, and restored the file
with `git checkout -- scripts/mcp/purlin/states.py`. Nothing of it is committed. With the shim,
80 failed and 1 errored, all in other lanes' files. Every one builds a project at the gate
`strong`, reads `min_strength` or the minimum, quotes the old gate words, or tests per-rule
signing:

- `dev/test_states.py` (37 failed, 1 error) and `dev/test_summary.py` (1): lane `counting`;
  section 6 expects these. Among them is states PROOF-224, which quotes
  `passed, strong or signed`, and PROOF-226 and PROOF-227, whose `"min_strength" is not a number`
  lines C1 deletes.
- `dev/test_run_script.py` (18), `dev/test_ai_audit.py` (4), `dev/test_consumer_ci.py` (2): lane
  `run`. The consumer-ci fixture is now `gate: passed` with no `min_strength`, as section 4 asks.
- `dev/test_export.py` (8), `dev/test_tag.py` (3): lane `release`.
- `dev/test_signatures.py` (10): lane `signoff`.

Without the shim, `dev/test_drift.py` (1), `dev/test_evidence_writer.py` (2),
`dev/test_report_refresh.py` (2) and `tests/test_feat.py` (1) failed too; each passes with the
shim, so each waits for lane `counting` alone.

## Tests that fail only because another lane has not merged

In `dev/test_init_scaffold.py`, 8 tests:

- Lane `counting` (C3's `TO_RELEASE` and the audit sentence, and `states.py`'s
  `cfg.min_strength`): PROOF-37, PROOF-94 (skipped where npm is missing), PROOF-36, PROOF-117.
  PROOF-95 too, where dotnet is present.
- Lanes `release` and `run` (`purlin:test --release`, C5): PROOF-90, PROOF-92.
- Lane `signoff` (`sign.py --answers`, C8 and C9): PROOF-119, PROOF-93.

`dev/test_init_update.py` needed no test waiting on another lane: every end-to-end test there
passes on this branch.
