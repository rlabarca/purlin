# Lane `words`

You are lane `words` of phase 3 of Purlin 0.10.0 (decisions 94, 95 and 96). Purlin is a Claude
Code plugin for spec-driven development that uses itself. This brief is complete in itself; the
files below are where its words come from.

- Worktree: `/Users/richlabarca/LocalCode/purlin-wt/words`, branch `lane/words`, created from
  `main` after P2 merged: `git -C /Users/richlabarca/LocalCode/purlin worktree add
  /Users/richlabarca/LocalCode/purlin-wt/words -b lane/words main`.
- Scratch folder: `<the scratchpad directory your session gives>/lane-words`. Nothing of yours
  goes anywhere else outside the worktree.

## Read first

1. `CLAUDE.md`, `references/writing_style.md`, `references/spec_quality_guide.md`.
2. `dev/plans/three-levels.md` lines 831 to 877 (decisions 94, 95, 96); a later decision amends
   an earlier one.
3. `dev/plans/phase3-plan.md` sections 1, 4 (your row), 6 and 7, and
   `dev/plans/phase3-contracts.md` whole.
4. `dev/plans/phase2-questions.md`, the readings named below, and in
   `dev/plans/phase2-report.md` the numbered questions named below (line 61 onward).
5. `references/glossary.md`, `references/purlin_commands.md`, `references/hard_gates.md`,
   `RELEASE_NOTES.md` (the section "Unreleased — 0.10.0"), `design/readme.md`, and decisions 60
   to 96 whole, since `RELEASE_NOTES.md` must say what 0.10.0 does.

You edit last in spirit: every machine string you write is fixed in `phase3-contracts.md`, and
every sentence around it is yours to write in the writing style, stating exactly the fact given.
Keep every row of every `| Command | Purpose |` table in `references/purlin_commands.md`: every
skill's test reads them.

## The files you own

You write these and no other file. Every other file is read-only for you, the frozen helpers
included: `dev/skill_checks.py`, `dev/mcp_project.py`, `dev/sign_project.py`,
`dev/run_project.py`, `dev/reports_project.py`, `dev/conftest.py`, `dev/fake_claude.py`.

- `references/glossary.md`, `references/purlin_commands.md`, `references/hard_gates.md`,
  `references/writing_style.md` (no change planned)
- `CLAUDE.md`, `RELEASE_NOTES.md`, `README.md` (no change planned)
- `docs/running-and-evidence.md`, `docs/dashboard.md`, `docs/how-purlin-works.md`,
  `docs/getting-started.md`, `docs/raising-the-gate-and-upgrading.md`,
  `docs/review-and-signing.md`, `docs/specs-and-anchors.md` (only the lines of item 7)

`design/readme.md` is not yours and does not change: its "No emoji." line stays (C10). No other
lane owns a file under `docs/`, and no page under `docs/` but these seven changes.

## The work

Each item names its source and the change. Where an item carries a `PENDING OQ<n>` mark that the
orchestrator has not replaced, or reads `REMOVED BY OQ<n>`, leave that item as it stands and
report it. Build every other item.

C12 is binding: the two new facts S1 (a remote runner runs only the tests tied to proofs tagged
for its own system) and S2 (test strength is one share per feature; with mutation testing on,
nothing measured leaves the rule weak) are each stated once, in `references/hard_gates.md`, and
every other file you own points at that home instead of restating them.

1. **`references/hard_gates.md`, the two homes (C12):**
   - S1, one paragraph in "Where a runner runs, and when a project has one" (line 123): a remote
     runner runs only the tests tied to proofs tagged `@env` for its own system; a proof with no
     `@env` is proven by a run on a person's machine (decision 95).
   - S2, one paragraph directly under the gate table (after line 28): test strength is one
     share per feature, in every language (decision 94); with mutation testing on, a feature
     whose share could not be measured leaves its rules `weak` with the reason
     `strength not measured: <reason>` (**PENDING OQ9**); an engine that cannot run on this
     system counts as none and the AI audit alone decides. Line 27's `strong` row keeps its
     words.
   - The `Left to do` table's `no_scope` row (line 79), **PENDING OQ10**: with OQ10's option 1
     its "When it applies" cell reads, word for word (`phase3-plan.md` section 12, item 2):

     ```
     at `signed`, the rule is not signed and its spec names no files; at `strong` and `signed` with mutation testing on, its strong cell reads `weak` because its spec names no code files
     ```

     With options 2 to 4 the row stays.
   - Lines 116 to 117: the clause "The tests a person ran are the tests a runner runs" goes,
     with nothing restated in its place. Line 140, the tag run's cell ("It runs the marked tests
     on a clean machine and nothing else"), and line 207, "A runner runs the marked tests", each
     point at the S1 paragraph in place of "the marked tests".
   - Line 26 (a result counts "on every platform a current section covered") and lines 232 to
     239 ("Platforms"): each section answers for the proofs it lists; `partial` is two systems
     that ran disagreeing; a system a proof is tagged for with no current section reads
     `not run` with `<os>: no run yet` (C4.1). Lines 238 to 239 ("Test strength is independent
     of the system ...") point at the S2 paragraph instead of saying it again.
   - Lines 69 to 81, the table of `Left to do` kinds: C2's kinds, with `to_correct`
     (**PENDING OQ3**) and `to_measure` (**PENDING OQ9**) in their C2 places; line 72,
     `to_fix`, keeps `partial`.
   - Lines 137 to 140: a run on another ref prints C3.8's line (**PENDING OQ23**).
   - Lines 128 to 129: the sentence that begins "A project whose git host is neither GitHub nor
     Azure DevOps" is replaced by this one, word for word (decision 96; `phase3-plan.md`
     section 12, item 3), so the words `neither GitHub nor Azure DevOps` leave the file
     (integration greps for them):

     ```
     Purlin runs tests remotely on GitHub and Azure DevOps. On any other git host the settings read `ci: none`, and setup prints `This git host cannot run tests remotely. Everything on this machine works.`
     ```
2. **`references/glossary.md`:**
   - lines 28 to 31, **suite**: the first test run suggests an entry for each test tool it
     recognises, confirmed together (**PENDING OQ5**);
   - lines 42 to 46, **Left to do**: the printed kinds of C2, with `to correct`
     (**PENDING OQ3**) and `to measure` (**PENDING OQ9**) in their places;
   - lines 58 to 59, **partial**: the tests passed on one system and failed on another; a
     system that has not run reads `not run`;
   - lines 75 to 78, **test strength**: the share of one feature's breaks the tests caught, as a
     percentage, compared with `min_strength`, then a pointer to the S2 paragraph;
   - lines 106 to 111, **remote runner**: its definition stays; one pointer to the S1
     paragraph;
   - line 126, the chain's `passed` row, "on every platform a current section covers": each
     section answers for the proofs it lists.
3. **`references/purlin_commands.md`:**
   - line 33, the `purlin:test` row: "The first run in a project with no test command suggests
     one" becomes "suggests one for each test tool it recognises" (decision 94, **PENDING OQ5**);
   - line 34, the `purlin:audit` row, and the usage block lines 70 to 72: `[--arm-timeout <seconds>]`
     is added to `purlin:audit`'s syntax, and the usage block gains the usage line of C3.2
     (**PENDING OQ11**; with OQ11's second or third option nothing is added), which is,
     character for character,
     `purlin:audit --arm-timeout <seconds>  Give the breaking tool longer per feature`,
     written after the two spaces every line of that block starts with;
   - line 95: the `purlin:init --add <framework>` usage line goes (decision 94); the
     `purlin:init` row of the table stays;
   - line 110, `purlin:test`'s `--remote`: one pointer to the S1 paragraph;
   - "Exit codes", lines 135 to 141: the table becomes contracts C6's table, every row in C6's
     order and every cell copied from C6 character for character, no word added or dropped
     (the new rows for `scripts/export/package.py`, `scripts/review/ai_audit.py` and
     `scripts/init/scaffold.py` included). Its marks are C6's: every
     `the settings file cannot be read` clause is **PENDING OQ1**, `sign.py`'s
     `git could not write the tag` **PENDING OQ16**;
   - lines 143 to 150: the run that stops before running anything also stops on C3.4's line
     (**PENDING OQ1**); with no test command it prints C3.7 R4 (**PENDING OQ5**), which ends on
     `Suggested tests setting: <the entries as one JSON array on one line>`, in place of
     `Suggested for <name>: <run>` and `Suggested entry: <one-line JSON>`;
   - lines 152 to 156: the run's lines R1 (**PENDING OQ4**) and R2, and the unknown-rule line
     `<feature> <RULE-N> is not a rule any spec has. Run purlin:status <feature> to see its rules.`
     (**PENDING OQ15**);
   - lines 158 to 162: a near miss to a rule with one proof suggests that proof (C3.9,
     **PENDING OQ18**);
   - "Path resolution": the one home of C9, one sentence: every Purlin script a skill runs is
     started as `sh "${CLAUDE_PLUGIN_ROOT}/scripts/purlin_python.sh" "${CLAUDE_PLUGIN_ROOT}/scripts/<path>" <args>`,
     which finds Python 3 the way the plugin's server does, `py -3` on Windows included.
4. **`CLAUDE.md`, "Releasing a new version"** (Q79): set the version with
   `bash dev/bump_version.sh <semver>`, commit, run `purlin:sign` at the gate `signed`, which
   writes the signed tag `signed/<version>` once nothing is left to do, and the owner pushes it
   with `git push origin signed/<version>`; the plain version tag goes. P1 already made the
   derived locations two. The design bullet, and its "no emoji anywhere, CLI output included",
   stays as it is (C10).
5. **`RELEASE_NOTES.md`, "Unreleased — 0.10.0":**
   - what is new or changed: a remote run on a system runs only the tests tied to proofs tagged
     for that system; test strength is one share per feature; with breaking on, nothing measured
     leaves a rule weak; the first test run suggests a command for every test tool it
     recognises; a mistake Purlin can see in a spec is warned of with its fix; a settings file
     that cannot be read stops every command (**PENDING OQ1**); `purlin:sign` exits 1 when it
     refused the tag for a reason to fix; the skills start Purlin's scripts through the
     interpreter lookup; each only as the owner's answers leave it;
   - what is gone: the shell command line that printed settings
     (`python3 scripts/mcp/config_engine.py`, Q67), which 0.9.5 shipped. Setup's `--add` is not
     listed: 0.9.5 never shipped it (it came and went inside 0.10.0), and the notes say what is,
     not what was (decision 44); the existing line on `--add-plugin` stays as it is;
   - Windows: the parts are proven on Windows and the whole path on the Mac; the whole path on
     Windows is not walked for 0.10.0;
   - correct every line of the section that decisions 60 to 96 made false, among them the
     trust question, the queue, `[level: ...]` and the per-rule strength, so the section says
     what 0.10.0 does. The owner reviews the section after (handoff step 6).
6. `README.md` and `references/writing_style.md`: read for anything these decisions made false;
   change nothing else, and report what you found.
7. **`docs/`, the lines this phase makes false** (CLAUDE.md "Format reference versioning" step
   4; plan section 7, call 65, and section 11). Lanes `run` and `package` change the format
   files with their code; you fix what they, and this phase, make false in these lines and no
   others (line numbers as on `main` at `b172b3c1c`; read your worktree's copy, since an
   earlier merge may not have touched `docs/` but your own edits shift lines):
   - `docs/running-and-evidence.md` 102 to 113 (the `needs` line, R3, **PENDING OQ20**; which run
     proves an untagged proof, a pointer to the S1 paragraph; `partial`, C4.1), 228 to 235
     (strength is one share per feature; `n/a` is printed nowhere; the time limit's reason,
     **PENDING OQ11**), 296 to 395, the section "When a project has a runner", with 348 in it
     (what a runner runs and writes, a pointer to S1, and the `ci` section's proofs of evidence
     format 5; the separate gate-check step at 348, which decision 83 removed);
   - `docs/dashboard.md` 13 (a later setup asks nothing before each file, Q14) and 67 (the
     `Strong` cell, decisions 73 and 93: no `level`, no `n/a`);
   - `docs/how-purlin-works.md` 102 (what a runner runs, a pointer to S1) and 160 to 162
     (`partial`, C4.1);
   - `docs/getting-started.md` 177 and `docs/raising-the-gate-and-upgrading.md` 24 (setup asks
     nothing before each write, Q14), and 63 (the `--add` row goes, decision 94);
   - `docs/review-and-signing.md` 80 (the command starts through the interpreter lookup, C9);
   - `docs/specs-and-anchors.md` 91 to 94 (a number written twice is warned of, C3.3; the new-id
     sentence of `phase3-plan.md` section 12, item 5) and 140 to 144 (which run proves a proof
     with no `@env`, a pointer to the S1 paragraph).
   Each change says what is, in the writing style; the pages point at `references/` rather than
   restating S1 or S2. Decision 63's reading of every page, after sanity check 3, reads the rest.
   The screenshots are not retaken now.

There are no test files of your own; run `--fast` to see that the skill tests reading
`references/purlin_commands.md` still pass.

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
cd /Users/richlabarca/LocalCode/purlin-wt/words
.venv/bin/python -m pytest dev/test_skill_spec.py dev/test_purlin_agent.py -q      # your own files, whole
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

- Commit on `lane/words` only, with the prefixes of `references/commit_conventions.md`, ending
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
