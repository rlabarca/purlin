# Lane `p2-warnings`

You are lane `p2-warnings` of phase 3 of Purlin 0.10.0 (decisions 94, 95 and 96). Purlin is a Claude
Code plugin for spec-driven development that uses itself. This brief is complete in itself; the
files below are where its words come from.

- Worktree: `/Users/richlabarca/LocalCode/purlin-wt/p2-warnings`, branch `lane/p2-warnings`, created from
  `main` (P2 starts after P1 merged): `git -C /Users/richlabarca/LocalCode/purlin worktree add
  /Users/richlabarca/LocalCode/purlin-wt/p2-warnings -b lane/p2-warnings main`.
- Scratch folder: `<the scratchpad directory your session gives>/lane-p2-warnings`. Nothing of yours
  goes anywhere else outside the worktree.

## Read first

1. `CLAUDE.md`, `references/writing_style.md`, `references/spec_quality_guide.md`.
2. `dev/plans/three-levels.md` lines 831 to 877 (decisions 94, 95, 96); a later decision amends
   an earlier one.
3. `dev/plans/phase3-plan.md` sections 1, 4 (your row), 6 and 7, and
   `dev/plans/phase3-contracts.md` whole.
4. `dev/plans/phase2-questions.md`, the readings named below, and in
   `dev/plans/phase2-report.md` the numbered questions named below (line 61 onward).
5. Readings Q33, Q43, Q44, Q46, Q48, Q53, Q54, Q55, Q12, Q65 and report questions 33, 43, 53,
   54, 55; the fault list item for `schema_spec_format` (report line 55); "Gaps left" for
   `evidence`, `specs` and `schema_spec_format`.

You run alone, after P1 merged and after the orchestrator wrote the owner's answers to every
question into `phase3-contracts.md` (you use OQ1, OQ2, OQ12 and OQ15). An item whose question was answered with its removal option
is skipped.

## The files you own

You write these and no other file. Every other file is read-only for you, the frozen helpers
included: `dev/skill_checks.py`, `dev/mcp_project.py`, `dev/sign_project.py`,
`dev/run_project.py`, `dev/reports_project.py`, `dev/conftest.py`, `dev/fake_claude.py`.

You run alone, so you may write any file an item below names, and any test file item 6 needs:
- `scripts/mcp/purlin/specs.py`, `scripts/mcp/purlin/payload.py`, `scripts/mcp/config_engine.py`,
  `scripts/review/sign.py`, `scripts/init/scaffold.py` (item 5 alone)
- `specs/_anchors/schema_spec_format.md`, `references/formats/spec_format.md`
- `dev/test_schema_spec_format.py`, `dev/test_signatures.py`, and the test files item 6 touches

## The work

Each item names its source and the change. Where an item carries a `PENDING OQ<n>` mark that the
orchestrator has not replaced, or reads `REMOVED BY OQ<n>`, leave that item as it stands and
report it. Build every other item.

1. **The five spec mistakes** (decision 94; C3.3, **PENDING OQ2**): `specs.spec_mistakes` returns
   one line per mistake, in the words of C3.3: a `> Scope:` entry that finds no tracked file
   (through `fingerprint.expand_scope`, imported inside the function; a spec whose every entry
   finds nothing gets only the existing line), two specs with one name (the reader keeps the
   walk-order winner), a rule number written twice (one entry kept in the rule order, so every
   count agrees), a line under `## Proof` that cannot be read, a first line `# Feature: <other>`
   or `# Anchor: <other>` naming another feature. The rules live in the spec-format anchor:
   RULE-2 (gains: a rule number written twice is warned of; its clause "the author assigns them
   in increasing order and never reuses one" stays, as `references/formats/spec_format.md`
   line 80 says), RULE-3 (a proof line that cannot
   be read is warned of), RULE-7 (what Purlin reads: the file name is the spec's name, `# Anchor:`
   makes a spec an anchor wherever it is kept, a first line naming another feature is warned
   of), and two new rules from the next free id (two specs with one name; a scope entry that
   finds no file). One proof per mistake, read from what the status prints, in
   `dev/test_schema_spec_format.py`. PROOF-3's and PROOF-7's checks of this repository's own
   files go (Q54's third option). `references/formats/spec_format.md` says which mistakes are
   warned of, in "Location", the `> Scope:` row, "Rules format", "Proof format" and the heading
   line, and in "Rules format" this sentence, word for word (Q46, Q48, C11; `phase3-plan.md`
   section 12, item 5):

   ```
   A new id is one more than the highest the file has held since it was last written whole; a number deleted since then is never used again.
   ```

   No Format-Version bump.
2. **The two plurals** (L8, L9): the unnumbered-rule warning in `payload.py` and the unread-tags
   warning in `specs.py` read `1 line ... is not numbered` and `1 spec file carries tags ...`
   for one; the plural stays. The unnumbered-rule warning, singular and plural, also ends
   ` Run purlin:spec <feature>.` (C3.1 L8; **PENDING OQ2**: options 1 and 2 add it, options 3
   and 4 leave it off). The payload's rule already knows its feature's name.
3. **`config_engine.config_problem(project_root)`** (C1.9, C3.4; **PENDING OQ1**) and its
   constant: the sentence when `.purlin/config.json` exists and cannot be read (not UTF-8, not
   JSON, JSON that is not an object, an open that failed), None otherwise. No caller yet; lane
   `settings` writes its rule and proofs.
4. **`sign.NOT_A_RULE`** (C3.6, **PENDING OQ15**) reads
   `%s %s is not a rule any spec has. Run purlin:status %s to see its rules.` (feature, rule,
   feature). Add beside it `def not_a_rule(feature, rule)`, which returns the line filled in
   (with OQ15's third option the constant has two `%s` and the function passes two values), and
   make every existing print of the line call it (C1.10); the tests in
   `dev/test_signatures.py` quoting it (around lines 872 to 895) follow.
5. **Setup's line for an engine that cannot run here** (C1.11; **PENDING OQ12**): add
   `NO_ENGINE_HERE` beside `NO_ENGINE` in `scripts/init/scaffold.py`, in OQ12's chosen words, and
   nothing else in that file; with OQ12's removal option skip this item. Lanes `scaffold` and
   `update` print it.
6. **The tree stays green:** run `--fast`; a fixture whose `> Scope:` names a file it never
   creates now prints a warning line; fix every test the new lines disturb, and list each file
   you touched.


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
cd /Users/richlabarca/LocalCode/purlin-wt/p2-warnings
.venv/bin/python -m pytest dev/test_schema_spec_format.py dev/test_specs_reader.py dev/test_states.py dev/test_signatures.py dev/test_config_engine.py -q      # your own files, whole
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

- Commit on `lane/p2-warnings` only, with the prefixes of `references/commit_conventions.md`, ending
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
