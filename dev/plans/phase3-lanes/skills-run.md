# Lane `skills-run`

You are lane `skills-run` of phase 3 of Purlin 0.10.0 (decisions 94, 95 and 96). Purlin is a Claude
Code plugin for spec-driven development that uses itself. This brief is complete in itself; the
files below are where its words come from.

- Worktree: `/Users/richlabarca/LocalCode/purlin-wt/skills-run`, branch `lane/skills-run`, created from
  `main` after P2 merged: `git -C /Users/richlabarca/LocalCode/purlin worktree add
  /Users/richlabarca/LocalCode/purlin-wt/skills-run -b lane/skills-run main`.
- Scratch folder: `<the scratchpad directory your session gives>/lane-skills-run`. Nothing of yours
  goes anywhere else outside the worktree.

## Read first

1. `CLAUDE.md`, `references/writing_style.md`, `references/spec_quality_guide.md`.
2. `dev/plans/three-levels.md` lines 831 to 877 (decisions 94, 95, 96); a later decision amends
   an earlier one.
3. `dev/plans/phase3-plan.md` sections 1, 4 (your row), 6 and 7, and
   `dev/plans/phase3-contracts.md` whole.
4. `dev/plans/phase2-questions.md`, the readings named below, and in
   `dev/plans/phase2-report.md` the numbered questions named below (line 61 onward).
5. Readings Q20, Q25, Q37, Q40, Q65 and report questions 40, 42, 45, 47, 59, 63, 71, 73 (the
   rule-size and skill-spec questions decision 94 answered); `skills/test/SKILL.md` and
   `skills/audit/SKILL.md` whole.

## The files you own

You write these and no other file. Every other file is read-only for you, the frozen helpers
included: `dev/skill_checks.py`, `dev/mcp_project.py`, `dev/sign_project.py`,
`dev/run_project.py`, `dev/reports_project.py`, `dev/conftest.py`, `dev/fake_claude.py`.

- `skills/test/SKILL.md` (118 of 120 lines), `skills/audit/SKILL.md` (105 of 105 lines)
- `specs/skills/skill_test.md`, `specs/skills/skill_audit.md`
- `dev/test_skill_test.py`, `dev/test_skill_audit.py`

## The work

Each item names its source and the change. Where an item carries a `PENDING OQ<n>` mark that the
orchestrator has not replaced, or reads `REMOVED BY OQ<n>`, leave that item as it stands and
report it. Build every other item.

1. **Q42, the test skill's rules split by claim** (decision 94). Read each proof first, then:
   RULE-2 keeps "runs `purlin_run.py` with `--test`" (PROOF-2, 9); a new rule for the exit-code
   line (PROOF-27, 8, 17); a new rule "a test run cannot make an audit or a signature appear"
   (PROOF-28, 29). RULE-5 keeps the two files (PROOF-5); a new rule for `--commit`, its two
   commits in order and `Evidence committed.` / `Evidence unchanged.` (PROOF-32, 11, 37, 33); a
   new rule "never pushes" (PROOF-34); a new rule "ends on the summary and `Left to do`, whose
   first line is the next step" (PROOF-35, 36, 18), merged into RULE-3 instead if the two always
   pass together. RULE-6 keeps the four reasons a feature is selected and the marked test files
   (PROOF-38, 39, 43); a new rule for `purlin:test --all` (PROOF-6, 41); a new rule for the line
   when nothing is selected (PROOF-40, 42). Proofs move unchanged; markers do not change.
2. **Q45, the audit skill's RULE-6 split in three:** RULE-6 keeps what each gate runs, and which
   evidence counts at `signed` (PROOF-6, 37, 38, 13, 40, 41, 14, 42); a new rule for the one line
   `AI audit: <n> rules read, <s> strong, <w> weak.`, the ending on the status table, the summary
   and `Left to do`, and with `--commit` the subject `purlin: evidence at <sha7>` (PROOF-11, 12,
   15, 43); a new rule "an audit cannot make a signature appear, so a rule waiting on one does not
   set the exit code" (PROOF-39, 16).
3. **Decision 94, every tool suggested** (C3.7 R4; **PENDING OQ5**): the test skill's row for the
   run that stops with a suggestion (around line 57) reads the line
   `Suggested tests setting: <the entries as one JSON array on one line>`: show the person each suggested command, ask once,
   and on yes write that array as the `tests` setting with the `purlin_config` tool, then run
   Step 1 again. skill_test RULE-7 and PROOF-12 follow, and `SUGGESTED_ROW` in the test.
4. **Q20** (C3.7 R1; **PENDING OQ4**): where the test skill tells the agent what a rule with no
   test prints (around lines 80, 81 and 88), it names the form
   `<feature> <RULE-N> has no test for <PROOF-N>[, <PROOF-M>...]. Run purlin:build <feature>.`
   (C3.7 R1: every proof with no test, joined `, `) beside the existing one.
5. **Q65** (C3.4; **PENDING OQ1**, whose first option shows the owner this row's words): the
   test skill's Step 2 table gets a row for the line beginning `.purlin/config.json cannot be read:`
   directing `→ Fix the settings file by hand, then run: purlin:test`; its exit-code line (around line 47)
   and the audit skill's (around lines 50 to 53) add "the settings file cannot be read" to the
   causes of `1`. The skill_test rule on exit codes and its proof follow.
6. **Decision 95, a remote run runs only the tests tied to proofs tagged for its system** (C12,
   S1): the test skill's Step 5 (lines 96 to 103), once, and the audit skill's paragraph on the
   remote runner (around line 57) point at `references/hard_gates.md`, "Where a runner runs",
   in a clause, and do not restate the rule. Where a line now says something false (for
   example that a runner runs the same tests a person ran), that clause goes. In Step 5 the
   sentence `An untagged proof runs anywhere.` goes, and the pointer stands in its place.
6b. **The test skill's Step 5, the line for a proof tagged for another system** (C3.7 R3;
   **PENDING OQ20**): Step 5 quotes today's per-proof line
   `<feature> PROOF-N needs Windows; this machine is macOS. Run purlin:test --remote.`
   (lines 99 to 100). It quotes R3's one line per system instead, word for word:
   `<n> proofs need <System>; this machine is <System>. Run purlin:test --remote.` (for one,
   `1 proof needs <System>; this machine is <System>. Run purlin:test --remote.`). With OQ20's second option the quoted line stays;
   with its third (no line), Step 5 says the list of work left counts such rules as
   `rules to test on <System>: purlin:test --remote` and quotes no line. Its sentence on
   `partial` says a rule reads `partial` where two systems that each ran disagree (C4.1).
   skill_test's proofs that quote the old line follow. Cut as many lines as you add (120).
7. **Decision 94 and Q37, strength** (C12, S2; **PENDING OQ9**, **PENDING OQ11**): the audit
   skill's Step 2 (around lines 63 to 66) drops any sentence that says strength is worked out per
   rule, and points at `references/hard_gates.md` (the paragraph under the gate table) for what
   the strong cell reads when nothing was measured, in one clause; where OQ9 kept
   `to_measure`, it names the line `rules to measure: purlin:audit` among the lines an audit
   clears. With OQ11's first option the audit skill's usage block gains the usage line of
   C3.2, which is, character for character,
   `purlin:audit --arm-timeout <seconds>  Give the breaking tool longer per feature`,
   starting in the first column as the block's other lines do, and Step 1 says
   to pass `--arm-timeout <seconds>` on to the run script when the person gave it (the run
   script already reads it); skill_audit gains a rule and one proof for it. Cut as many lines
   as you add (105).
8. **Q25** (C3.10, **PENDING OQ17**): the audit skill (around lines 71 to 72) says the audit
   reader prints the notes under `What the audit noted`, after the findings.
9. **The interpreter lookup** (C9): test skill line 29 and audit skill line 33 read
   `sh "${CLAUDE_PLUGIN_ROOT}/scripts/purlin_python.sh" "${CLAUDE_PLUGIN_ROOT}/scripts/run/purlin_run.py" --test`
   (and `--audit`). The proofs that quote the script path on one line still hold; any that quotes
   `python3` follows.
10. **Decision 94, instruction rules:** skill_test RULE-2 and RULE-7, skill_audit RULE-2, and every
    other rule of both specs, say what the skill tells the agent.
11. **Q40's reason, applied** (C11, **PENDING OQ13**): the damaged-copy proofs of skill_test
    (about 24) and skill_audit (about 32) leave the specs, each kept as a second assertion in
    its guarded test. With OQ13's second or third option they stay as they are.
12. **Split by claim** (C11) for the other rules, each RULE-1 included.


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
cd /Users/richlabarca/LocalCode/purlin-wt/skills-run
.venv/bin/python -m pytest dev/test_skill_test.py dev/test_skill_audit.py -q      # your own files, whole
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

- Commit on `lane/skills-run` only, with the prefixes of `references/commit_conventions.md`, ending
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
