# Lane `anchors`

You are lane `anchors` of phase 3 of Purlin 0.10.0 (decisions 94, 95 and 96). Purlin is a Claude
Code plugin for spec-driven development that uses itself. This brief is complete in itself; the
files below are where its words come from.

- Worktree: `/Users/richlabarca/LocalCode/purlin-wt/anchors`, branch `lane/anchors`, created from
  `main` after P2 merged: `git -C /Users/richlabarca/LocalCode/purlin worktree add
  /Users/richlabarca/LocalCode/purlin-wt/anchors -b lane/anchors main`.
- Scratch folder: `<the scratchpad directory your session gives>/lane-anchors`. Nothing of yours
  goes anywhere else outside the worktree.

## Read first

1. `CLAUDE.md`, `references/writing_style.md`, `references/spec_quality_guide.md`.
2. `dev/plans/three-levels.md` lines 831 to 877 (decisions 94, 95, 96); a later decision amends
   an earlier one.
3. `dev/plans/phase3-plan.md` sections 1, 4 (your row), 6 and 7, and
   `dev/plans/phase3-contracts.md` whole.
4. `dev/plans/phase2-questions.md`, the readings named below, and in
   `dev/plans/phase2-report.md` the numbered questions named below (line 61 onward).
5. Readings Q44, Q49, Q50, Q51 and report questions 44, 49, 50, 51; the report's "Gaps left"
   for `specs`, `evidence`, `schema_spec_format` and `security_no_dangerous_patterns`, and its
   "Test files that skip on Windows today" (line 3007).

## The files you own

You write these and no other file. Every other file is read-only for you, the frozen helpers
included: `dev/skill_checks.py`, `dev/mcp_project.py`, `dev/sign_project.py`,
`dev/run_project.py`, `dev/reports_project.py`, `dev/conftest.py`, `dev/fake_claude.py`.

- `scripts/mcp/purlin/specs.py`, `scripts/mcp/purlin/fingerprint.py`, `scripts/mcp/purlin/evidence.py`
- `specs/mcp/specs.md`, `specs/mcp/evidence.md`, `specs/_anchors/schema_spec_format.md`,
  `specs/_anchors/security_no_dangerous_patterns.md`
- `dev/test_specs_reader.py`, `dev/test_schema_spec_format.py`, `dev/test_security.py`,
  `dev/test_fingerprint.py`, `dev/test_evidence_reader.py`
- `references/formats/spec_format.md`, `references/formats/anchor_format.md`

## The work

Each item names its source and the change. Where an item carries a `PENDING OQ<n>` mark that the
orchestrator has not replaced, or reads `REMOVED BY OQ<n>`, leave that item as it stands and
report it. Build every other item.

P2 already put the five spec-mistake warnings into `specs.py`, the anchor's RULE-2, 3 and 7
and two new anchor rules, with their proofs. Do not redo them.

1. **Q44.** Specs RULE-4, RULE-5 and RULE-6 go, with PROOF-5, 20, 21, 22 (RULE-4), PROOF-6, 23
   (RULE-5), PROOF-7 (RULE-6) and their tests. `> Requires: schema_spec_format` stays. First
   check each deleted case against the anchor's proofs (PROOF-9, 25 to 33, 10, 36 to 43): a case
   they do not show (specs PROOF-5 and PROOF-21, an unknown tag read through a whole scan, the
   spec named and reading stopped) moves into `specs/_anchors/schema_spec_format.md` as a proof
   of its own with a test in `dev/test_schema_spec_format.py`.
2. **Q49.** The C# `Process.Start(` form leaves security RULE-1: the `.cs` row of the RULE-1 table
   in `dev/test_security.py` (around line 86) and PROOF-20 and PROOF-21 with their tests go. The
   Description's "six file types" stays true through RULE-2, 4 and 5.
3. **Q50** (P1 changed the one start to `subprocess.Popen([*command], ...)`): every
   `subprocess.Popen(` under `scripts/` is held to a first argument that is a list written in
   place; `Popen(*argv)` is not accepted; `run(*argv)` stays accepted (PROOF-36). PROOF-38 flips
   to the case "a `subprocess.Popen(` handed a name is found, naming the file and line". The
   check is near `dev/test_security.py:181`.
4. **Q51.** `system(` and `passthru(` leave RULE-1's PHP list and stay in RULE-3 alone; PROOF-19
   is reworded and loses its two planted files; `dev/test_security.py` around line 85.
5. **Decision 95, the unreadable spec on Windows** (the six tests): the test of specs RULE-14
   (`test_a_spec_that_cannot_be_read_is_skipped`, PROOF-15 or its current id) locks the file the
   Windows way where `os.name == 'nt'` (open it with `msvcrt.locking`, or `ctypes`
   `CreateFileW` with share mode 0, held for the scan) and keeps `chmod` elsewhere; its skip for
   a root user on POSIX stays. No product change: `specs.scan_specs` already catches `OSError`.
6. **Split by claim and one case per proof** (C11) across specs, evidence, the spec-format anchor
   (candidates: RULE-2, 9, 10) and the security anchor. Evidence RULE-5 keeps "is listed as
   unmatched": P2's warning now shows the list.

**You consume** P1's `Popen([*command], ...)` and P2's anchor rules. **You produce** nothing
another lane reads.


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
cd /Users/richlabarca/LocalCode/purlin-wt/anchors
.venv/bin/python -m pytest dev/test_specs_reader.py dev/test_schema_spec_format.py dev/test_security.py dev/test_fingerprint.py dev/test_evidence_reader.py -q      # your own files, whole
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

- Commit on `lane/anchors` only, with the prefixes of `references/commit_conventions.md`, ending
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
