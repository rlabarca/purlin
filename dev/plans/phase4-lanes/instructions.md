# Lane `instructions` (phase 4, fan-out 1)

You are lane `instructions` of phase 4 of Purlin 0.10.0: sanity check 3 applied, with the
owner's answers of decision 98. Purlin is a Claude Code plugin for spec-driven development that
uses itself. This brief is complete in itself; the files below are where its words come from. No
reviewer follows you: you check your own work with the self-check at the end and report.

- Worktree: `/Users/richlabarca/LocalCode/purlin-wt/p4-instructions`, branch `p4/instructions`,
  created from `main` after P1 merged:
  `git -C /Users/richlabarca/LocalCode/purlin worktree add /Users/richlabarca/LocalCode/purlin-wt/p4-instructions -b p4/instructions main`.
- Scratch folder:
  `<the scratchpad directory your session gives>/p4-instructions`. Nothing of
  yours goes anywhere else outside the worktree.

## Read first

1. `CLAUDE.md`, `references/writing_style.md`, `references/spec_quality_guide.md`,
   `references/glossary.md`.
2. `dev/plans/three-levels.md` decisions 94 to 98 (decision 98 holds the answers of sanity check
   3); a later decision amends an earlier one.
3. `dev/plans/phase4-plan.md` sections 1, 4 (your row), 5, 6 and 11, and
   `dev/plans/phase4-contracts.md` whole: every line you print or quote is there, word for word.
4. `sanity-3.md` section 8 item 10; section 5 rows 1 and 3.
5. `agents/purlin.md` whole.

Section references such as "§6 item 5" are to `dev/plans/sanity-3.md`; "A<n>" is the owner's
answer <n> of decision 98; K-numbers are sections of the contracts.

## The files you own

You write these and no other file. Every other file is read-only for you, the frozen helpers
included: `dev/skill_checks.py`, `dev/mcp_project.py`, `dev/sign_project.py`,
`dev/run_project.py`, `dev/reports_project.py`, `dev/conftest.py`, `dev/fake_claude.py`.

- `agents/purlin.md`
- `specs/instructions/purlin_agent.md`
- `specs/instructions/purlin_version.md`
- `specs/instructions/purlin_output.md`
- `dev/test_purlin_agent.py`
- `dev/test_purlin_version.py`
- `dev/test_purlin_output.py`
- `dev/bump_version.sh`
- `.github/workflows/version-check.yml`

## The work

Build every item. Each names its source and the change; where it names a contract, the contract
is the words.

1. **`sync_status` and the project root** (§8 item 10; K3.12): `agents/purlin.md`'s first call
   gains K3.12's clause; 135 lines at most, so a line is cut elsewhere. purlin_agent gains a
   proof reading the clause.
2. **Python 3.9** (§5 row 1; call 18): purlin_output gains a rule, "Setup, a test run and the
   status run on Python 3.9", with one proof that every file under `scripts/` parses as Python
   3.9 (`ast.parse(..., feature_version=(3, 9))`) and three proofs, each skipped where no
   Python 3.9 is on the machine (`/usr/bin/python3` is 3.9.6 on this Mac): setup, a test run and
   the status each exit 0 under it in a scratch project.
3. **No background job** (§5 row 3): purlin_output gains a rule, "No Purlin command leaves a
   process of its own running after it exits", with one proof: after setup, a test run with
   `--commit` and the status in a scratch project, no process whose command line names the
   scratch project is left.
4. **Adjust to `scaffold`** (K6): `dev/test_purlin_version.py` near line 224 runs setup with
   `--yes`, which now commits the files setup wrote.
5. **`> Highest-Rule:`** (K4.2) in `specs/instructions/purlin_agent.md`, `purlin_version.md`
   and `purlin_output.md`.

**You produce** for other lanes: nothing another lane consumes.

**You consume**: K3.9 (setup commits with `--yes`).

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
cd /Users/richlabarca/LocalCode/purlin-wt/p4-instructions
.venv/bin/python -m pytest dev/test_purlin_agent.py dev/test_purlin_version.py dev/test_purlin_output.py -q
bash dev/run_tests.sh --fast
```

If `.venv` is missing in the worktree, use
`/Users/richlabarca/LocalCode/purlin/.venv/bin/python`. Do not run the full sweep; integration
runs it once. A failure in a test file you do not own: check the contracts' K6. If K6 predicts
it, leave it; otherwise report the test, its assertion and the value it saw. Never edit that
file.

## Limits

- Commit on `p4/instructions` only, with the prefixes of `references/commit_conventions.md`,
  each message ending with the attribution lines your session gives. Push nothing, tag nothing,
  open no pull request.
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
   remove the clause from the agent definition: its proof fails; (b) add a `match` statement to
   one file under `scripts/`: the Python 3.9 parse proof fails; (c) make the run start
   `sleep 30` and not wait for it: the no-background-process proof fails.

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
