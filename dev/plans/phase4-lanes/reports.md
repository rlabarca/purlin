# Lane `reports` (phase 4, fan-out 1)

You are lane `reports` of phase 4 of Purlin 0.10.0: sanity check 3 applied, with the owner's
answers of decision 98. Purlin is a Claude Code plugin for spec-driven development that uses
itself. This brief is complete in itself; the files below are where its words come from. No
reviewer follows you: you check your own work with the self-check at the end and report.

- Worktree: `/Users/richlabarca/LocalCode/purlin-wt/p4-reports`, branch `p4/reports`, created
  from `main` after P1 merged:
  `git -C /Users/richlabarca/LocalCode/purlin worktree add /Users/richlabarca/LocalCode/purlin-wt/p4-reports -b p4/reports main`.
- Scratch folder: `<the scratchpad directory your session gives>/p4-reports`.
  Nothing of yours goes anywhere else outside the worktree.

## Read first

1. `CLAUDE.md`, `references/writing_style.md`, `references/spec_quality_guide.md`,
   `references/glossary.md`.
2. `dev/plans/three-levels.md` decisions 94 to 98 (decision 98 holds the answers of sanity check
   3); a later decision amends an earlier one.
3. `dev/plans/phase4-plan.md` sections 1, 4 (your row), 5, 6 and 11, and
   `dev/plans/phase4-contracts.md` whole: every line you print or quote is there, word for word.
4. `sanity-3.md` section 7 fault 1; section 6 items 15, 16 and 40; section 5 groups 9, 10 and
   26.
5. `scripts/mcp/purlin/markers.py` lines 800 to 1060 and `references/formats/marker_format.md`.

Section references such as "§6 item 5" are to `dev/plans/sanity-3.md`; "A<n>" is the owner's
answer <n> of decision 98; K-numbers are sections of the contracts.

## The files you own

You write these and no other file. Every other file is read-only for you, the frozen helpers
included: `dev/skill_checks.py`, `dev/mcp_project.py`, `dev/sign_project.py`,
`dev/run_project.py`, `dev/reports_project.py`, `dev/conftest.py`, `dev/fake_claude.py`.

- `scripts/run/reports.py`
- `scripts/mcp/purlin/markers.py`
- `specs/run/reports.md`
- `dev/test_reports.py`
- `references/formats/marker_format.md`

## The work

Build every item. Each names its source and the change; where it names a contract, the contract
is the words.

1. **The status before the first run** (fault 1; call 12). With no suite set,
   `markers.test_files` reads every tracked file whose extension has a test reader in
   `markers.py` (the Python, JS, C# and Go extension sets), so a marked proof with no run reads
   `not run`. reports RULE-3 says which files are read, with and without a suite;
   `marker_format.md` says the same. New proofs: with `tests: []` and a marked test, the
   proof's passed cell reads `not run`; that project's status ends
   `  1 rule to test: purlin:test`; a file of a language with no test reader
   is not read.
2. **Test comments that fail** (§6 items 15, 16, 40; K2.8 reports-1 to reports-3). PROOF-5, 13,
   23 and their tests quote the new lines; `marker_format.md` lines 196, 198 and 199 quote them.
3. **`marker_format.md`** (K4.1): wording only, no Format-Version change.
4. **The suite problems** (§5 group 9): proofs quoting
   `"tests" in .purlin/config.json is not a list`,
   `tests[<i>] is not an object`, `the <name> suite names no files`
   and `the <name> suite is named twice; the second is left out`,
   each as `read_suites` gives it (the run adds `purlin: ` and the step, run-11).
5. **The near-miss reasons** (§5 group 10): one proof per reason quoting it whole: the comment
   that names no id, `` `<kind>` is one character from `<FIXED>` ``, `` `<kind>` is `<FIXED>` in
   lower case ``, `` `<feature>` is one character from the feature `<name>` ``, and PROOF-31,
   90, 91 quote theirs whole.
6. **The report reasons** (§5 group 26): proofs quoting
   `wrote a report at <path> that could not be read` and
   `wrote a report at <path> that is not <fmt>: <error>`.
7. **`> Highest-Rule:`** (K4.2) in `specs/run/reports.md`.

**You produce** for other lanes: reports-1 to reports-3 (K2.8); markers read with no suite.

**You consume**: nothing new.

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
cd /Users/richlabarca/LocalCode/purlin-wt/p4-reports
.venv/bin/python -m pytest dev/test_reports.py -q
bash dev/run_tests.sh --fast
```

If `.venv` is missing in the worktree, use
`/Users/richlabarca/LocalCode/purlin/.venv/bin/python`. Do not run the full sweep; integration
runs it once. A failure in a test file you do not own: check the contracts' K6. If K6 predicts
it, leave it; otherwise report the test, its assertion and the value it saw. Never edit that
file.

## Limits

- Commit on `p4/reports` only, with the prefixes of `references/commit_conventions.md`, each
  message ending with the attribution lines your session gives. Push nothing, tag nothing, open
  no pull request.
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
   return `{}` from `test_files` again with no suite: the `not run` proof fails; (b) print
   reports-3 with its old words: PROOF-23 fails; (c) read a Markdown file for markers with no
   suite: the no-reader proof fails.

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
