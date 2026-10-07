# Handoff, 2026-10-06: ready for decision 135

Local `main` is green and not pushed. Decisions 100 to 134 are built. Decision 135, testing
prompts and skills, is planned in `dev/plans/ai-proofs-plan.md` and not built. Nothing is
signed or tagged, and the owner has planned no signing. GitHub holds `main` (far behind local)
and the two `qa/` branches.

## Where it stands

| | Result |
|---|---|
| `bash dev/run_tests.sh` | 1375 passed, 0 failed, 10 skipped; 4 suites passed, 0 failed |
| `purlin_run.py --test --all --commit` | 1380 markers tied, 0 not tied; 40 specs, 609 rules, every one passing |
| `python3 dev/windows_run.py` | ends `609 rules. 609 pass their tests.` |
| `sign.py --show` | does not refuse; about 20 seconds |

Formats: spec 24, anchor 12, marker 6, evidence 17, package 17, signature 17. The dashboard's
data is schema 19.

## The audit is held back, on purpose

The status ends `The audit found 81 of 601 rules strong (13%): 81 strong, 8 spot-checked, 488
out of date, 32 not audited.` Out of date is not weak: on 2026-10-06 every rule had been read
and 566 of 569 read `strong`. The changes since then put those results out of date, and 32
rules are new.

The owner chose not to audit again before decision 135, since that round changes the same code:
"we are about to kick off a big piece of work that might invalidate a bunch". The audit of
every spec in the project is the closing step of that round.

How the audit of Purlin itself went, for whoever runs it next:

- It was done in batches of 100 to 200 rules, each batch's findings worked before the next.
- About 1 rule in 5 was weak on a first read. Of 140 planted bugs that got past a test, 136
  were caught once the test held the value its proof names; 4 tests were judged sound and
  settled with `--sound`. No strengthened test failed on the code as it stood.
- The tests that hold pages and printed lines were the weakest: a test that looks for a word
  passes when the sentence says the opposite.
- A rule with a proof tagged for Windows settles only after a Windows run.
- The procedure the lanes followed is the build skill's "Strengthening a weak rule".

## What this round built, since decision 129

- **Decision 130**, after a goal-seek test by real sessions: a plain audit plants a surviving
  bug again first; the first run commits the settings file after a question that says so; the
  last line names the sign-off as optional; the update restores what setup writes on a project
  0.9.5 never set up.
- **Decision 131**: the code says planted bug (`scripts/review/planted_bug.py`, the fields
  `bugs` and `bug_key`, the reply line `no bug:`).
- **Decision 132**, what the audit showed about Purlin: a test whose name begins with
  another's is no longer left out with it; a settle reads the spot tests again and starts the
  slow test of the rule it names; the full run reads an audited anchor again.
- **Decision 133**: the docs are short, about 1,800 lines where they held 3,400. A heading
  states the idea, and each page has a flow diagram with its box names in bold. The audit's
  research is on `docs/audit-research.md`. `docs/regulated.md` is the page for regulated
  work, beside a document control system such as Veeva.
- **Decision 134**: each test's evidence keeps what the test tool reported, and a sign-off
  commits the reports the machine holds beside the package; the package names the co-authors
  git holds on each commit.
- **Every warning has one shape**, in the terminal and on the dashboard:
  `<what it is about>: <kind>. <what is wrong, in few words>. Run <command>.`, as
  `package PROOF-3 (RULE-3): test comment to correct. "sixteen" became "seventeen" after
  dev/test_export.py:336 last changed (82c91f6). Run purlin:build package.` The kinds are one
  list, `KINDS` in `scripts/mcp/purlin/notices.py`; `references/writing_style.md`, "A
  warning's shape", is its home. Three or more of a kind fold into one line, and
  `purlin:status <name>` lists each. A run's result lines take the shape too, under the
  names `Left to do` uses: `rule to fix`, `rule to write a test for`, `evidence missing`.
- **The sign-off's preview** takes about 20 seconds; it took two minutes.
- **The deck** is published at version 139.

## For the owner

1. **Read `docs/regulated.md` first**, then the other pages: every one was rewritten.
2. **A failing rule's line reads `rule to fix`**, where the owner's example read `failing
   test`: the name `Left to do` already had was kept, so one piece of work has one name.
3. **A slow test whose name is the start of another test's name is started on every plain
   run**, with a line saying so, until one is renamed. pytest cannot leave out exactly one.
4. **A test report is kept only on the machine that ran the tests.** The preview here reads
   `Test reports kept with the package: 2 of 3. 1 is not on this machine`: the third is the
   Windows runner's.
5. **Prompts run through the `claude` program in the plan**, as the audit's model does, where
   the option the owner picked said the prompt way needs an API key.
6. **About a dozen kinds of warning can still pass 160 characters** with long names; what
   remains in each is a name, a path or the command.
7. **Not in the one shape**: the audit's findings under a rule, and a refusal that ends a
   command.
8. **Left by earlier rounds, unchanged**: a rule can read `strong` while one of its proofs has
   no caught bug; a session runs the scripts directly where a skill names a command, and
   guesses their options; a session's status tool keeps the code it loaded when it started.

## How to work, as the owner settled it

- **Decisions close before anything launches.** Ask with the question UI, one decision at a
  time, from the root: what the thing is for, in plain words, with everything needed to answer
  inside the question and the recommended option first. Name a thing by what a person sees.
- **The least change.** Before adding a concept, a format or a command, check whether
  something Purlin has already does the job. "dont just bolt this on".
- **Maximum parallelization, cut by ownership of files.** Each lane has its own worktree and
  scratch folder and owns files no other lane writes. What one makes and another uses is
  fixed word for word before they start.
- **No push, no pull request, no tag and no signing by any agent**, but the run branch
  `python3 dev/windows_run.py` pushes and deletes.
- **Acceptance is the full sweep**, `bash dev/run_tests.sh`, plus this repository run through
  its own tool with every marker tied. Never edit a number to make a sweep green.
- **Run with the project's `.venv` first on PATH.** The system `python3` has no pytest.
- **Look at anything visual** with playwright from the `.venv`, at several widths and both
  themes, before saying it is done.
- **A clean release.** Nothing that represents earlier functionality stays.
- **The docs are short**, and the only pictures are simple flow diagrams. Not every decision
  goes in a doc.
- **The deck and the docs are changed when their source is.** Pushing waits for the owner.
- **A sign-off is optional**, and every line that names it says so.
- **A prompt for a new session is pasted into the conversation**, never written as a file.
- **No statement about cost** in anything that ships.
- **Any commit puts the sign-off's refusal back**; `purlin:test --all --commit` clears it by
  carrying the results forward.
