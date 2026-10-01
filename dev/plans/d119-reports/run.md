# Lane `run`, decision 119

Branch `lane/d119-run`, one code commit: `feat(run_script): the remote runner goes; --ci writes
its section and --commit commits it (decision 119)`. Nothing pushed.

## Test numbers

| | Passed | Failed | Skipped |
|---|---|---|---|
| Before, the seven files the lane owned (3 kept, 4 to delete) | 164 | 0 | 2 |
| After, `dev/test_run_script.py`, `dev/test_evidence_writer.py`, `dev/test_evidence_reader.py` | 122 | 0 | 1 |

166 less 45 deleted plus 2 added is 123. The skipped test that went is `host PROOF-117`; the one
left is `run_script PROOF-221`'s, which runs on Windows.
`python3 -m pytest dev/test_init_scaffold.py -q -k readme`: 1 passed, 1 skipped.
No test waits on another lane.

## Tests

- **Deleted, 45.** `dev/test_host.py` (31), `dev/test_remote.py` (7), `dev/test_consumer_ci.py`
  (3), `dev/test_host_pathspec.py` (1); in `dev/test_run_script.py` the tests of `run_script`
  PROOF-272 and PROOF-273 with the fixture `on_github`; in `dev/test_evidence_writer.py` the
  test of `evidence_writer` PROOF-44.
- **Rewritten, 6.** `run_script` PROOF-10, PROOF-12, PROOF-117, PROOF-17;
  `evidence_writer` PROOF-78; `evidence` PROOF-19. Helpers: `evidence_run` now runs the script in
  this process and returns the exit code alone (no fake `host` module, no `calls`), so the tests
  of PROOF-209, PROOF-102, PROOF-109, PROOF-87 and PROOF-171 changed in how they call it and in
  nothing they assert; `_FakeModule`, `commit_files` and `_mixed` are gone; `_section` in
  `dev/test_evidence_writer.py` writes `email` under either source and takes no `hostname`.
- **Added, 2.** `evidence_writer` PROOF-95 and PROOF-96, with the helper `_runner_checkout`.

Every proof of `run_script`, `evidence_writer` and `evidence` has a test comment. Appendix A's
script over the three files: `0 gone, 0 reworded, 124 right as they stand.`
The greps of plan section 8 find nothing in the lane's files.

Broken on purpose: the call to `commit_ci` in `_ci` replaced by `pass`. The tests of
`evidence_writer` PROOF-95 and PROOF-96 failed. Restored with
`git checkout -- scripts/run/purlin_run.py`.

## What was built

- `scripts/run/purlin_run.py`: K1 and K2 as written. `--remote` and `--commit-runner` get
  `purlin: unknown argument <token>.` and the usage. `--commit` is accepted with `--ci`; a `--ci`
  run makes no first commit of specs, tests or settings. `_ci` writes on whatever branch it is
  on. `runner_name(project_root)` and `machine_name()` lost their unused arguments.
- `scripts/run/evidence.py`: K3. `commit_ci` added; `email` written on every section;
  `hostname` and `merge_for_host` gone.
- `scripts/mcp/purlin/evidence.py`: K4.
- Deleted: `scripts/run/{remote,host,workflow,ci}.py`, `templates/purlin.yml`,
  `templates/purlin.azure-pipelines.yml`, the four test files. `dev/fixtures/consumer-ci/` is
  not in this worktree and is not tracked; nothing to delete here.
- `references/formats/evidence_format.md`: 8 to 9, in the same commit as the code.
  `references/formats/marker_format.md`: one clause, version 4 kept.
  `templates/evidence-readme.md`: plan section 4's two lines and sentence.

## Lines a person reads

All are the plan's or a spec's, word for word:

- `1 proof needs Windows; this machine is macOS. Run purlin:test on Windows.` and
  `3 proofs need Windows; this machine is macOS. Run purlin:test on Windows.`, printed by
  `--test` and `--audit` after `Ran ... on ...`.
- `.purlin/evidence/ci/login.json names the source "local" but sits in ci/; it is ignored. Start the run that wrote it again.`,
  the reader's warning; `Start the run that wrote it again.` ends every warning for a `ci/` file.
- The usage line, K1's.
- `Evidence committed.` and `Evidence unchanged.` under `--ci --commit`, the lines `--test --commit` prints.

Chosen by this lane, none new: one line reused where no spec speaks. `--ci --commit` outside a
git repository prints the existing
`Evidence written; there is no git repository to commit it to.`, as `--test --commit` does.

Wording chosen in `references/formats/evidence_format.md` (a reference, not a printed line):
the `runner` row reads `the slug of `email`, made from its part before the `@`; `unknown` where
there is none`; the last bullet of "How a writer merges" and the last paragraph of "The two
commits" are rewritten to plan section 0.

## Differences from the plan

- The plan counts 4 tests rewritten in `dev/test_run_script.py` and 1 in each of the other two;
  that holds. Five more tests changed only in how they call `evidence_run`.
- Comments and docstrings in the lane's files that named a `runner` as a machine now say
  `pipeline` or `machine`; two test docstrings that told the history of the first CI runs now
  state the reason alone (decision 44). The field `runner` keeps its name.
- The first commit of the lane was amended once, before anything else was built on it: a
  mistyped `git add` had left the code out of the commit that carried the deletions.

## Left unbuilt, or open

Nothing in the lane's files.

## In files this lane does not own

- `dev/test_ai_audit.py:517` still writes `'hostname': 'runner-17'` into a section. No lane's
  list in plan section 3 names that file. Section 8's grep will find it.
- `dev/fixtures/reports/vitest/vitest.xml:3` holds `hostname="dev-machine"`. It is an attribute
  of vitest's own JUnit report, a fixture of the report reader, and was left. Section 8's grep
  will find it too, so the grep needs that path excluded or the finding accepted.
- `dev/test_export.py:102` and `dev/test_signatures.py:86` set `found['hostname']` (lane
  `surfaces`).
- `dev/test_init_scaffold.py:450` and `:453` name `purlin.yml` (lane `surfaces`, PROOF-173).
- `dev/manual/check_azure_remote.py` imports the deleted `remote`, and `dev/manual/README.md`
  names it (lane `own` deletes one and edits the other).
- `.purlin/evidence/ci/*.json` in this repository still read `remote runner, Windows` and carry
  `hostname`, as plan section 6 says they will until the next Windows run. The reader ignores
  the extra key.
