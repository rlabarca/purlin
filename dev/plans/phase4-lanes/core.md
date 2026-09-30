# Lane `core` (phase 4, fan-out 1)

You are lane `core` of phase 4 of Purlin 0.10.0: sanity check 3 applied, with the owner's
answers of decision 98. Purlin is a Claude Code plugin for spec-driven development that uses
itself. This brief is complete in itself; the files below are where its words come from. No
reviewer follows you: you check your own work with the self-check at the end and report.

- Worktree: `/Users/richlabarca/LocalCode/purlin-wt/p4-core`, branch `p4/core`, created from
  `main` after P1 merged:
  `git -C /Users/richlabarca/LocalCode/purlin worktree add /Users/richlabarca/LocalCode/purlin-wt/p4-core -b p4/core main`.
- Scratch folder: `<the scratchpad directory your session gives>/p4-core`.
  Nothing of yours goes anywhere else outside the worktree.

## Read first

1. `CLAUDE.md`, `references/writing_style.md`, `references/spec_quality_guide.md`,
   `references/glossary.md`.
2. `dev/plans/three-levels.md` decisions 94 to 98 (decision 98 holds the answers of sanity check
   3); a later decision amends an earlier one.
3. `dev/plans/phase4-plan.md` sections 1, 4 (your row), 5, 6 and 11, and
   `dev/plans/phase4-contracts.md` whole: every line you print or quote is there, word for word.
4. `sanity-3.md` section 6 items 5, 11, 12, 21, 39; section 7 faults 5, 7 and 18; section 8 item
   10; section 5 row 5 and groups 8, 13, 14 and 15.
5. `references/glossary.md` ("The chain", "waiting") and `references/hard_gates.md`
   ("`Left to do`").

Section references such as "§6 item 5" are to `dev/plans/sanity-3.md`; "A<n>" is the owner's
answer <n> of decision 98; K-numbers are sections of the contracts.

## The files you own

You write these and no other file. Every other file is read-only for you, the frozen helpers
included: `dev/skill_checks.py`, `dev/mcp_project.py`, `dev/sign_project.py`,
`dev/run_project.py`, `dev/reports_project.py`, `dev/conftest.py`, `dev/fake_claude.py`.

- `scripts/mcp/purlin/states.py`
- `scripts/mcp/purlin/payload.py`
- `scripts/mcp/purlin/status.py`
- `scripts/mcp/purlin/summary.py`
- `scripts/mcp/purlin/board.py`
- `scripts/mcp/purlin/gate.py`
- `scripts/mcp/purlin/console.py`
- `specs/mcp/states.md`
- `specs/mcp/summary.md`
- `dev/test_states.py`
- `dev/test_summary.py`
- `dev/test_backing_tests.py`
- `dev/test_failing.py`
- `skills/status/SKILL.md`
- `specs/skills/skill_status.md`
- `dev/test_skill_status.py`

## The work

Build every item. Each names its source and the change; where it names a contract, the contract
is the words.

1. **Fault 5, one untested proof among tested ones** (§7 fault 5; decision 97; call 13). In
   `states._untested`, a proof counts as listed in a section only where the section names a test
   for it (`evidence.proof_tests` already skips an entry whose `test` is empty). states RULE-8
   says "a proof that no marker ties to a test and no current section lists with a test has no
   test". New proof: PROOF-1 passed and the evidence lists PROOF-2 with `"result": "missing"`
   and an empty test; the passed cell reads `no test` with the reason
   `no test for PROOF-2`. New summary proof: that project ends
   `  1 rule to write a test for: purlin:build`.
2. **Fault 18, no files and `waiting`** (§7 fault 18; glossary "waiting"; call 11). The signed
   cell's override for a spec that names no files (near `states.py` 202-210) applies only once
   the strong cell is met; before that the signed cell reads `waiting` with
   `waiting for the audit`. states RULE-63 says so. New proof: at `signed`, a rule of a
   spec with no `> Scope:` whose test passed and that no audit has read has its strong cell
   `not audited` and its signed cell `waiting`. PROOF-75 and PROOF-137 hold.
3. **Fault 7, system words in the reasons** (§6 item 5; K2.1 core-1 to core-4; K3.8). Every
   system word in a cell reason goes through `evidence.os_word`; `passed on` joins with the
   `<Systems>` join (`, ` and a last ` and `). states RULE-6 reads
   `<System>: no run yet`; PROOF-8, 204, 155, 53 and 154, 156 and their tests
   (`dev/test_states.py`, `dev/test_failing.py`) quote the new words. The payload's
   `missing_env` keeps the stored words.
4. **The settings lines** (§6 items 11 and 39; K2.1 core-5, core-6; K3.4). `gate.py` builds
   core-5 and core-6, `<value>` as JSON writes it. Their rules are item 9's.
5. **A spec that names no files** (§6 item 21; K2.1 core-7, core-8; K3.6).
   `status.incomplete_line(names)` returns core-7 or core-8; states PROOF-76, 198, 199, 109,
   200, 201 and their tests quote them. Lane `update` prints it (K6).
6. **The source that could not be read** (§6 item 12; K2.1 core-9; K3.5). The status's anchor
   line gains the step. The lines for a pin behind its source and for a source with no pin do
   not change.
7. **`sync_status` and the project root** (§8 item 10; K3.12). `skills/status/SKILL.md`'s first
   call of `sync_status` gains K3.12's clause, cutting a line elsewhere (100 of 100 lines).
   skill_status gains a proof reading the clause.
8. **The page reads a run at once** (§5 row 5). New states rule: after a test run the data file
   the dashboard reads, `.purlin/report-data.js`, holds that run's results with no other
   command; one proof (a run that passes a rule; the data file then reads that rule `passed`).
9. **The settings warnings** (§5 group 8; call 15). `specs/mcp/states.md`'s `> Scope:` gains
   `scripts/mcp/purlin/gate.py`. One rule on the warnings resolving the settings prints beside
   the table, with one proof per line: core-5, core-6,
   `"min_strength" is not a number; no minimum applies`,
   `"min_strength" is not a number; using <n>` and
   `.purlin/config.json still carries <keys>, which this release does not read. Run purlin:init --update.`,
   each quoted as the code prints it.
10. **The uncommitted-specs block** (§5 group 13). One rule and one proof: with a spec changed
    and not committed, the status carries `Uncommitted spec changes:` and under it the
    spec's `git status` line indented two spaces.
11. **The status's anchor lines** (§5 group 14). One rule on the `Anchors:` block, with one
    proof per line: `Anchors:`, the pin behind its source, the source with no pin, the source
    that could not be read (core-9) and `<name>: (source rejected: <reason>)`.
12. **The plural test-comments line** (§5 group 15; decision 97). summary gains the proof: three
    comments naming nothing end the status on
    `  3 test comments to correct: purlin:build`.
13. **`> Highest-Rule:`** (K4.2) in `specs/mcp/states.md`, `specs/mcp/summary.md` and
    `specs/skills/skill_status.md`.

**You produce** for other lanes: core-1 to core-9 (K2.1), `status.incomplete_line` (K3.6), the
cell reasons of K3.8.

**You consume**: P1's `status.no_spec_lines` and the warning line (K1); `evidence.os_word`.

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
cd /Users/richlabarca/LocalCode/purlin-wt/p4-core
.venv/bin/python -m pytest dev/test_states.py dev/test_summary.py dev/test_backing_tests.py dev/test_failing.py dev/test_skill_status.py -q
bash dev/run_tests.sh --fast
```

If `.venv` is missing in the worktree, use
`/Users/richlabarca/LocalCode/purlin/.venv/bin/python`. Do not run the full sweep; integration
runs it once. A failure in a test file you do not own: check the contracts' K6. If K6 predicts
it, leave it; otherwise report the test, its assertion and the value it saw. Never edit that
file.

## Limits

- Commit on `p4/core` only, with the prefixes of `references/commit_conventions.md`, each
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
   give `_untested` back its old test of a listed proof: item 1's proof fails; (b) drop the
   `strong met` condition from item 2's override: its proof fails; (c) print the stored word
   in `<System>: no run yet`: states PROOF-8 fails.

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
