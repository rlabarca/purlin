# Lane `dashboard` (phase 4, fan-out 1)

You are lane `dashboard` of phase 4 of Purlin 0.10.0: sanity check 3 applied, with the owner's
answers of decision 98. Purlin is a Claude Code plugin for spec-driven development that uses
itself. This brief is complete in itself; the files below are where its words come from. No
reviewer follows you: you check your own work with the self-check at the end and report.

- Worktree: `/Users/richlabarca/LocalCode/purlin-wt/p4-dashboard`, branch `p4/dashboard`,
  created from `main` after P1 merged:
  `git -C /Users/richlabarca/LocalCode/purlin worktree add /Users/richlabarca/LocalCode/purlin-wt/p4-dashboard -b p4/dashboard main`.
- Scratch folder: `<the scratchpad directory your session gives>/p4-dashboard`.
  Nothing of yours goes anywhere else outside the worktree.

## Read first

1. `CLAUDE.md`, `references/writing_style.md`, `references/spec_quality_guide.md`,
   `references/glossary.md`.
2. `dev/plans/three-levels.md` decisions 94 to 98 (decision 98 holds the answers of sanity check
   3); a later decision amends an earlier one.
3. `dev/plans/phase4-plan.md` sections 1, 4 (your row), 5, 6 and 11, and
   `dev/plans/phase4-contracts.md` whole: every line you print or quote is there, word for word.
4. `sanity-3.md` section 6 items 9, 10, 24, 25, 26, 27 and 43; section 11 question 13; section 5
   rows 9, 10 and 11 and groups 27 and 28.
5. `design/readme.md`; `CLAUDE.md` "Design and copy".

Section references such as "§6 item 5" are to `dev/plans/sanity-3.md`; "A<n>" is the owner's
answer <n> of decision 98; K-numbers are sections of the contracts.

## The files you own

You write these and no other file. Every other file is read-only for you, the frozen helpers
included: `dev/skill_checks.py`, `dev/mcp_project.py`, `dev/sign_project.py`,
`dev/run_project.py`, `dev/reports_project.py`, `dev/conftest.py`, `dev/fake_claude.py`.

- `scripts/report/src/**`
- `scripts/mcp/purlin/report_data.py`
- `dev/build_report.py`
- `dev/capture_doc_screenshots.py`
- `specs/dashboard/purlin_report.md`
- `dev/test_purlin_report.py`
- `dev/test_purlin_report_board_layout.py`
- `dev/test_report_refresh.py`
- `dev/fixtures/report/*.json`

## The work

Build every item. Each names its source and the change; where it names a contract, the contract
is the words.

1. **The Audit panel** (§6 item 24; K3.1; dashboard-1): purlin_report RULE-39 and PROOF-54, 144,
   145, 146, 147, 39 and their tests follow.
2. **Test strength** (§6 items 9, 25; K3.3; dashboard-2): floor on the rule page; one proof with
   a share of 85.7 reading `85%` on both the board and the rule page.
3. **The sign command** (§6 item 26; dashboard-3): PROOF-26 and its test quote the line whole.
4. **No test yet** (§6 item 27; K3.2; dashboard-4): PROOF-69 and its test.
5. **Glyphs** (§6 item 10; dashboard-5, dashboard-6): RULE-25, PROOF-25, 138 and PROOF-6 (the
   page holds `▶` and `▼`, and no glyph outside `▶ ▼ ▲ →`) follow; the theme button
   reads its label.
6. **Capitals** (A13): nothing on the page changes; RULE-8 holds.
7. **The data file's messages** (§5 rows 9, 10, 11): proofs quoting
   `No board data yet. Run purlin:status to write .purlin/report-data.js, then reload this page.`
   and the uncommitted-tree notice whole, and one that a theme chosen with the toggle is the
   theme the page opens in after a reload.
8. **Hovers and empty states** (§5 groups 27, 28): one proof per line of group 27's uncovered
   list in the research (`app.js` 496-497, 519-521, 526-528, 271, 297, 318, 460-462, 464;
   `board.js` 350; `rule.js` 73-74, 133-135, 186, 220-221) and the theme label, each quoted as
   the page shows it.
9. **Comments** (A8): `board.js` and `app.js` comments that say a spec proves rules from "an
   anchor it requires" stay; any that say a spec requires another feature's spec say anchor.
   Adjust to `core` (K6): PROOF-17, 100, 101 and the fixtures under `dev/fixtures/report/` read
   `<System>` words where the product now writes them.
10. **`> Highest-Rule:`** (K4.2) in `specs/dashboard/purlin_report.md`.

**You produce** for other lanes: dashboard-1 to dashboard-6 (K2.15).

**You consume**: K3.1, K3.2, K3.3; the reasons of K3.8.

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
cd /Users/richlabarca/LocalCode/purlin-wt/p4-dashboard
.venv/bin/python -m pytest dev/test_purlin_report.py dev/test_purlin_report_board_layout.py dev/test_report_refresh.py -q
bash dev/run_tests.sh --fast
```

If `.venv` is missing in the worktree, use
`/Users/richlabarca/LocalCode/purlin/.venv/bin/python`. Do not run the full sweep; integration
runs it once. A failure in a test file you do not own: check the contracts' K6. If K6 predicts
it, leave it; otherwise report the test, its assertion and the value it saw. Never edit that
file.

## Limits

- Commit on `p4/dashboard` only, with the prefixes of `references/commit_conventions.md`, each
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
   round the rule page's strength again: the 85.7 proof fails; (b) put `←` back on the back
   button: PROOF-6 fails; (c) show the old undecided or no-audit words: PROOF-147 fails.

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
