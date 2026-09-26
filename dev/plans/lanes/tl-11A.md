# Lane 11A: strong counts any audit, signed requires CI, platforms roll up

Plan: `dev/plans/three-levels.md` (in full; decision 29 is yours and overrides decisions 5
and 28 where they disagree). Rules: `dev/plans/lanes/tl-_rules.md` (in full). Worktree
`/Users/richlabarca/LocalCode/purlin-wt/11A`, branch `lane/11A` off `lane/10B`. **Do not
push. Do not open a pull request.** Your work stays committed on your branch.

## What you own

### The audit writes and commits its record

- `purlin_run.py --audit` writes the record for each feature it audited and the briefs, under
  `.purlin/records/local/<feature>/` and `.purlin/briefs/local/<feature>/`, `source: local`,
  and commits them itself as `purlin: record for <sha7>` the way `results.py` commits the
  test results (never a push; `Record committed.` / `Record unchanged.`). Reuse `results.py`'s
  commit path rather than a second one. Ends with `gate strong: <n> of <rules>` or
  `gate not met: <n> of <rules>`, exit 1 when not met, counting every rule under `specs/`.
- `--ci` writes the same files under `.purlin/records/ci/` and `.purlin/briefs/ci/`, `source:
  ci`, committed through the host's API where `commits_here` says so. `record_format.md`
  bumps to 4: the two folders, `source` `local` | `ci`, the folder-and-field agreement rule.
- `scripts/mcp/purlin/records.py` reads both folders; a file whose `source` disagrees with
  its folder is ignored with one warning naming the path. `counts_under`: `passed` and
  `strong` count `local` and `ci`; `signed` counts `ci` only, for the passed cell and the
  strong cell both (the local test results and local records are previews there).
- `scaffold.py`'s branch rules restrict `.purlin/records/ci/**` and `.purlin/briefs/ci/**`;
  `update.py` moves an existing `.purlin/records/<feature>/` into `ci/` or `local/` by the
  file's source and refreshes the workflow.

### Platforms in the passed cell

- `states.py`: the passed cell gains `platforms: {<os>: {word, source, at}}`, one entry per
  operating system a counting run covered (test results and records, newest per platform).
  Word `partial` when the rule's tests passed on at least one platform and failed or did not
  run on another it ran on or is tagged for; `partial` is not met; a rule tagged for a
  platform with no run there and no other platform reads `not run` as today. `failed` still
  wins when every platform that ran failed. New bucket `partial` between `failing` and
  `passed`; summary and rollup keys gain `partial`; `flags.partial`. The signed cell gains
  `at` (the signature's commit date) beside `signer`. `blocked_by` unchanged.
- `payload.py`: schema 6 (`SCHEMA_VERSION = 6`; `app.js` `SCHEMA = 6` is lane 11B's), the
  new keys, `proofs_without_test` per feature rollup (count and ids). `dev/fixtures/report/`:
  regulated gains a `partial` rule (login RULE-4 becomes partial: linux passed, windows failed),
  every `platforms` map filled from the records present, `proofs_without_test` set, the
  summaries updated; `solo` and `team` follow. `tl-_rules.md` items 6, 9 and 11 follow.
- `status.py`, `scan.py`, `gate_check.py`: the table columns per decision 29 (`Spec | Rules |
  Proofs | Tests | Strong | Signed`), `partial` counted and named, the `Partial (n)` section
  in the gate check between `Not passed` and `Weak`.

### Words

`skills/test`, `skills/audit`, `skills/init`, `skills/status`, `agents/purlin.md`,
`references/hard_gates.md` (which source counts at each gate, in one table), `glossary.md`
(`partial`, the record folders), `purlin_commands.md`, `commit_conventions.md`,
`review_criteria.md` where the strong cell is described, `references/formats/tests_format.md`
if the results gain a platform field. Lane 11B does the docs pages, the board and the slides.

### Tests and specs

`dev/test_run_script.py`, `dev/test_records.py`, `dev/test_test_results.py`,
`dev/test_mcp_server.py` (the platforms and partial cases, the source agreement warning),
`dev/test_init_scaffold.py`, `dev/test_init_update.py`, `dev/test_init_e2e.sh` (the walk:
local audit meets `strong`; `signed` needs CI's), `dev/test_gate_check.py`, `dev/test_scan.py`,
`dev/test_skills.py`, `dev/test_vocabulary.py`. Specs: `specs/mcp/states.md`, `specs/run/records.md`,
`specs/run/run_script.md`, `specs/init/scaffold.md`, `specs/init/update.md`, `specs/ci/gate_check.md`,
`specs/skills/skill_audit.md`, `skill_test.md`, `skill_init.md`, `specs/instructions/purlin_agent.md`.
Keep every marker aligned. `dev/test_purlin_report*.py` will be red on the new fixtures until
lane 11B; name them as expected red.

## Acceptance

```
pytest dev/test_run_script.py dev/test_records.py dev/test_test_results.py dev/test_mcp_server.py dev/test_init_scaffold.py dev/test_init_update.py dev/test_gate_check.py dev/test_scan.py dev/test_skills.py dev/test_vocabulary.py
bash dev/test_init_e2e.sh
bash dev/run_tests.sh --fast
```

Report in the DONE shape of `tl-_rules.md`, with the spec maxima, the test delta, the exact
fixture keys you added (so 11B can read them), and decisions.
