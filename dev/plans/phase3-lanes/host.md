# Lane `host`

You are lane `host` of phase 3 of Purlin 0.10.0 (decisions 94, 95 and 96). Purlin is a Claude
Code plugin for spec-driven development that uses itself. This brief is complete in itself; the
files below are where its words come from.

- Worktree: `/Users/richlabarca/LocalCode/purlin-wt/host`, branch `lane/host`, created from
  `main` after P2 merged: `git -C /Users/richlabarca/LocalCode/purlin worktree add
  /Users/richlabarca/LocalCode/purlin-wt/host -b lane/host main`.
- Scratch folder: `<the scratchpad directory your session gives>/lane-host`. Nothing of yours
  goes anywhere else outside the worktree.

## Read first

1. `CLAUDE.md`, `references/writing_style.md`, `references/spec_quality_guide.md`.
2. `dev/plans/three-levels.md` lines 831 to 877 (decisions 94, 95, 96); a later decision amends
   an earlier one.
3. `dev/plans/phase3-plan.md` sections 1, 4 (your row), 6 and 7, and
   `dev/plans/phase3-contracts.md` whole.
4. `dev/plans/phase2-questions.md`, the readings named below, and in
   `dev/plans/phase2-report.md` the numbered questions named below (line 61 onward).
5. Readings Q27, Q28, Q29 and report questions 27, 28, 29; "Gaps left" for `host`; the report's
   section on Windows, point 4 (the four probable faults, line 2873).

## The files you own

You write these and no other file. Every other file is read-only for you, the frozen helpers
included: `dev/skill_checks.py`, `dev/mcp_project.py`, `dev/sign_project.py`,
`dev/run_project.py`, `dev/reports_project.py`, `dev/conftest.py`, `dev/fake_claude.py`.

- `scripts/run/host.py`, `scripts/run/ci.py`, `scripts/run/remote.py`, `scripts/run/workflow.py`
- `templates/purlin.yml`, `templates/purlin.azure-pipelines.yml`, `dev/fixtures/consumer-ci/**`
- `specs/run/host.md`
- `dev/test_host.py`, `dev/test_remote.py`, `dev/test_host_pathspec.py`, `dev/test_consumer_ci.py`

## The work

Each item names its source and the change. Where an item carries a `PENDING OQ<n>` mark that the
orchestrator has not replaced, or reads `REMOVED BY OQ<n>`, leave that item as it stands and
report it. Build every other item.

1. **Q27.** Host RULE-26 is retired and its number never reused; RULE-27 keeps the five proofs
   (PROOF-30, 32, 96, 97, 98), re-pointed where needed, text and markers unchanged, and reads as
   one rule: a CI commit from a folder that is not the one the job checked out is refused, and
   with no such folder named every project commits.
2. **Q28** (**PENDING OQ22**): `default_branch()` (around lines 130 to 158) and its use (around
   187 to 189) go. `current_branch()` reads the git host's variables, then HEAD's branch, and
   answers nothing on a detached head (`git rev-parse --abbrev-ref HEAD` answers `HEAD`
   there). With nothing named, `_commit_github` and `_commit_azure` commit nothing and print
   `No branch could be read from the git host or from git, so the results were not committed.`;
   the job's exit code stays the tests' (decision 68). RULE-21, PROOF-21, PROOF-88 and PROOF-89
   go; a new rule from the next free id, "an API commit with no branch named is refused", with
   one proof. Tests around lines 1276 to 1301.
3. **Q29** (**PENDING OQ23**): `no_commit_line` gives, for a ref that is neither a `run/*`
   branch nor a `signed/*` tag,
   `This run is on <ref>, which is neither a run branch nor a signed tag: the tests ran and nothing is written.`;
   the tag line `Tag run: nothing is written. This run reruns the tests on <ref>.` is unchanged.
   A new proof under RULE-28 (test around line 1239).
4. **Decision 95, fault 1, finding `gh` and `az`:** `remote._have` (around lines 382 to 386) and
   `workflow._which` (around lines 213 to 217) use `shutil.which`, which honours `PATHEXT` on
   Windows and needs the exec bit on POSIX; the program is still started as `gh` or `az`, so
   PROOF-24, 55, 66 and the watch arguments stay as they are. Stand-ins (C8): the fake `gh` in
   `dev/test_host.py` (around line 1041) and the fake `az` in `dev/test_remote.py` (around line
   136) are written with the exec bit on POSIX and as `gh.cmd` / `az.cmd` on Windows. Lane
   `scaffold`'s `gh` test builds its own stand-in the same way.
5. **Decision 95, descriptions:** `specs/run/host.md`'s Description and the consumer-CI
   fixture's `dev/fixtures/consumer-ci/specs/core/greeting.md` Description say the runner runs
   the tests of proofs tagged for its system (RULE-1's untagged proof is proven on the person's
   machine; RULE-2's `@env(linux)` proof on a Linux runner).
6. **Q65, the remote run** (C1.9, **PENDING OQ1**): where `remote.py` reads the settings
   (around line 116), a `config_problem` answer is printed and the command exits 1.
7. **One case per proof** (Q8): PROOF-67 (three gates), PROOF-36 (three URLs), PROOF-74 (two
   URLs), PROOF-79 (three results) become one proof per case. **Split by claim** (C11):
   candidates RULE-12, 28, 31.
8. `workflow.NO_REMOTE` does not change (OQ7). `UNKNOWN_HOST` was set by P1; leave it.
9. **SQLite on the runner:** nothing now; the first real Windows run shows whether the runner
   image has `sqlite3` (plan call 50).
10. **Decision 95, the templates' header comments** (C12, S1): in `templates/purlin.yml` (lines 16
    to 21) and `templates/purlin.azure-pipelines.yml` (lines 15 to 19), where a run branch run
    and a tag run each "runs the marked tests", the comment says which tests by pointing at
    `references/hard_gates.md in the Purlin plugin, "Where a runner runs"` (C12's form for a
    file that is not Markdown), and restates nothing. The consumer-CI fixture's copies under
    `dev/fixtures/consumer-ci/**` follow where a test compares them with the templates.

**You consume** P1's `UNKNOWN_HOST` and P2's `config_problem`. **You produce** C3.8's lines and
the `shutil.which` lookup of C8.


## How to number, split and write proofs

- A new id is one more than the highest the spec file has held since it was last written whole
  (`git log -p --follow -- <spec>`); a deleted number is never reused.
- Every proof you write or reword holds one case (one starting situation, one action, what is
  seen) in at most 60 words, names no file of code, function or test framework, and has a test of
  its own with `# purlin: <feature> PROOF-<n>` directly above it. A proof whose test loops over
  gates, inputs or systems with one expected result becomes one proof per case (Q1, Q8).
- Split by claim (decision 94): split a rule of your specs where its text states two or more
  claims, its proofs fall into groups each showing exactly one, and no proof shows two. The first
  claim keeps the id; each other claim takes a new id; proofs keep their ids and text, only their
  `(RULE-N)` changes; markers do not change. Do not split a rule whose claims share every proof.
- Delete outright what is retired: no test that a removed thing is absent, nothing added to
  `dev/test_vocabulary.py`, no reader of an old spelling.
- A format you change updates its file under `references/formats/` in the same commit, with the
  bump the contracts name.

## How to test

```
export PATH=/opt/homebrew/opt/dotnet@8/bin:$PATH
cd /Users/richlabarca/LocalCode/purlin-wt/host
.venv/bin/python -m pytest dev/test_host.py dev/test_remote.py dev/test_host_pathspec.py dev/test_consumer_ci.py -q      # your own files, whole
bash dev/run_tests.sh --fast                     # the fast sweep, in your worktree
```

If `.venv` is missing in the worktree, use `/Users/richlabarca/LocalCode/purlin/.venv/bin/python`.
Do not run the full sweep; integration runs it once.

Before you break code on purpose to see an assertion fail, confirm the test that runs it uses
`dev/fake_claude.py` or no model at all, that no real `claude` is on its `PATH`, and that it
reaches no real git host, `gh`, `az` or network service. Restore the file with
`git checkout -- <that file>`; never `git checkout -- specs/`.

A failure in a test file you do not own: check `phase3-contracts.md` C7. If the contracts predict
it, leave it; otherwise report the test, its assertion and the value it saw. Never edit that file.

## Limits

- Commit on `lane/host` only, with the prefixes of `references/commit_conventions.md`, ending
  each message with the attribution lines your session gives. Push nothing, tag nothing, open no
  pull request.
- Run no `purlin:audit` and no `purlin:sign`, never start the real `claude` program or any real
  service.
- Stage no generated file: `scripts/report/purlin-report.html`, `purlin-report.html`,
  `.purlin/evidence/**`, `.purlin/tests.md`, `.purlin/report-data.js`, screenshots.
- Keep each skill and `agents/purlin.md` within its line ceiling; a change cuts as many lines as
  it adds.
- A call no decision or contract makes: build the rest, leave that thing as it is, report it.
- Before you finish: `git rebase main`, rerun your files and `--fast`, fix your own files where a
  lane merged earlier changed a result the contracts predict.

## Report, as your final message

- The branch and its commits (sha and subject).
- For each spec you own: its highest RULE and PROOF id now, and its rule and proof counts before
  and after.
- Tests in your files before and after, and the `--fast` result.
- Every split, as `<spec> RULE-<old> -> RULE-<a> (<claim>), RULE-<b> (<claim>)`.
- Every proof deleted, moved or re-pointed.
- Every word a person reads that you chose because no decision or contract gave it.
- Every item left as it stands, and why.
- Every failure in a file you do not own.
