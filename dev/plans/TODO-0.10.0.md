# Purlin 0.10.0: outstanding after the unattended run (2026-09-14, closed at `2ca875e5`; updated 2026-09-15; restated 2026-09-16 for the three-level model)

Everything below is open. The refactor's lanes have all landed on `three-levels`; this
is what the run could not finish, found and left, or left to a person.

## For the user, in order

1. **Sign the review list.** Every old signature file, and every file CI wrote for one, was
   dropped rather than migrated (decision 10 of the plan), so nothing is signed. Run
   `purlin:sign` to walk the review list; 432 rules are on it.
2. **Apply the three GitHub rulesets** init printed (require a pull request and the `purlin`
   check with the Actions app as the only bypass; restrict `.purlin/records/**` and
   `.purlin/briefs/**` to the Actions app; block force pushes and deletions).
3. **Release.** One more green sweep to set the `Tests at this commit` line, `purlin:audit
   --tag 0.10.0` to write the `record/0.10.0` tag, a pull request from `three-levels` to
   `main`, the `v0.10.0` tag (`VERSION` already reads 0.10.0; `dev/bump_version.sh --check`
   guards the derived copies).
4. **`purlin:audit --remote`** from this Mac has not been exercised (C4 item 4); the GitHub
   branch of `scripts/run/remote.py` is untested against a live host. The Azure DevOps
   branch prints the pipeline URL and carries `TODO(ado-remote)` for the work machine.

## Defects and gaps found by the run, not fixed

5. **Test strength is real locally and `n/a` in CI.** `setup.cfg` points mutmut at `scripts/`
   under the `dev/` tests; init names nested source and a test directory, and ignores
   `mutants/`. CI does not install mutmut: a full run takes hours here and mutmut 3 does not
   run on Windows, so CI records carry `n/a` and the gate skips the comparison. Measure locally
   with `--arm-timeout 18000`, or in a scheduled Linux job. The first full run (2026-09-15, 55%
   judged) read under 80 on every finished feature (scaffold 12, server 15, upstream 56), and
   2,516 breaks had no covering test, about 2,100 of them code reached only by subprocess.
   In-process tests closed most of that reach. Scoped runs, before and after: scaffold 12 to
   69, server 15 to 58, upstream 59 to 68, config_engine 62 to 75, `pytest_purlin.py` 18 to 50,
   `ci.py` 46 to 71, `remote.py` 30 to 65, `records.py` 50 to 60, `static_checks.py` 58 to 68.
   What remains is mostly assertion strength, not reach: server keeps 257 survivors with no
   uncovered break. A full rerun at `e78d1868` was stopped at about 40% (8,600 of 22,012) to
   free the machine; its state is kept, so `mutmut run` in that worktree resumes where it
   stopped and only then are the per-feature numbers final. Partial reads at that point:
   mutation 73, records 71, config_engine 70, static_checks 66, states 66, upstream 62,
   approvals 57, server 53, brief 51, proof_common 46, scaffold 43, run_script 36, drift 28,
   with only 142 breaks left uncovered across `scripts/`. `security_no_dangerous_patterns` scopes `scripts/**/*.py`, so its number is all of
   `scripts/`; nine tests that read git state or source text are deselected under mutmut.
6. **Fixed: the local anchor repository is reproducible, and the pin is current.** Two fresh
   runs of `dev/setup-external-refs.sh` published the same sha, `62a2091`, the head this
   checkout's own copy already had; the old pin `379a046` was simply behind. The script now also
   turns commit signing off, since a signature carries its own time and a machine that signs by
   default would publish another sha. The pin advanced with `upstream.py sync`, which kept the
   note once `upstream` RULE-23 fixed a sync dropping it.
7. **Fixed: `scan.py` prints the review list.** After the rollup it prints one line per rule on
   the list: risk, feature and rule id, state and why it is listed, high risk and Stale first
   (`records` RULE-25). The QA tool reads it from there. The list is the payload's review list,
   so it still holds signed rules until the review-list defect found on the dashboard is fixed.
8. **Fixed: the shell arm runs `*.test.sh` in subdirectories.** It walks the project, skipping
   hidden directories, `node_modules`, `bin`, `obj` and `mutants/`, and runs each from the root in
   sorted order (`run_script` RULE-44). This repository's own suites under `dev/` are named
   `test_*.sh`, not `*.test.sh`, so the root wrappers and the three `@env(linux)` proofs stay as
   they are; renaming the suites is a separate change.
9. **Fixed: a Windows developer's record commit stages its records.** `scripts/run/records.py`
   `deleted_records` and `_commit_as_developer` now hand git `.purlin/records` with `/` on every
   operating system (`records` RULE-24).
10. **Fixed: the matrix sentences say Linux is always present.** `skills/init/SKILL.md` and
    `docs/raising-the-gate-and-upgrading.md` now say a Linux job always runs, plus one job for
    each other operating system an `@env` tag names.
11. **Fixed: the spec skill says "one sentence in, at least three rules out".**
12. **`dev/manual/` checks** drive the nested CLI with permissions skipped; fine for a
    throwaway project, worth knowing before running them elsewhere.
13. **The Windows job takes 15 to 18 minutes** (playwright plus the whole suite); the Linux
    job four. Acceptable, noted.
14. **Part A of the plan is stale in three places** (`dev/plans/evidence-workflow.md`): A4's
    claim that the API commit's committer is `github-actions[bot]` (it is GitHub's web-flow
    identity, the bot is the author); the matrix wording (Linux always present); the
    `report` config key, which no longer exists. The DONE sections record the corrections;
    the design file itself was left verbatim.
19. **The dashboard changed after run 9** (brand navy, the record boxes, the risk tints, the
    one-line ledger, the shorter bar); CI is green on it from `ed20c8b3`. Look at the board
    once more with your own data before release.
20. **Fixed: a brief shows each test's own body.** `brief.py` printed the first test's body
    under every test name when one proof had several tests (seen on 14 `run_script` rules). The
    body and the free findings are now looked up by the test name the record holds, and a name
    the file no longer holds shows no body rather than another test's (`brief` RULE-26).
21. **Fixed: reading a brief no longer dirties the tree.** The brief JSON is evidence and stays
    committed: CI commits it, a signer reads it and a signature names it. Writing a brief again
    for the same triple leaves the JSON untouched unless its evidence changed (`brief` RULE-27).
    The `.brief.txt` beside it is a local view: `*.brief.txt` is in this repository's
    `.gitignore`, in the block init writes (`scaffold` RULE-41), and the update adds it to an
    existing project (`update` RULE-22). The first CI run after the item 20 fix rewrites the
    briefs whose test bodies were wrong, about 120, once.
22. **Fixed in `b4b7a783`: a timed-out engine no longer records a partial number.** A run
    past `--arm-timeout` now measures nothing and prints why (`mutation` RULE-22). mutmut
    loses every feature's number because it runs the whole project at once; Stryker and
    Stryker.NET lose only the feature that timed out.
23. **Fixed: a signature's test hash no longer depends on which tests ran on the machine.**
    T now binds the tests the feature's latest counting records observed, every operating system
    together; a checkout's own runtime proofs speak only for a proof no record has observed
    (`states` RULE-30). Moving to it staled two signatures whose T had bound a machine's own run:
    `purlin_version` RULE-9 (its signature bound `test_unreleased_counts_match_the_sweep_record`,
    which CI never runs) and `static_checks` RULE-37 (its signature bound no test for PROOF-33,
    whose one test runs on Windows only). The fixture `Project.record` in
    `dev/test_signatures.py` wrote test names its runtime proofs did not use; fixing it stales
    the signatures that file backs.

24. **CI never writes a signature; a hold is written with `purlin:sign <feature> RULE-N --hold
    "<case>"`**, for example
    `purlin:sign records RULE-12 --hold "PROOF-12 names run_remote() with an Azure DevOps origin; the tests call _azure and _host apart"`
    and `purlin:sign static_checks RULE-39 --hold "no test shows a sweep never prints an unmeasurable row"`.

25. **The sweep ran a hand-kept list of test files**, so the 11 files this round added were
    left out of `dev/run_tests.sh`; it now globs `dev/test_*.py`, with the browser suites
    `dev/test_purlin_report*.py` still held out by `--fast`. Fixed.
26. **`dev/test_e2e_external_refs.sh` check 11 expects `- RULE-1: FORBIDDEN`**, wording the
    anchor dropped at `4fcc16ab`. It fails only where `dev/setup-external-refs.sh` has run.
    Fixing it edits that test file, which stales the signatures it backs.
27. **The `open` filter is gone with the state filters.** The board's filters are now
    `Untested`, `Failing`, `Weak`, `Unsigned`, `Stale or held`.
28. **Done by this release.** The three-level model gives level 1 the word `passed` and retires
    the old level-2 gate word for `strong`.
29. **The counts line in `RELEASE_NOTES.md` reads 986 passed**; the sweep now collects 1,083
    tests. `purlin_version` RULE-9 fails locally until the orchestrator sets the line after the
    closing sweep (item 3).

## Housekeeping

16. `.purlin/records/` now holds three records per feature per runner plus the developer's;
    retention is working. The first `record/*` tag will pin the ones that matter.
17. The design system copy under `design/` leaves out the PNG renders (gitignored `*.png`),
    the deck templates, slides and the reference dashboard kit, per A11.
