# Handoff, 2026-10-02: decisions 124 to 128 are built

Local `main` is green and not pushed: 39 specs, 556 rules, 1243 proofs, every rule passing on
committed evidence, the Windows rules included. Nothing is signed or tagged. GitHub holds `main`
(far behind local) and the two `qa/` branches; the Windows runs' branches were deleted when
they finished.

## What was built

- **Decision 124, a test run settles a finding.** `purlin:audit <feature> RULE-N --settle`
  plants each recorded bug that survived again and runs its proof's test. The test fails: the
  bug reads `caught`. The test still passes: the bug is dropped and one new bug is planted; a
  second survivor leaves the proof with no bug and the reason `two planted bugs left the
  proof's check passing`. `purlin:build` runs it as the last step on a weak rule. The one home
  is `references/review_criteria.md`, "Settling a finding".
- **Decision 125, the owner's calls during the build** (`three-levels.md`):
  - The theme button is always at the top right; the top bar's boxes move together to the line
    below the logo where they do not fit.
  - The top bar holds `Tests` and `Sign-off` alone. The `Strong` count box's hover carries the
    audit's counts and `Last audit: <date>`.
  - `not signed` is drawn plain, in the secondary text colour; signed is green; signed with
    commits since is orange.
  - An anchor's `Strong` cell reads one word, `weak`, `out of date` or `spot-checked`, or
    nothing, in the terminal and on the dashboard.
  - The share of strong rules counts no rule of an anchor. Where no rule that could be strong
    passes, the sentence lists what was found: `The audit found 8 spot-checked.`
- **The 12 loose proofs are sharpened** (`d124-reports/proofs.md`, each before and after), and
  three more the strengthening found: `signatures` PROOF-258, `ai_audit` PROOF-34, and
  `run_script` PROOF-93 split in two (`d124-reports/fixes.md`).
- **Three faults left from the last code review** are fixed (`d124-reports/audit.md`), and a
  timeout of the model has a proof (`ai_audit` PROOF-160).
- **A dead end is closed.** A run with no test tool recorded results as `missing`; a plain
  `purlin:test` then said `Nothing to run` while the status said `rules to test: purlin:test`.
  A plain run now also selects a feature the status counts under `rules to test`, printing
  `Selected 1 of 2 features: login (1 rule to test).` It builds the status to decide, about 6
  seconds on this repository; the owner accepted that.
- **The docs example clones Purlin at `signed/0.10.0`**, and `dev/bump_version.sh` carries that
  tag as a derived location.
- **A slow proof may be an acceptance test**: the specs page, the glossary, the quality guide,
  the spec skill and the deck say so.
- **An outside review of the settle code and the pages** (`d124-reports/review.md`): 7 certain
  faults, all fixed with a test seen failing first (`d124-reports/review-fixes.md`); 3 likely
  and 8 judgment calls left, listed below.

- **Decision 126, the upgrade from 0.9.5 survives a real project** (`d126-plan.md`). A fresh
  agent upgraded a copy of a real 0.9.5 project from the pages alone, three times, with the
  fixes built between (`d126-reports/upgrade-tests.md`). The first full test run after the
  upgrade went from 57 of 476 rules to 475, the miss being the project's own unstable test,
  with no hand repair, and the output alone leads to `Tests: met`. What changed:
  - The upgrade renumbers a lettered proof (`PROOF-3b`), rewrites a marker to one plain test
    title and checks each with the run's own reader, cleans every file that loaded the old
    pytest plugin, drops every kind-of-test tag, looks at how the project runs its tests and
    asks, keeps its backups in `.purlin/runtime/update-backup/`, and ends on the next step:
    `→ Run: purlin:init --update` where nothing was applied, `→ Run: purlin:test --all --commit`
    where everything was.
  - The status of a 0.9.5 project is three lines. The status and every run name the tests that
    still carry a 0.9.5 marker.
  - A run reads a test title with an escaped quote or joined from pieces, says so where a
    test ran under another name, prints a line as each suite starts, says when the tests
    setting changed, names what `--commit` left uncommitted, and keeps its commit's subject
    short.
  - **`purlin:test --all` hands each tool the files that carry a marker.** It used to start
    the tool with no file list. A test file with no marker no longer runs under `--all`.
    Over 30,000 characters the list is left out, and the run says so.
  - The dashboard draws three or more warnings of one kind as one notice with a count.

- **Decision 127, the open items after the third upgrade test** (`d127-plan.md`,
  `d127-reports/`):
  - `purlin:test --all` prints `<n> test files carry no marker and were not run.` On this
    repository that is 3, Purlin's own end-to-end shell suites among them; the sweep still
    runs them.
  - The dashboard shows a red `Failing` box where a rule fails, specs with a failing rule
    first, and every line the terminal prints between the table and the sentence.
  - The warning for tests that still carry a 0.9.5 marker lists each, `<file>:<line>
    <feature> <rule>`, up to 20; the upgrade names the same line after its rewrite.
  - `purlin:sign` refuses while such a test remains. The status's last line names that
    rewrite, and names `purlin:test --all --commit` where a sign-off would refuse results
    taken on another version or with files uncommitted, so the last line never sends a
    person to a sign-off that refuses.
  - A settle is refused for a proof whose test is as it was when the bug got past it;
    `--settle --sound PROOF-N` records that the test was judged sound and left as it was.
    The evidence and package formats are at version 14.
  - The upgrade's polish: `CLAUDE.md` first among its leftovers, docstring tags removed, the
    proposed command citing the script it matches, the backups sentence, no repeated list.
  - A fourth upgrade test on a fresh copy, at the end, reached a state `purlin:sign --show`
    accepts, by the output alone; the one fault it found (the last line above) is fixed.

- **Decision 128, the answers after the fourth upgrade test** (`d128-plan.md`,
  `d128-reports/`):
  - The sign-off's list of findings names each proof settled with its test unchanged, and
    the question before it counts them, so a finding cleared by judgment is seen.
  - The upgrade removes the 0.9.5 instructions from the project's `CLAUDE.md`, `AGENTS.md`
    and `.claude/` Markdown and JSON files inside the `markers` step, with a backup and no
    question of its own. On RLabGenMusic it removed 14 lines: two bullets, a two-line
    paragraph and one sentence.
  - `purlin:status <name>` prints one spec's rules with their two cells, the reasons of a cell
    that names work, and the proof lines.
  - An anchor out of date reads `0 of 11 · 11 out of date`, in the terminal and on the
    dashboard.
  - The dashboard's count boxes stand above its notices at every width.

## The numbers

| | Result |
|---|---|
| `bash dev/run_tests.sh` | 1240 passed, 0 failed, 9 skipped; 4 suites passed, 0 failed |
| `purlin_run.py --test --all --commit` | 1243 markers tied, 0 not tied; 39 specs, 556 rules, 1243 proofs |
| `python3 dev/windows_run.py`, run seven times | the last ends `556 rules. 556 pass their tests.` |
| `purlin:init --update` on this repository | `Nothing is pending: this project is at 0.10.0.` |
| The plan's grep for cost and counts of model calls | empty |
| The deck's two checks | every slide ends at 920 of 920, no overlap |

Formats: spec 24, anchor 12, marker 5, evidence 14, package 14, signature 16.
The dashboard's data is schema 16. The drift criteria are version 14.

## The loop on Purlin's own weak rules

The tests behind the 15 weak rules were read by the build skill's steps: 11 got the assertion
their proof names, each seen failing with its recorded bug in place; 4 already asserted it and
were left alone (`d124-reports/strengthen-a.md`, `strengthen-b.md`). No proof stopped the build
as too loose. Then each rule was settled with the real model.

| Ended | Rules |
|---|---|
| The test now catches the bug it missed (12) | `specs` RULE-17; `evidence` RULE-7; `ai_audit` RULE-3, RULE-4, RULE-40; `run_script` RULE-63, RULE-102, RULE-103; `signatures` RULE-106, RULE-110, RULE-115, RULE-132 |
| The finding was wrong, and a new bug was caught (2) | `planted_bug` RULE-10; `ai_audit` RULE-1 |
| Two bugs left one proof's check passing (1) | `evidence_writer` RULE-16, PROOF-41; the rule read `strong` through its other proof |

The status lists no rule to strengthen. After decision 124 it ended `The audit found 93 of 485
rules strong (19%)`; after decisions 126 and 127, which changed more of the audited code, it ends
`The audit found 37 of 548 rules strong (6%): 37 strong, 177 out of date, 342 not audited.`

**Why 37 and not 197.** This round changed the audit's own code and criteria, so results taken
before it read `out of date`, each still showing what the last audit found and when. After the
settle runs 99 rules read `strong`; the review's fixes then changed the audit's code again, and
the six settled rules of `ai_audit`, `planted_bug` and `evidence_writer` went out of date with
it. Where each spec stands: `plain_checks` 9 strong, `reports` 22, `specs` 6, `package` 22 and 1
out of date, `signatures` 30 and 1, `run_script` 3 and 32, `evidence` 1 and 18; `ai_audit` 24,
`planted_bug` 23 and `evidence_writer` 22 out of date. Decision 126 then put `run_script`'s and `evidence`'s settled rules out of date too.
A plain audit of those specs brings them current, and plants new bugs as it does.

## The dashboard, looked at

This repository's own data, dark and light, 1500 and 390 pixels, the board, `signatures`
RULE-106 (settled `strong`) and `evidence_writer` RULE-16 (the two-bugs sentence in its `Audit`
panel): no sideways scroll, no value on two lines. The top bar was looked at at 1500, 1280,
1120, 1024, 768 and 390. The docs' two screenshots were retaken.

## The deck

Published at version 133: `example` (it names no requirement number), `together`, `manual` and
`audit`. The live `slow` slide was edited on the web to the same words as the source and was
left as it is; that edit set its four code words in Arial.

## Lines a person reads

Each lane's report holds every line it chose, word for word, under `dev/plans/d124-reports/`.
Chosen at integration:

| Line | Where |
|---|---|
| `The audit found 8 spot-checked.` | the closing sentence where no rule that could be strong passes |
| `weak`, `out of date`, `spot-checked` or nothing | an anchor's `Strong` cell |
| `No bug is planted for an anchor's rule.` | the first line of that cell's hover |
| `Selected 1 of 2 features: login (1 rule to test).` | a plain test run |
| `purlin: --settle goes with --audit.`, `purlin: --settle needs exactly one --feature.`, `purlin: --settle needs a rule, as RULE-N.` | the three refusals |

## For the owner

1. **Read `docs/audit.md`**: "What to do with a finding", the two sentences under its six
   bullets, and the new part `On Purlin's own tests`.
2. **Read the reworded proofs**: `d124-reports/proofs.md` and `fixes.md`.
3. **A settle with nothing changed clears a weak rule.** A person who runs `--settle` over an
   untouched weak test gets the bug dropped and the rule `spot-checked`, or `strong` where
   another proof has a caught bug. The plan chose this; the audit cannot tell a sound test
   from an untouched one.
4. **A rule can read `strong` while one of its proofs has no caught bug**, as `evidence_writer`
   RULE-16 did. The rule's `Audit` panel shows the sentence; the board does not.
5. **Whether an AI working toward a goal takes the build path unprompted is not proven.** The
   output and the skills send a weak rule to `purlin:build`; no real session has been watched
   doing it.
6. **The four rules on how `--settle` is typed** sit in `ai_audit`, whose scope leaves out the
   file that holds them, so an audit reads them `spot-checked`.
7. **A plain `purlin:test` reruns, every time, a feature whose rule stays `not run`**, such as
   one whose result must come from Windows. `evidence` was selected this way on this Mac until
   the Windows run came back.
8. **Left by the review**: a capitalised `No break:` is not read; `The audit found 2 out of
   date.` reads awkwardly; `ai_audit` RULE-56's "until its test or code changes" has no proof;
   the other judgment calls are in `d124-reports/review.md`.
9. **Left from earlier rounds**: `evidence_writer` RULE-16's "or `unknown`" has no proof and
   `local_machine()` repeats `machine_name()`; the release notes' "Three questions" beside the
   command reference's "Four"; the `remote` slide's `purlin:test`; `skills/sign/SKILL.md`'s "on
   their yes"; `docs/sign-off.md` and the package format use `(URS-042)` as their example.
10. **A session's status tool keeps the code it loaded when the session started.** The owner
    starts Claude with `--plugin-dir` at this checkout, so the skills are current; the status
    tool's process is not until a new session. Run `scripts/run/purlin_status.py` meanwhile.
11. **Kept as they are, by the owner's answers to decision 128:** a test with a 0.9.5 marker is
    a warning and a closing line, not a `Left to do` line, and the tests stay `met`; `Left to
    do` shows the next step; an unstable test gets one sentence on the upgrade page, no retry.
12. **The upgrade's `CLAUDE.md` cleanup removes a whole bullet** where one of its lines names
    0.9.5, so a useful sentence in the same bullet can go with it; a removed line is in
    `update.log` and the file's backup. Hook scripts under `.claude/` are listed, not edited.
13. **The backup folder `.purlin/runtime/update-backup/` stays until a person deletes it**;
    the update's ending says when.

## What is left

1. The owner's review: the release notes, the README, the docs, the deck.
2. An audit of the specs whose results are out of date, and of the 29 never read, if a higher
   share is wanted.
3. `purlin:sign` on Purlin, the tag pushed, `main` pushed.
4. `dev/plans/d124-plan.md`, `d124-reports/`, `d126-plan.md`, `d126-reports/`, `d127-plan.md`,
   `d127-reports/`, `d128-plan.md` and `d128-reports/` go once the owner has read them. The four upgraded copies under
   `../purlin-wt/` can be deleted.
5. Before signing, by the owner's answers: the audit of the out-of-date specs, settled, and a
   real AI session given a goal on a sample project with weak rules.
   `dev/plans/diagrams/` and `drafts/` are not tracked by git and were left on disk.

## How to work, as the owner settled it

- **Decisions close before anything launches.** Ask with the question UI, one decision at a
  time, from the root: what the thing is for, in plain words, with everything needed to answer
  inside the question and the recommended option first. Name a thing by what a person sees,
  never by the code's word for it.
- **Maximum parallelization, cut by ownership of files.** Each agent has its own worktree and
  scratch folder and owns files no other agent writes. What one produces and another consumes
  is fixed word for word before they start.
- **No push, no pull request, no tag and no signing by any agent**, but the run branch
  `python3 dev/windows_run.py` pushes and deletes.
- **Acceptance is the full sweep**, `bash dev/run_tests.sh`, plus this repository run through
  its own tool with every marker tied. Never edit a number to make a sweep green.
- **Run with the project's `.venv` first on PATH.** The system `python3` has no pytest.
- **Look at anything visual** with playwright from the `.venv`, at 1500, 1280, 1024, 768 and
  390 pixels, both themes, before saying it is done. On the dashboard a cell is one word where
  it can be.
- **A clean release.** Nothing that represents earlier functionality stays. `RELEASE_NOTES.md`
  is the one place history is kept.
- **No statement about cost** in anything that ships.
- **A page says what is**, checked against the code, in the words of
  `references/writing_style.md`.
