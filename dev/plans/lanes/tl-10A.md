# Lane 10A: spec, build, test; the test results; audit measures; CI records

Plan: `dev/plans/three-levels.md` (in full; decision 28 is yours, with 23 to 27 behind it).
Rules: `dev/plans/lanes/tl-_rules.md` (in full). Worktree
`/Users/richlabarca/LocalCode/purlin-wt/10A`, branch `lane/10A` off `lane/9B`. **Do not push.
Do not open a pull request.** Your work stays committed on your branch.

## What you own

### `purlin:test` writes and commits the test results

- `scripts/run/purlin_run.py --quick` (the arm `purlin:test` runs) writes, after the run:
  `.purlin/tests/<feature>.json` per feature covered (`schema: purlin-tests/1`, `commit`,
  `at`, `os`, `rules: {RULE-N: word}` with the passed-cell words, `proofs: [{id, rule,
  result, tier, env, test}]`), and `.purlin/tests.md`, one table for the whole project:
  `Feature | Rules | Passed | Failing | No test | Last run` where Last run is `<sha7> ·
  <time> · <os>`, a heading line naming the commit, and one sentence saying these are the
  last local run and count only at `passed`. Then it commits both with the subject
  `purlin: tests at <sha7>`, under the person's identity, and prints `Test results
  committed.`; it never pushes and never prints a push command. A run with nothing changed
  prints `Test results unchanged.` and commits nothing. `--feature` runs write the features
  they ran and leave the rest of the table as it was.
- `.purlin/tests/` and `.purlin/tests.md` are tracked; `templates/gitignore.purlin` and this
  repository's `.gitignore` leave them tracked. The runtime proofs under `.purlin/runtime/`
  stay as they are; the payload reads the committed results as the `local` source and the
  runtime proofs for this checkout's uncommitted run, newest wins.
- The summary line: `gate passed: <n> of <rules>` or `gate not met: <n> of <rules>`, exit 1
  when not met. This is the check a person runs at `passed`; no script.
- `scripts/mcp/purlin/payload.py`, `states.py`, `records.py`: source `developer` is gone;
  `counts_under('passed', label)` is true for `local` and `ci`; the `local` source reads the
  committed test results first and the runtime run second. `references/formats/` gains
  `tests_format.md` (Format-Version 1) for the two files, in the same commit as the writer.
- When the run finds a proof tagged `@env` for an operating system this machine is not, it
  prints one sentence: `<feature> PROOF-N needs <os>; this machine is <os>. A remote runner
  runs it: purlin:init adds one.` and nothing else changes.

### `purlin:audit` measures, CI records

- `purlin_run.py --record` becomes `--audit`: the breaks, the free checks and the model
  review, printing strength beside the minimum, the findings and the observations per rule,
  and `This audit counts only when CI runs it.` It writes no record. `--commit` is deleted.
  `_commit_as_developer` and the developer identity are deleted from `records.py`.
- `--ci` is the CI job's arm: `purlin:test`'s run, then at `strong` and above the audit,
  then `build_record` and the briefs, committed through the host's API where `commits_here`
  says so (lane 8A). At `passed` `--ci` runs the tests, posts the comment, publishes the
  dashboard, writes no record and commits nothing. `templates/purlin.yml` and the Azure
  template call the arm the same way; the gate step stays last.
- `--remote` moves from the audit to the test: `purlin_run.py --quick --remote` pushes the
  run branch, waits, pulls back what the runner committed (records at `strong` and above;
  nothing at `passed`, where it prints the runner's summary instead), deletes the run branch.
  `remote.py` follows; `purlin:audit --remote` is refused with one line naming
  `purlin:test --remote`.
- `record_format.md` bumps to 3: the `source` enum is `ci` only, the developer paragraph is
  gone, and the record is written by the CI job after the tests and the audit.

### `purlin:init` explains, checks, then asks

- `scripts/init/scaffold.py`: at `passed`, when a remote exists, print the three reasons in
  the exact wording of decision 28 (three sentences, one per reason), then ask `Run the tests
  on a remote runner too? [y/n]`; `--ci` is deleted (a yes is what it did). At `strong` and
  above the workflow is always written and the reasons are printed as the explanation.
  Before writing a workflow: check a remote exists (`git remote`), read the host from its
  URL, check the protected branch exists on the remote (`git ls-remote --heads`), report the
  host CLI (`gh` or `az`) as present or absent; a failed check prints one line naming it and
  what to do, and writes no workflow. The same checks run under `--update` when the workflow
  is refreshed.
- `scripts/init/update.py`: a project carrying `--ci` in its notes or a `developer` record
  is migrated (records with source `developer` are deleted with one line saying why; the
  retired table names `--commit` and `developer`).

### Skills, agent, references (the words; lane 10B rewrites the prose)

- `skills/test/SKILL.md`: the results files, the summary line, the `@env` sentence,
  `--remote`. `skills/audit/SKILL.md`: measures, never records locally, no `--commit`, no
  `--remote`. `skills/init/SKILL.md`: the explanation, the checks, the question.
  `agents/purlin.md`, `references/purlin_commands.md`, `hard_gates.md`, `glossary.md` (test
  results, source `developer` retired), `commit_conventions.md` (`purlin: tests at <sha7>`;
  the record commit is CI's only). Keep every sentence short; 10B does the pages.

### Tests and specs

`dev/test_run_script.py`, `dev/test_records.py`, `dev/test_consumer_ci.py`,
`dev/test_init_scaffold.py`, `dev/test_init_update.py`, `dev/test_init_e2e.sh` (the walk at
`passed` is spec, build, test, results committed, no record; at `strong` CI's record),
`dev/test_mcp_server.py` (sources), `dev/test_skills.py`, `dev/test_vocabulary.py` (`developer`
as a source and `--commit` join the retired list; `audit --remote` too), a new
`dev/test_test_results.py` for the two files and the commit. Specs: `specs/run/run_script.md`,
`specs/run/records.md`, `specs/init/scaffold.md`, `specs/init/update.md`, `specs/mcp/states.md`,
`specs/skills/skill_test.md`, `skill_audit.md`, `skill_init.md`, `specs/instructions/purlin_agent.md`,
and a new `specs/run/test_results.md` for the results files. Keep every marker aligned.
`dev/fixtures/report/*.json`: `source` values `local` and `ci` only; `team.json`'s
checkout_design record becomes `local` with `counts` false under `strong`.

## Acceptance

```
pytest dev/test_run_script.py dev/test_records.py dev/test_consumer_ci.py dev/test_init_scaffold.py dev/test_init_update.py dev/test_test_results.py dev/test_mcp_server.py dev/test_skills.py dev/test_vocabulary.py
bash dev/test_init_e2e.sh
python3 scripts/run/purlin_run.py --feature states --quick --project-root .   (paste the summary line; confirm .purlin/tests.md and the commit)
bash dev/run_tests.sh
```

Report in the DONE shape of `tl-_rules.md`, with the spec maxima per touched spec, the test
delta, the exact wording of the three reasons and init's question as printed, and decisions.
