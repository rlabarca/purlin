# Lane `upstream`

You are lane `upstream` of phase 3 of Purlin 0.10.0 (decisions 94 to 97). Purlin is a Claude
Code plugin for spec-driven development that uses itself. This brief is complete in itself; the
files below are where its words come from.

- Worktree: `/Users/richlabarca/LocalCode/purlin-wt/upstream`, branch `lane/upstream`, created from
  `main` after P2 merged: `git -C /Users/richlabarca/LocalCode/purlin worktree add
  /Users/richlabarca/LocalCode/purlin-wt/upstream -b lane/upstream main`.
- Scratch folder: `<the scratchpad directory your session gives>/lane-upstream`. Nothing of yours
  goes anywhere else outside the worktree.

## Read first

1. `CLAUDE.md`, `references/writing_style.md`, `references/spec_quality_guide.md`.
2. `dev/plans/three-levels.md` lines 831 to 988 (decisions 94 to 97; decision 97 holds the
   owner's answers); a later decision amends an earlier one.
3. `dev/plans/phase3-plan.md` sections 1, 4 (your row), 6 and 7, and
   `dev/plans/phase3-contracts.md` whole.
4. `dev/plans/phase2-questions.md`, the readings named below, and in
   `dev/plans/phase2-report.md` the numbered questions named below (line 61 onward).
5. Reading Q41 and report question 41; the fault list item for `upstream` (report line 54);
   the report's Windows point 4, the backslash `--path`; `phase3-contracts.md` C13, which is
   the whole of item 6 below, and `phase3-plan.md` section 7, calls 67 to 73.

## The files you own

You write these and no other file. Every other file is read-only for you, the frozen helpers
included: `dev/skill_checks.py`, `dev/mcp_project.py`, `dev/sign_project.py`,
`dev/run_project.py`, `dev/reports_project.py`, `dev/conftest.py`, `dev/fake_claude.py`.

- `scripts/anchor/upstream.py`
- `specs/anchor/upstream.md`
- `dev/test_upstream.py`, `dev/test_upstream_notes.py`
- `references/formats/anchor_format.md` (moved to you from lane `anchors`, plan call 72)

## The work

Each item names its source and the change. The owner's answers are written in (decision 97);
build every item.

1. **Q41** and fault RULE-15: a plain `sync` fetches each distinct source once per run: `sync`
   and `_sync_one` share a fetch cache `{url: (checkout, head, error)}` beside the `ls-remote`
   cache, and every anchor pinned to that source reads from the one checkout; the pin written
   is the `ls-remote` head, as today. RULE-15 stays as written. New proof under RULE-15: two
   anchors pinned from one repository, both behind; `sync` starts exactly one `git clone` naming
   that repository (test near line 578). `dev/test_e2e_external_refs.sh` should still pass; run
   it once.
2. **Decision 95, fault 3, a backslash `--path`:** `--path` is turned to `/` before use, so the
   `> Source:` line and git read it the same everywhere, and `_default_name` (around line 253)
   takes the name after the last separator of either kind. The test of RULE-3's proof (around
   line 288) builds the path with the running system's separator (`os.path.join('specs',
   'no_secrets.md')`), so a Windows run shows the fix. The Windows proof waits for wave W.
3. **Line endings** (plan call 34): `_write` opens with `newline=''` and turns every `\r\n` of
   the text into `\n` before writing, so a synced copy has no carriage return on any system,
   whatever line endings the source held. (The upgrade, lane `update`, keeps each line's ending
   instead, because it edits the project's own files; a copy Purlin composes is not one.) One new
   proof under RULE-11, with its own marked test: a new version of the source written with
   `\r\n` endings is synced, and the copy's bytes hold no carriage return.
4. `drift._looks_like_git` and `drift._ls_remote` keep their behaviour (C8); do not copy them.
5. **Split by claim and one case per proof** (C11) across the spec.
6. **Decision 97, an anchor is a spec in Purlin's format; anchors made from plain text go**
   (contracts C13, word for word; OQ19 and OQ25). Lane `drift` merged before you with
   `drift.source_is_repository`, `drift.NOT_A_SPEC_SOURCE` and `drift.not_a_spec_source`; import
   them, do not copy them.
   - **Delete outright:** `FREE_TEXT_NOTE`, `_free_text`, `is_repository` (its callers use
     `drift.source_is_repository`), the `no_rules` status and its printed line in `_render`,
     the module docstring's sentence "A source that is not a repository is free text ...",
     `add`'s help "or a file of free text" (it reads `a git url`); in `specs/anchor/upstream.md`
     RULE-7 with PROOF-7, 24, 28 and 29, and RULE-14 with PROOF-14, their numbers never reused,
     and the Description's clause "and a source that is free text rather than a repository is
     copied in as an anchor with no rules yet instead"; their tests in `dev/test_upstream.py`
     (the free-text helper around line 245, the tests around lines 359 to 410, and the text-file
     anchor of the test around line 563). No test that any of it is absent.
   - **`add` refuses** a source that is not a spec in Purlin's format kept in a git repository,
     in C13's three cases: a file on disk and a description in words before any process starts;
     a file in a repository at `--path` whose text `parse_rules` reads as holding no rule after
     the fetch, the checkout removed before `add` returns. It returns
     `{"command": "add", "anchor": <name>, "source": <source>, "path": <path>, "status": "error", "error": <text>}`,
     prints the one line `<name>: <text>` and exits 2; nothing is written or changed under
     `specs/`, `specs/_anchors/` is not created, and no file is left under
     `.purlin/runtime/anchors/` by the call. `NOT_A_SPEC`, word for word, with two `%s` (what,
     then the name):
     ```
     not added. %s is not a spec in Purlin's format kept in a git repository. Run purlin:anchor create %s to write its rules in this project.
     ```
     where what is the source as given for a file on disk, the `--path` as given for a file in a
     repository, and `The description given` for words; so the line reads, for example,
     `refunds: not added. policy.txt is not a spec in Purlin's format kept in a git repository. Run purlin:anchor create refunds to write its rules in this project.`
     The check of an unsafe source (RULE-6) still comes first.
   - **`sync`:** `pinned_anchors` covers every anchor carrying a `> Source:`. One whose source
     `drift.source_is_repository` rejects gets the row
     `{"anchor", "source", "path", "pinned", "status": "error", "not_a_spec": true, "error": drift.not_a_spec_source(name, source)}`,
     starts no process, writes nothing, and is printed `<name>: <error>`, for example
     `refunds: its source, policy.txt, is not a spec in Purlin's format kept in a git repository, so it cannot be checked. Run purlin:spec refunds to take out its > Source: and > Pinned: lines and keep it as this project's own anchor.`;
     the command exits 2, as for any source that cannot be read (RULE-9). This holds for
     `sync --check`, `sync <name>` and `sync` with no name. A local anchor, with no `> Source:`,
     is not listed.
   - **New rules** from the next free id (C11), one proof and one marked test per case:
     `add` refuses a source that is not a spec in Purlin's format kept in a git repository,
     prints the refusal, writes nothing and exits 2 (a text file in the project; a description
     in words; a file in a repository with no rule); `sync --check`, `sync <name>` and `sync`
     with no name report an anchor whose `> Source:` names no repository as `error` with the
     reason, start no process for it, write nothing and exit 2 (three proofs; the one for
     `sync` with no name holds two repository anchors and one from a text file, the case
     PROOF-14 had). The Description says an anchor's source is a spec in Purlin's format kept in
     a git repository.
   - **`references/formats/anchor_format.md`**, in the same commit as the code that makes `add`
     refuse (CLAUDE.md "Format reference versioning", step 5): `> Format-Version:` 9 to 10, and
     in "The source: a git URL plus a path", after its first paragraph, word for word
     (`phase3-plan.md` section 12, item 8):
     ```
     The file at the path is a spec in this format that holds at least one rule. `purlin:anchor add` refuses any other source, a file on disk, a description in words or a file with no rule, and writes nothing. A copy whose `> Source:` names no repository reads `error` in `purlin:drift` and in `purlin:anchor sync --check`. A local anchor carries no `> Source:` and is never checked.
     ```
     Grep `docs/`, `skills/`, `references/` and `agents/purlin.md` for the format (CLAUDE.md
     step 4): the lines that change are lanes `skills-author`'s and `words`'s (C13); report any
     other you find.
   - `dev/test_upstream_notes.py`'s "free text" is a `> Note:`'s own words and stays.
   - A sync whose repository file, at the new head, holds no rule is written as today (plan
     section 11); do not build a refusal for it.


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
cd /Users/richlabarca/LocalCode/purlin-wt/upstream
.venv/bin/python -m pytest dev/test_upstream.py dev/test_upstream_notes.py -q      # your own files, whole
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

- Commit on `lane/upstream` only, with the prefixes of `references/commit_conventions.md`, ending
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
