# Handoff, 2026-10-02: decisions 122 and 123 are built

Local `main` is green and not pushed: 39 specs, 465 rules, 1004 proofs, every rule passing on
committed evidence, the Windows rules included. Nothing is signed or tagged. GitHub holds `main`
(far behind local) and the two `qa/` branches; the Windows runs' branches were deleted when
they finished.

## What was built

- **Decision 123, how the audit plants a bug.** One bug per proof, aimed past that proof's
  test. The model names the case its bug breaks, and a surviving bug shows that line under its
  finding on every surface: `PROOF-2: the AI says this breaks: <case>`. A part that names no
  case, or a change that touches only a comment, is not planted.
- **Decision 122, the real-skills check's findings 1 to 13 and 17**, as `d122-plan.md` planned
  them, and no cost or count of model calls in anything that ships.
- **The audit page**, `docs/audit.md`: simple at the top; below it the reasoning, with quotes,
  sources and the trial on the sample lab project. `dev/plans/audit-research.md` is its source:
  23 papers, each read in full.
- **A review of the audit's code after it was built**, by a reader that had not written it
  (`d122-reports/review-audit.md`): 11 faults, 8 fixed with a rule and a proof each (`planted_bug` RULE-19 to 25, `ai_audit`
  RULE-51 and the reworded RULE-35).
- **A reading of every page against the code** (`d122-reports/review-pages.md`): 9 certain
  disagreements, fixed.
- **A speed fault found by auditing Purlin itself.** For each planted bug the audit ran the
  proof's whole test file twice. On this repository that was about 100 seconds a proof; one
  spec took 74 minutes. It now leaves the file's other marked tests out where the test tool
  can (`planted_bug` RULE-26). The same spec then took 5 minutes.

## The numbers

| | Result |
|---|---|
| `bash dev/run_tests.sh` | 1002 passed, 0 failed, 9 skipped; 4 suites passed, 0 failed |
| `purlin_run.py --test --all --commit` | 1004 markers tied, 0 not tied; 39 specs, 465 rules, 1004 proofs |
| `python3 dev/windows_run.py`, run 3 times | the last ends `465 rules. 465 pass their tests.` |
| The plan's greps | each empty, but the proof that names `"sign": true` as the case that signs nothing |
| The deck's two checks | every slide ends at 920 of 920, no overlap |

Formats: spec 24, anchor 12, marker 5, evidence 13, package 13, signature 16. The dashboard's
data is schema 16. The drift criteria are version 14.

## The audit of Purlin itself

Ten specs, each with its own `--feature`, the real model, the results committed. It was run
twice, with the weak tests strengthened between.

| Spec | First audit | After the tests were strengthened |
|---|---|---|
| `plain_checks` | 9 of 9 strong | not read again |
| `reports` | 22 of 22 | not read again |
| `planted_bug` | 21 of 23, 1 weak, 1 spot-checked | the same |
| `ai_audit` | 17 of 24, 7 weak | 20 of 23, 3 weak |
| `specs` | 5 of 6, 1 weak | 5 of 6, 1 weak |
| `package` | 21 of 23, 2 weak | 22 of 22 |
| `evidence` | 16 of 19, 2 weak, 1 spot-checked | 15 of 16, 1 weak |
| `evidence_writer` | 21 of 22, 1 weak | 21 of 22, 1 weak |
| `run_script` | 26 of 35, 9 weak | 31 of 34, 3 weak |
| `signatures` | 26 of 31, 5 weak | 27 of 31, 4 weak |

The status now ends `The audit found 197 of 465 rules strong (42%): 197 strong, 14 weak,
2 spot-checked, 1 out of date, 251 not audited.` and `14 rules to strengthen: purlin:build`.

What the two rounds showed:

- **The first audit found 28 weak rules, 35 surviving bugs.** A person's part was done by two
  agents that read each proof, its test and the bug: 33 findings held, and each test now fails
  with its bug in place. 2 did not hold. `planted_bug` PROOF-12: the model's claim about the
  result was wrong. `evidence_writer` PROOF-41: the bug sat on a path no run reaches.
- **The second audit aimed new bugs past the stronger tests** and found 14 rules weak. That is
  the loop the audit page describes; it does not end at zero in one pass.
- **Every finding carries the model's case line**, and the two false ones were plain from it.
- **A rule kept `weak` on a false finding stays `weak`** until its test or code changes.
  Nothing lets a person mark a finding as not holding.
- The 14 are listed by `purlin:status` and shown on the dashboard, each with its bug.

The agents that strengthened the tests proposed sharper wording for 12 proofs, since the
proof named too little for a test to be held to it: `run_script` PROOF-88, 91, 93, 117, 271,
288, 289; `signatures` PROOF-228, 238; `ai_audit` PROOF-122; `package` PROOF-52; `evidence`
PROOF-88. No proof was changed. Their sentences are in `dev/plans/d122-reports/strengthen.md`, and the
tests already check the sharper reading.

## The dashboard, looked at

This repository's own data after the audit, dark and light, 1500 and 390 pixels, the board and
`ai_audit RULE-4`: no sideways scroll. The top bar's `Audit` box reads `197 of 465 strong`, the
`Strong` column reads `20 of 24` for `ai_audit`, and the rule's `Audit` panel shows the spot
test's finding, the missed bug, `PROOF-55: the AI says this breaks: ...`, and the lines before
and after. The `surfaces` lane looked at the regulated sample at five widths in both themes.

## Lines a person reads

Each lane's report holds every line it chose, word for word: `dev/plans/d122-reports/`
(`setup`, `run`, `collision`, `signoff`, `surfaces`, `words`, `audit`). Chosen at integration:

| Line | Where |
|---|---|
| `PROOF-2: the AI says this breaks: <case>` | the audit, the dashboard, the sign-off's findings. It is not indented under the finding and does not open `The AI says`, as the preview the owner chose showed it: every surface prints a rule's findings as one list of whole sentences |
| `aim` (`past the test` or `plain`) and `case` in a planted bug's entry | `evidence_format.md` and `package_format.md`, version 13 |
| `the change touches only a comment` now also covers a comment at the end of a code line | the audit, under a rule |
| `--yes answers yes to each migration.` | `RELEASE_NOTES.md` |
| `19 rules on Linux/Unix: 18 pass their tests, 1 has a hand check.` and `The audit: 17 strong, 1 weak.` | the example in `docs/sign-off.md` and the sign skill |

## For the owner

1. **Read `docs/audit.md`**, the top and the reasoning. It quotes its papers word for word.
2. **The deck.** The `audit` slide is published (version 131). The source also changes two
   other slides, not published: the `together` slide's fourth row and the `manual` slide's
   notes.
3. **The proofs to sharpen**, above: 12 sentences proposed, none applied.
4. **A finding a person judges false has nowhere to be recorded.** It keeps its rule `weak`.
5. **The comment check is narrow on purpose.** It refuses a `#` or `//` comment line and a
   comment at a line's end. It plants a change to a `/* */` comment, a docstring or a `--`
   comment, and it refuses a shebang line and a `//go:build` line, which are real changes.
6. **Left from the code review**, not fixed: a `no break` reason whose words match one of the
   audit's own sentences is classed as an unusable answer; a `case:` line wrapped over two
   lines or written after `file:` is not read.
7. **`evidence_writer` RULE-16**: `local_machine()` repeats `machine_name()` on a path no run
   reaches, and the rule's "or `unknown`" has no proof.
8. **The docs example clones Purlin at the tag `v0.10.0`**, and the release steps write only
   `signed/<version>`.
9. **The page review's likely findings and judgment calls** that were not changed: the release
   notes' "Three questions" beside the command reference's "Four"; the `remote` slide's
   `purlin:test` for a run that is `purlin_run.py --ci --commit`; `skills/sign/SKILL.md`'s
   "on their yes".
10. **Each lane's calls**, in its report, under "Calls the plan did not make".
11. **One thing outside the repository**: a reading agent passed the owner's email address to
    the Unpaywall API once, as its contact parameter, while looking for a paper.
12. **The installed plugin copy is an earlier build**: a session still lists the old skill
    descriptions until the plugin is installed again from this checkout.

## What is left

1. The owner's review: the release notes, the README, the docs, the deck.
2. `purlin:build` and `purlin:audit` on the 14 weak rules, if a higher share is wanted, and an
   audit of the 29 specs never read.
3. `purlin:sign` on Purlin, the tag pushed, `main` pushed.
4. `dev/plans/d122-plan.md`, `d123-plan.md` and `d122-reports/` go once the owner has read
   them. The plan files of every earlier round are removed. `dev/plans/diagrams/` and
   `drafts/` are not tracked by git and were left on disk.

## How to work, as the owner settled it

- **Decisions close before anything launches.** Ask with the question UI, one decision at a
  time, from the root: what the thing is for, in plain words, with everything needed to answer
  inside the question and the recommended option first.
- **Maximum parallelization, cut by ownership of files.** Each agent has its own worktree and
  scratch folder and owns files no other agent writes. What one produces and another consumes
  is fixed word for word before they start.
- **No push, no pull request, no tag and no signing by any agent**, but the run branch
  `python3 dev/windows_run.py` pushes and deletes.
- **Acceptance is the full sweep**, `bash dev/run_tests.sh`, plus this repository run through
  its own tool with every marker tied. Never edit a number to make a sweep green.
- **Look at anything visual** with playwright from the `.venv`, at 1500, 1280, 1024, 768 and
  390 pixels, both themes, before saying it is done.
- **A clean release.** Nothing that represents earlier functionality stays. `RELEASE_NOTES.md`
  is the one place history is kept.
- **No statement about cost** in anything that ships.
- **A page says what is**, checked against the code, in the words of
  `references/writing_style.md`.
