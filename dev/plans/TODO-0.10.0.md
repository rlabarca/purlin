# Purlin 0.10.0: outstanding after the unattended run (2026-09-14, closed at `2ca875e5`; updated 2026-09-15)

Everything below is open. The refactor's lanes have all landed on `evidence-workflow`; this
is what the run could not finish, found and left, or left to a person.

## For the user, in order

1. **Approve the rest.** 329 of 437 high and medium rules are approved, in the signed commits
   `72c4f1f4` and `6883ed3f`, each after a review read its test against its proof. 108 are held
   with the missing case named in `dev/plans/held-rules-0.10.0.md`; the 13 `skill_*` RULE-3 holds
   are one weakness in the shared next-step check. Six `schema_proof_format` approvals (RULE-1,
   2, 3, 4, 6, 7) do not count: the approver authored `d1006609`, the last commit to
   `dev/test_schema_proof_format.py`, so another approver signs those, or the approver signs
   again after someone else's next real change to that file. A change to a test file stales
   every approval that file backs. The public key still has to be uploaded to GitHub for the
   host to show Verified, and `verify_gate.py --check` counts an approval only once its commit
   is on `origin/main`.
2. **Apply the three GitHub rulesets** init printed (require a pull request and the `purlin`
   check with the Actions app as the only bypass; restrict `.purlin/records/**` and
   `specs/**/*.approvals/*.ci.json` to the Actions app; block force pushes and deletions).
3. **Release.** One more green sweep to set the `Tests at this commit` line, `purlin:verify
   --tag 0.10.0` for the validation tag, a pull request from `evidence-workflow` to `main`,
   the `v0.10.0` tag (`VERSION` already reads 0.10.0; `dev/bump_version.sh --check` guards
   the derived copies).
4. **`purlin:verify --remote`** from this Mac has not been exercised (C4 item 4); the GitHub
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
   so it still holds approved rules until the review-list defect found on the dashboard is fixed.
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
    body and the free findings are now looked up by the recorded test name, and a name the file
    no longer holds shows no body rather than another test's (`brief` RULE-26).
21. **Fixed: reading a brief no longer dirties the tree.** The brief JSON is evidence and stays
    committed: CI commits it, Reviewed reads it and an approval names it. Writing a brief again
    for the same triple leaves the JSON untouched unless its evidence changed (`brief` RULE-27).
    The `.brief.txt` beside it is a local view: `*.brief.txt` is in this repository's
    `.gitignore`, in the block init writes (`scaffold` RULE-41), and the update adds it to an
    existing project (`update` RULE-22). The first CI run after the item 20 fix rewrites the
    briefs whose test bodies were wrong, about 120, once.
22. **Fixed in `b4b7a783`: a timed-out engine no longer records a partial number.** A run
    past `--arm-timeout` now measures nothing and prints why (`mutation` RULE-22). mutmut
    loses every feature's number because it runs the whole project at once; Stryker and
    Stryker.NET lose only the feature that timed out.
23. **Fixed: an approval's test hash no longer depends on which tests ran on the machine.**
    T now binds the tests the feature's latest counting records observed, every operating system
    together; a checkout's own runtime proofs speak only for a proof no record has observed
    (`states` RULE-30). Moving to it staled two approvals whose T had bound a machine's own run:
    `purlin_version` RULE-9 (its approval bound `test_unreleased_counts_match_the_sweep_record`,
    which CI never runs) and `static_checks` RULE-37 (its approval bound no test for PROOF-33,
    whose one test runs on Windows only). The fixture `Project.record` in
    `dev/test_approvals.py` wrote test names its runtime proofs did not use; fixing it stales the
    approvals that file backs.

24. **Fixed: CI approves alone only what the free checks can settle, and gives way to a hold.**
    CI cannot read whether a test proves its proof text. It now also needs a clear body on every
    backing test (`approvals` RULE-39), and a person who finds the test does not prove the proof
    commits a hold with `approve.py <feature> RULE-N --hold "<case>"` (`approvals` RULE-40,
    `approval_format.md` Format-Version 2). CI never approves a held rule and its `.ci.json`
    gives way to a current hold (`approvals` RULE-41, `states` RULE-29). The two rules this item
    names still carry CI approvals until someone holds them:
    `approve.py records RULE-12 --hold "PROOF-12 names run_remote() with an Azure DevOps origin; the tests call _azure and _host apart"`
    and `approve.py static_checks RULE-39 --hold "no test shows a sweep never prints an unmeasurable row"`.

25. **The sweep ran a hand-kept list of test files**, so the 11 files this round added were
    left out of `dev/run_tests.sh`; it now globs `dev/test_*.py`, with the browser suites
    `dev/test_purlin_report*.py` still held out by `--fast`. Fixed.
26. **`dev/test_e2e_external_refs.sh` check 11 expects `- RULE-1: FORBIDDEN`**, wording the
    anchor dropped at `4fcc16ab`. It fails only where `dev/setup-external-refs.sh` has run.
    Fixing it edits that test file, which stales the approvals it backs.
27. **The `open` filter on the board still counts approved rules** that need a model review,
    while the review list no longer does. `purlin_report` PROOF-13 pins the current meaning, so
    matching them changes that proof.
28. **Proposal: rename the state Recorded to Passed.** Touches `scripts/mcp/purlin/states.py`,
    `references/glossary.md`, the dashboard labels, `specs/mcp/states.md`,
    `specs/dashboard/purlin_report.md`, the skills and the docs. The gate value `recorded` is a
    separate word. Every approval whose rule text names the state goes Stale.
29. **The counts line in `RELEASE_NOTES.md` reads 986 passed**; the sweep now collects 1,083
    tests. `purlin_version` RULE-9 fails locally until the release sweep sets the line (item 3).

## Housekeeping

16. `.purlin/records/` now holds three records per feature per runner plus the developer's;
    retention is working. The first `validated/*` tag will pin the ones that matter.
17. The design system copy under `design/` leaves out the PNG renders (gitignored `*.png`),
    the deck templates, slides and the reference dashboard kit, per A11.
