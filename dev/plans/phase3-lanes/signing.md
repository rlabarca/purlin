# Lane `signing`

You are lane `signing` of phase 3 of Purlin 0.10.0 (decisions 94, 95 and 96). Purlin is a Claude
Code plugin for spec-driven development that uses itself. This brief is complete in itself; the
files below are where its words come from.

- Worktree: `/Users/richlabarca/LocalCode/purlin-wt/signing`, branch `lane/signing`, created from
  `main` after P2 merged: `git -C /Users/richlabarca/LocalCode/purlin worktree add
  /Users/richlabarca/LocalCode/purlin-wt/signing -b lane/signing main`.
- Scratch folder: `<the scratchpad directory your session gives>/lane-signing`. Nothing of yours
  goes anywhere else outside the worktree.

## Read first

1. `CLAUDE.md`, `references/writing_style.md`, `references/spec_quality_guide.md`.
2. `dev/plans/three-levels.md` lines 831 to 877 (decisions 94, 95, 96); a later decision amends
   an earlier one.
3. `dev/plans/phase3-plan.md` sections 1, 4 (your row), 6 and 7, and
   `dev/plans/phase3-contracts.md` whole.
4. `dev/plans/phase2-questions.md`, the readings named below, and in
   `dev/plans/phase2-report.md` the numbered questions named below (line 61 onward).
5. Readings Q11, Q12, Q13 and report questions 11, 12, 13; "Gaps left" for `signatures`; the
   report's Windows point 4, the home folder.

## The files you own

You write these and no other file. Every other file is read-only for you, the frozen helpers
included: `dev/skill_checks.py`, `dev/mcp_project.py`, `dev/sign_project.py`,
`dev/run_project.py`, `dev/reports_project.py`, `dev/conftest.py`, `dev/fake_claude.py`.

- `scripts/review/sign.py`, `scripts/mcp/purlin/signatures.py`
- `specs/review/signatures.md`
- `dev/test_signatures.py`, `dev/test_tag.py`

## The work

Each item names its source and the change. Where an item carries a `PENDING OQ<n>` mark that the
orchestrator has not replaced, or reads `REMOVED BY OQ<n>`, leave that item as it stands and
report it. Build every other item.

1. **Q11** (C6): `tag_if_met` returns the refusal's kind; `walk` keeps it in its result; `_finish`
   passes it on; `main` exits 1 for uncommitted work (`NO_TAG_WORK`), uncommitted results
   (`NO_TAG_EVIDENCE`), no version (`NO_VERSION`) and a package not committed (`NO_TAG_PACKAGE`),
   at the walk's return (around line 852) and the nothing-waiting return (around line 873), and
   0 when the tag already exists (`NO_TAG_EXISTS`). The module docstring's exit paragraph
   follows. A new rule from the next free id: "`purlin:sign` exits 1 when the tag is refused for
   a reason the person must fix, and 0 when the tag already exists", with one proof per reason
   (tests call `sign.main` or a subprocess, in the "no tag" group of `dev/test_tag.py`).
2. **git failing to write the tag** (C3.6, **PENDING OQ16**): where `git tag -s` fails after the
   package was committed (around line 471), print
   `No tag: git could not write signed/<version>: <git's own message, first line>.` in place of
   `NO_TAG_EXISTS`, and exit 1. One proof. OQ16's other options are in C3.6; in every option
   `NO_TAG_EXISTS` is no longer printed for this case and the exit is 1.
3. **Q12** (C1.10; **PENDING OQ15**): P2 set `NOT_A_RULE` to
   `<feature> <RULE-N> is not a rule any spec has. Run purlin:status <feature> to see its rules.`
   and added `not_a_rule(feature, rule)`, which returns it filled in; print it only through
   `not_a_rule`.
   `main` (around lines 855 to 886) prints it last, just above the summary ending; when every
   rule named is unknown, it prints the line(s) and then the summary ending. RULE-64, PROOF-125
   and PROOF-144 are reworded; tests around lines 872 to 895.
4. **Q13:** RULE-2 and PROOF-2 go with the test under `# purlin: signatures PROOF-2` (around line
   216). RULE-64 covers the case.
5. **Decision 95, fault 4, the home folder:** one helper in `scripts/mcp/purlin/signatures.py`
   finds the home as git does, `HOME`, then `USERPROFILE`, then `os.path.expanduser('~')`;
   `sign.no_key_lines`'s default key path and `signatures.py`'s key path (around line 308) use
   it. The `home` fixture of `dev/test_signatures.py` (around lines 173 to 176) sets `HOME`, and
   `USERPROFILE` too on Windows; PROOF-21, 95 and 22 hold.
6. **Q65, signing** (C1.9, C3.4; **PENDING OQ1**): `main`, after the command line is read and
   before anything else is read or written, prints `config_engine.config_problem(project_root)`'s
   sentence when it answers, writes nothing and exits 1. One new rule, or one proof under an
   existing rule that already says what `purlin:sign` does when it cannot start, with a test
   whose `.purlin/config.json` holds a trailing comma. The module docstring's exit paragraph
   and C6's `sign.py` row (lane `words` writes the table) name it.
7. **Split by claim and one case per proof** (C11): candidates signatures RULE-11, 45, 53.

**You consume** P2's `NOT_A_RULE`, `not_a_rule` and `config_problem`. **You produce** C6's
`sign.py` exit codes, whose cells lane `words` copies from C6; lane
`review` imports `sign.not_a_rule`, so keep its name and its two parameters.


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
cd /Users/richlabarca/LocalCode/purlin-wt/signing
.venv/bin/python -m pytest dev/test_signatures.py dev/test_tag.py -q      # your own files, whole
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

- Commit on `lane/signing` only, with the prefixes of `references/commit_conventions.md`, ending
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
