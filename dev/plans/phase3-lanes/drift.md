# Lane `drift`

You are lane `drift` of phase 3 of Purlin 0.10.0 (decisions 94 to 97). Purlin is a Claude
Code plugin for spec-driven development that uses itself. This brief is complete in itself; the
files below are where its words come from.

- Worktree: `/Users/richlabarca/LocalCode/purlin-wt/drift`, branch `lane/drift`, created from
  `main` after P2 merged: `git -C /Users/richlabarca/LocalCode/purlin worktree add
  /Users/richlabarca/LocalCode/purlin-wt/drift -b lane/drift main`.
- Scratch folder: `<the scratchpad directory your session gives>/lane-drift`. Nothing of yours
  goes anywhere else outside the worktree.

## Read first

1. `CLAUDE.md`, `references/writing_style.md`, `references/spec_quality_guide.md`.
2. `dev/plans/three-levels.md` lines 831 to 988 (decisions 94 to 97; decision 97 holds the
   owner's answers); a later decision amends an earlier one.
3. `dev/plans/phase3-plan.md` sections 1, 4 (your row), 6 and 7, and
   `dev/plans/phase3-contracts.md` whole.
4. `dev/plans/phase2-questions.md`, the readings named below, and in
   `dev/plans/phase2-report.md` the numbered questions named below (line 61 onward).
5. Readings Q30, Q31, Q32, Q78 and report questions 30, 31, 32, 78; the fault list items for
   `drift` and `skill_drift` (report lines 52, 58, 59).

## The files you own

You write these and no other file. Every other file is read-only for you, the frozen helpers
included: `dev/skill_checks.py`, `dev/mcp_project.py`, `dev/sign_project.py`,
`dev/run_project.py`, `dev/reports_project.py`, `dev/conftest.py`, `dev/fake_claude.py`.

- `scripts/mcp/purlin/drift.py`, `specs/mcp/drift.md`, `dev/test_drift.py`
- `references/drift_criteria.md`
- `skills/drift/SKILL.md` (111 of 150 lines), `specs/skills/skill_drift.md`, `dev/test_skill_drift.py`

## The work

Each item names its source and the change. The owner's answers are written in (decision 97);
build every item.

1. **Q30.** `_eng_view` (around lines 454 to 525) counts a path deleted in the range under every
   spec whose `> Scope:` entry covers it: a file entry equal to the path, a folder entry that is
   a prefix of it, a glob that matches it. It joins that spec's
   `<n> files changed under <spec>'s scope`. A deleted path no scope covers joins the line of
   files no spec covers, with that line's exclusions. RULE-7 and RULE-8 say a deleted file
   counts; one proof per case from the next free id. `references/drift_criteria.md` (around line
   70, "A file deleted in the range is not on disk and is in neither list.") is rewritten to say
   so.
2. **Q31.** `not_audited` goes from `_qa_view` (around lines 558 to 560); PROOF-49 says the QA
   view carries exactly `left`, `lines`, `specs_uncommitted` and `tests_changed`; its test around
   line 1072; its row in `references/drift_criteria.md` (around line 76) goes.
   `Criteria-Version` goes from 9 to 10.
3. **Q32** and fault `drift` RULE-10: `check_pin` (around line 115) stops returning None for a
   source `_looks_like_git` rejects: every source that passes `source_url_is_safe` and that
   `source_is_repository` (item 3b) accepts is asked with one cached `git ls-remote`, and one
   that cannot be read gives an `error` row. New proof under RULE-10: an anchor pinned to
   `https://dev.azure.com/acme/p/_git/policies`, which cannot be reached, reads `error`. Keep
   `_looks_like_git(url)` and `_ls_remote(project_root, url)` with today's names and behaviour:
   `scripts/anchor/upstream.py` imports both (C8). The comment above `_ABSOLUTE_WINDOWS_PATH`
   (around line 138) that calls a Windows path "free text" is reworded to what the pattern is
   for, or goes with the filter.
3b. **Decision 97, an anchor is a spec in Purlin's format** (contracts C13, OQ19 and OQ25). You
   produce, for lane `upstream`, which imports them (C8):
   - `source_is_repository(project_root, source) -> bool`: false when the value holds whitespace
     (a description in words) or names a file that exists, joined to the project root or as
     written (a file on disk); true otherwise.
   - `NOT_A_SPEC_SOURCE`, word for word, with two `%s` (the `> Source:` value as written, then
     the anchor's name):
     ```
     its source, %s, is not a spec in Purlin's format kept in a git repository, so it cannot be checked. Run purlin:spec %s to take out its > Source: and > Pinned: lines and keep it as this project's own anchor.
     ```
     and `not_a_spec_source(name, source) -> str`, which returns it filled in.
   - `check_pin` answers `{"status": "error", "remote_sha": None, "not_a_spec": True}` for a
     source `source_is_repository` rejects, before any process is handed it; `pin_report`'s row
     carries `not_a_spec: True` and `error: not_a_spec_source(name, source)`; `_anchor_line`
     prints `anchor <name>: <error>` for such a row, so the engineer view reads, for example,
     `anchor refunds: its source, policy.txt, is not a spec in Purlin's format kept in a git repository, so it cannot be checked. Run purlin:spec refunds to take out its > Source: and > Pinned: lines and keep it as this project's own anchor.`
   - `specs/mcp/drift.md`: a rule from the next free id, "The engineer view reports an anchor
     whose `> Source:` names no repository, words or a file on disk, as `error` with the line
     that names `purlin:spec`, and no process is handed the source", with two proofs, one for a
     text file in the project and one for a description in words; `dev/test_drift.py` their
     tests.
   - `references/drift_criteria.md`, "Anchors behind": the table gains, after "The source cannot
     be read", the row
     `| The source names no repository: words, or a file on disk | `anchor <name>: its source, <source>, is not a spec in Purlin's format kept in a git repository, so it cannot be checked. Run purlin:spec <name> to take out its > Source: and > Pinned: lines and keep it as this project's own anchor.` |`,
     under the one Criteria-Version bump, 9 to 10, of item 2. The paragraph above the table
     ("For every anchor carrying a `> Source:`, drift runs one cached `git ls-remote`") says a
     source that names no repository is reported without one.
   A local anchor, with no `> Source:`, is never asked (C13).
4. **Q78** and fault `skill_drift` (the 40-character sha): the sample views, the pm, eng and qa
   blocks and their sentences (around lines 54 to 88 of `skills/drift/SKILL.md`), go; the skill
   points at `references/drift_criteria.md`, which it already names in Step 1.
5. **Decision 94, instruction rules:** skill_drift RULE-2 says "the skill tells the agent to take
   its data from the `drift` tool and to show the lines it returns".
6. **Q40's reason, applied** (C11, OQ13): skill_drift's damaged-copy proofs (about 21) leave
   the spec, each kept as a second assertion in the test it guards.
7. **Q65, the drift tool** (C1.9, C3.4; OQ1): `drift.drift`, before anything is
   read, returns `config_engine.config_problem(project_root)`'s sentence alone as the tool's
   text, in place of the JSON, when it answers, and writes nothing (a tool has no exit code;
   lane `settings`'s server check answers the same sentence first for a call through the
   server, and this covers every other caller). One new drift rule with one proof, calling the
   tool on a project whose `.purlin/config.json` holds a trailing comma.
8. **Split by claim and one case per proof** (C11) across drift and skill_drift.

Check `dev/test_skill_drift.py` PROOF-27, which reads the criteria's line kinds: Q30 adds no
kind. Keep `dev/test_drift.py`'s `_rmtree` as it is: `dev/test_upstream.py` imports it.


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
cd /Users/richlabarca/LocalCode/purlin-wt/drift
.venv/bin/python -m pytest dev/test_drift.py dev/test_skill_drift.py -q      # your own files, whole
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

- Commit on `lane/drift` only, with the prefixes of `references/commit_conventions.md`, ending
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
