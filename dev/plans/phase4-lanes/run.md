# Lane `run` (phase 4, fan-out 1)

You are lane `run` of phase 4 of Purlin 0.10.0: sanity check 3 applied, with the owner's answers
of decision 98. Purlin is a Claude Code plugin for spec-driven development that uses itself.
This brief is complete in itself; the files below are where its words come from. No reviewer
follows you: you check your own work with the self-check at the end and report.

- Worktree: `/Users/richlabarca/LocalCode/purlin-wt/p4-run`, branch `p4/run`, created from
  `main` after P1 merged:
  `git -C /Users/richlabarca/LocalCode/purlin worktree add /Users/richlabarca/LocalCode/purlin-wt/p4-run -b p4/run main`.
- Scratch folder: `<the scratchpad directory your session gives>/p4-run`. Nothing
  of yours goes anywhere else outside the worktree.

## Read first

1. `CLAUDE.md`, `references/writing_style.md`, `references/spec_quality_guide.md`,
   `references/glossary.md`.
2. `dev/plans/three-levels.md` decisions 94 to 98 (decision 98 holds the answers of sanity check
   3); a later decision amends an earlier one.
3. `dev/plans/phase4-plan.md` sections 1, 4 (your row), 5, 6 and 11, and
   `dev/plans/phase4-contracts.md` whole: every line you print or quote is there, word for word.
4. `sanity-3.md` section 6 items 14, 17, 40 and 41; section 7 faults 4, 8, 9, 17, 19 and 21;
   section 11 questions 3 and 15; section 5 rows 4, 14 and 37 and groups 18, 21, 22, 23 and 24.
5. `scripts/run/purlin_run.py` whole; `scripts/mcp/purlin/frameworks.py`;
   `references/supported_frameworks.md`.

Section references such as "§6 item 5" are to `dev/plans/sanity-3.md`; "A<n>" is the owner's
answer <n> of decision 98; K-numbers are sections of the contracts.

## The files you own

You write these and no other file. Every other file is read-only for you, the frozen helpers
included: `dev/skill_checks.py`, `dev/mcp_project.py`, `dev/sign_project.py`,
`dev/run_project.py`, `dev/reports_project.py`, `dev/conftest.py`, `dev/fake_claude.py`.

- `scripts/run/purlin_run.py`
- `scripts/run/evidence.py`
- `scripts/mcp/purlin/frameworks.py`
- `specs/run/run_script.md`
- `specs/run/evidence_writer.md`
- `dev/test_run_script.py`
- `dev/test_evidence_writer.py`
- `references/formats/evidence_format.md`
- `references/supported_frameworks.md`

## The work

Build every item. Each names its source and the change; where it names a contract, the contract
is the words.

1. **`--help`** (fault 19; run-1). run_script RULE-1 says `--help` and `-h` print the usage and
   exit 0; one proof each.
2. **The two flag lines** (§6 items 40, 41; run-2, run-3): PROOF-146 and a new proof quote them
   whole.
3. **An unknown feature** (§6 item 17; run-4): PROOF-2 quotes it whole.
4. **No test tool** (A15; run-5; K3.10): the line, its proof, and the page in
   `references/supported_frameworks.md` where it quotes it.
5. **Evidence is missing** (§6 item 14; run-6 to run-10): each line with its step; the timeout
   names `purlin:test` or `purlin:audit` by the run's own action. New proofs for run-6, run-7
   and run-9; PROOF-8, 156, 157, 158 and reports' quotes hold where they quote the beginning.
6. **The suite problems** (§6 item 40; run-11): the run prints each with the step; one proof.
7. **A proof with no test is named** (fault 17; run-12; call 10). R2 stays only for a rule with
   no proof; run_script RULE-67 says so; PROOF-210 and its test follow; one proof that a rule
   whose only proof has no test prints `has no test for PROOF-<n>`.
8. **The dirty heading** (fault 21; run-13). evidence_writer RULE-20 says the heading names
   uncommitted changes where the newest section is dirty; one proof.
9. **jest-junit by the lock file** (fault 9; run-14): one proof each for `yarn.lock` and
   `pnpm-lock.yaml`; PROOF-134 keeps npm for a project with neither.
10. **jest and `{files}`** (fault 4; call 8): the entry of K2.5 in `frameworks.py` and
    `references/supported_frameworks.md` (line 93 and the table); one proof that a run naming
    files hands them to jest as files (the command line puts them before `--reporters`),
    PROOF-130 and PROOF-133 hold.
11. **Examples in documentation** (A3; fault 8; call 9): the pytest entry carries
    `--doctest-modules` where a listed file names it (K2.5); one proof each way. The interpreter
    stays `python3` and `py -3` (decision 97).
12. **Evidence format wording** (A8; K4.1): `references/formats/evidence_format.md` line 189
    reads "of every anchor it requires, transitively"; no Format-Version change.
13. **The three run lines** (§5 row 4): proofs quoting `Running the <suite> suite.`,
    `Markers: <t> tied to a test, <u> not tied.` and
    `Ran <suite> on <n> feature(s).` in that order before the table.
14. **mutmut's advice** (§5 row 14): `references/supported_frameworks.md`'s pytest section
    carries the advice about dotted imports, `mutants/` and `--deselect` that
    `docs/running-and-evidence.md` lines 241-244 hold, where it does not already.
15. **An evidence conflict** (§5 row 37): evidence_writer gains a rule, "A test run over a
    feature whose evidence file was resolved to either side of a merge rewrites that system's
    section", and one proof.
16. **`.purlin/tests.md`** (§5 group 18): proofs quoting
    `Each row is the newest run of that feature, whoever made it; the source in the last column says whose run it was.`
    and `No feature has been run yet.`
17. **The run's other lines** (§5 groups 21 to 24): one proof per argument refusal of
    `parse_args`, quoted as `purlin: <error>.`;
    `The <suite> suite printed nothing.`; the timeout reasons; run-4.
18. **Adjust to earlier lanes** (K6): run_script PROOF-91
    (`no run on <System> yet`), PROOF-177 to 182 (core-6), and
    `dev/test_evidence_writer.py` near line 1361, where setup now commits with `--yes`.
19. **`> Highest-Rule:`** (K4.2) in `specs/run/run_script.md` and
    `specs/run/evidence_writer.md`.

**You produce** for other lanes: run-1 to run-14 (K2.5); the jest and pytest entries.

**You consume**: core-6, anchors-3, the setup commit of K3.9 (K6); reports-1 to reports-3.

## How to number, split and write proofs (contracts K7)

- A new id is one more than the highest the spec has ever held: the larger of its
  `> Highest-Rule:` and the highest of its own `RULE-`/`PROOF-` ids in
  `git log -p --follow -- <spec>` (its own lines only, not ids a proof or another
  spec names). A deleted number is never reused. Every spec you own carries
  `> Highest-Rule: <n>` after its last other `>` line, raised with every rule you add.
- Every proof you write or reword holds one case (one starting situation, one action, what is
  seen) in at most 60 words; a list of like inputs sharing one action and one kind of result is
  one case. It names no source file, no test and no test framework; a library's public names and
  error types may appear. It has a test of its own with `# purlin: <feature> PROOF-<n>`
  (in the file's comment syntax) directly above it.
- A statement of `sanity-3.md` section 5 gets a rule and one proof per line or case, each
  quoting the printed line character for character as the code prints it after your change.
- Split a rule of yours where its text states two claims whose proofs fall into groups each
  showing one: the first claim keeps the id, each other claim takes a new id, proofs keep their
  ids and text and only their `(RULE-N)` changes. List each split.
- Delete outright what is retired: no test that a removed thing is absent, nothing added to
  `dev/test_vocabulary.py`.
- A format you change updates its file under `references/formats/` in the same commit, with the
  Format-Version K4 names (none but the spec format changes number).

## How to test

```
export PATH=/opt/homebrew/opt/dotnet@8/bin:$PATH
cd /Users/richlabarca/LocalCode/purlin-wt/p4-run
.venv/bin/python -m pytest dev/test_run_script.py dev/test_evidence_writer.py -q
bash dev/run_tests.sh --fast
```

If `.venv` is missing in the worktree, use
`/Users/richlabarca/LocalCode/purlin/.venv/bin/python`. Do not run the full sweep; integration
runs it once. A failure in a test file you do not own: check the contracts' K6. If K6 predicts
it, leave it; otherwise report the test, its assertion and the value it saw. Never edit that
file.

## Limits

- Commit on `p4/run` only, with the prefixes of `references/commit_conventions.md`, each message
  ending with the attribution lines your session gives. Push nothing, tag nothing, open no pull
  request.
- Run no `purlin:audit` and no `purlin:sign`; never start the real `claude` program, a real git
  host, `gh`, `az` or any network service.
- Stage no generated file: `scripts/report/purlin-report.html`, `purlin-report.html`,
  `.purlin/evidence/**`, `.purlin/tests.md`, `.purlin/report-data.js`,
  `.github/workflows/purlin.yml`, `docs/images/**`.
- Keep each skill and `agents/purlin.md` within its line ceiling (status 100, test 120, build
  130, init 250, audit 105, sign 185, export 90, spec 210, spec-from-code 130, drift 150, anchor
  160, agent 135): a change cuts as many lines as it adds.
- A call no decision or contract makes: build the rest, leave that thing as it is, report it. A
  word a person reads that the contracts do not give: do not choose it; leave the line as it is
  and report it.
- Do not touch `/Users/richlabarca/LocalCode/purlin-wt/winfix-1`, `docs/` or `README.md`.
- Before you finish: `git rebase main`, rerun your files and `--fast`, fix your own files
  where a lane merged earlier changed a result K6 predicts.

## Self-check (run it, then report each result)

1. Every proof you wrote or reworded: one case, at most 60 words (count them), and a test of its
   own with its marker directly above it. List any that fails.
2. Every printed line you built or quote: character for character as K2 and K3 give it. Grep
   your files for each old form in K2 for your lane; none remains.
3. No generated file is staged: `git diff --cached --name-only main` names none of
   `scripts/report/purlin-report.html`, `purlin-report.html`, `.purlin/evidence/**`,
   `.purlin/tests.md`, `.purlin/report-data.js`, `.github/workflows/purlin.yml`,
   `docs/images/**`.
4. No id reused: for each spec you own, every RULE and PROOF id you added is above the highest
   that spec had ever held before you began (K7), and its `> Highest-Rule:` is its highest
   rule number now.
5. Break each of these on purpose, one at a time, run its test, see it fail, then restore the
   file with `git checkout -- <file>` (never `git checkout -- specs/`): (a)
   put `{files}` after `--reporters` again: the jest proof fails; (b) refuse `--help` again: its
   proof fails; (c) print `has no test.` for a rule whose only proof has no test: the
   fault-17 proof fails.

## Report, as your final message

- The branch and its commits (sha and subject).
- For each spec you own: its highest RULE and PROOF id, its `> Highest-Rule:`, and its rule
  and proof counts before and after.
- Tests in your files before and after, and the `--fast` result.
- Each item of "The work": done, or left and why.
- Every split, as
  `<spec> RULE-<old> -> RULE-<a> (<claim>), RULE-<b> (<claim>)`, and every
  proof deleted, moved or re-pointed.
- Every word a person reads that you had to write and the contracts did not give.
- Every failure in a file you do not own.
- The self-check: each of its five results, and for the breaks, the test that failed.
