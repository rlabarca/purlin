# Lane `own`: this repository's own Windows run

Branch `lane/d119-own`, commit `3d321a690`. Nothing pushed, no run started on GitHub.

## Tests

| | Passed | Failed | Skipped |
|---|---|---|---|
| Before, `dev/test_windows_run.py` | the file did not exist | | |
| After, `python3 -m pytest dev/test_windows_run.py -q` | 4 | 0 | 0 |

- Added: 4, one per proof of `windows_run` (PROOF-1 to PROOF-4).
- Deleted or rewritten: none. The tests these come from, in `dev/test_host.py`, are lane
  `run`'s to delete.
- Waiting on another lane: none. No test here starts `purlin_run.py`.
- Appendix A's script over `dev/test_windows_run.py`: `0 gone, 0 reworded, 4 right as they stand.`
- Section 8's first grep over `dev/manual/README.md`: empty.
- Broken on purpose: the `git pull --ff-only` line taken out of `_bring_back`. PROOF-1 and
  PROOF-2 failed; restored, 4 passed.

No test needs the network or the real `gh`. PROOF-1 answers every process from a stand-in for
`subprocess.run`, since the proof fixes HEAD at `4f1c2ab…`. PROOF-2 runs git for real against
a bare repository on disk; the stand-in answers `gh`, and its watch puts the runner's one
commit on the run branch before it exits 1, so the test also sees that commit pulled and the
run branch gone. PROOF-3 uses a real checkout with one uncommitted file. PROOF-4 reads the
workflow file with the standard library.

## What came from where

| New | From |
|---|---|
| `dev/windows_run.py` | `scripts/run/remote.py`, carried over as they stood: `run_branch_name`, `find_run`, `_github`, `_bring_back`, `_push`, `_delete`, `_dirty`, `_table`, `_branch`, `_have`, `_environment`, `_run`, `_capture`, the constants `FIND_SECONDS`, `FIND_EVERY`, `COMMAND_SECONDS`, and the body of `run_remote` as `windows_run` |
| `.github/workflows/windows.yml` | `.github/workflows/purlin.yml`: the trigger, the permissions, the 90-minute cap, checkout, Python 3.11 and the framework step, unchanged |
| `dev/test_windows_run.py` | `dev/test_host.py`: `stand_in`, `git`, `make_repo`, `FakeProcesses`, and the tests of `host PROOF-24`, `68` and `63`; the bare repository of `host PROOF-143` |

Nothing was taken from `host.py` or `workflow.py`: the GitHub round trip needed neither once
the host lookup and the runner file were gone.

Not carried: `ensure_runner`, every Azure DevOps function and line, the `workflow` import,
`NOT_A_HOST`, the `config_problem` check (the status table already prints that problem),
`_dirty`'s `besides` argument and `AZURE_EXTENSION_USE_DYNAMIC_INSTALL`.

## Lines a person reads, and where they print

All in `dev/windows_run.py`. The first two are the spec's and the plan's; the rest are the
old lines with `purlin:test --remote` reading `python3 dev/windows_run.py` and `the git host`
reading `GitHub`, as section 6 says.

- `This checkout has changes that are not committed, so a run would prove something other than what is here. Commit them, then run python3 dev/windows_run.py again.`
- `The run failed on GitHub. The table below is what came back.`
- `This checkout is not on a branch, so there is nothing to push. Make one with git switch -c <name>, then run python3 dev/windows_run.py again.`
- `python3 dev/windows_run.py waits for the run with the GitHub CLI, gh, which is not installed, so nothing was pushed. Install gh, then run python3 dev/windows_run.py again.`
- `The push failed, so no run was started. Check that git push origin works from this checkout, then run python3 dev/windows_run.py again.`
- `No run registered for <run branch> within 60 seconds, so the run branch was deleted and nothing came back. Check that GitHub runs .github/workflows/windows.yml on a push to run/*, then run python3 dev/windows_run.py again.`
- `Pushing <branch> as run/<branch>-<sha7>.`, `Waiting for the windows.yml workflow on <run branch>.` and `The run branch <run branch> is still on origin. Delete it with: git push origin --delete <run branch>`: unchanged.

The workflow's header comment and its two step names, `Run the tests tagged for Windows` and
`Return the evidence`, are the names the docs example in plan section 4 uses.

`dev/manual/README.md`: `Two checks a person runs. Each drives the real `claude` CLI once ...`,
`Run them from the repository root, in this order:` and `these two are none of those.`

## Differences from the plan

1. `_bring_back` answers 0 or 1, not `gh run watch`'s own code. The spec says the script exits
   1 when the run failed; `gh` may exit with another number.
2. The workflow has no matrix: `runs-on: windows-latest` directly, since the spec names one job
   and no other system. The job is named `windows`.
3. The test command is `python3 scripts/run/purlin_run.py --ci --commit`, with no `--all`, as
   K1 and `run_script` RULE-59 have it.
4. `.github/workflows/version-check.yml` does not name the old file, so it is not changed.
5. Git records the workflow as a delete and an add, not a rename: too little of the text is
   the same. `git mv` was used.

## Open

- **The workflow depends on lane `run`.** On this branch `--ci --commit` is still the old arm.
  The workflow is right only once `run` is merged (K1 to K3).
- **The script takes no arguments and reads none.** `python3 dev/windows_run.py --help` starts
  a run. No rule or contract asks for a usage line, so none was added.
- **A run that fails before the test step** (checkout, Python, the framework step) leaves no
  commit; the script then pulls nothing, prints the failure line and the table, and exits 1.
  That is as the old code behaved.
- Not shown by any test: how GitHub's runner behaves. Integration's step 10 shows it.
- The first real run needs `windows.yml` on the pushed commit, which it is once this is merged.

## Failures in files this lane does not own

None seen; only `dev/test_windows_run.py` was run. `dev/test_host.py`, `dev/test_remote.py`
and `dev/test_run_script.py` still name `purlin.yml` and `remote.py`, and are lane `run`'s.
`docs/`, `references/glossary.md` and `dev/test_init_scaffold.py` name
`.github/workflows/purlin.yml` and belong to `docs-a`, `words` and `surfaces`.
