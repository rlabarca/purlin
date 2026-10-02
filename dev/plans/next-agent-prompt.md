# Prompt for the next session: build decision 124

Paste everything below the line into a new session opened in `/Users/richlabarca/LocalCode/purlin`.

---

You are continuing Purlin 0.10.0, a Claude Code plugin for spec-driven development that uses
itself. Local `main` is green and not pushed: 39 specs, 465 rules, every one passing on
committed evidence, the Windows rules included. Decisions 100 to 123 are built. Nothing is
signed or tagged. Your job is decision 124, which is decided and planned and not started: a
test run settles every finding of the audit.

## Read first, in this order

1. `dev/plans/handoff.md`, in full.
2. `dev/plans/three-levels.md`: decisions 100 to 124 (search `100. **`); later wins. Decision 44
   is the clean release.
3. `dev/plans/d124-plan.md`, in full: it is the plan you build. Then section 4 of
   `dev/plans/d123-plan.md`, the lane brief it reuses.
4. `CLAUDE.md`, `references/writing_style.md` (its section "Short and plain"),
   `references/spec_quality_guide.md`, `references/review_criteria.md`.
5. `docs/audit.md`, `skills/audit/SKILL.md`, `skills/build/SKILL.md`,
   `scripts/review/audit_run.py`, `scripts/review/targeted_break.py`,
   `scripts/review/ai_audit.py`.
6. `dev/plans/d122-reports/strengthen.md` (the 12 proof sentences and the two wrong findings)
   and `dev/plans/d122-reports/review-audit.md` (the three faults left).

## What was decided, so you do not ask again

The owner's words: "I want the audit to be informative and guide the user to the next step...
I dont want users to bang their heads on an impossible task to get the proof strong when it's
not useful", and "i dont want the human to be the judge".

- `purlin:build` writes the assertion the proof names; the recorded bug is planted again and
  that test runs. Fails: the finding was right, and the rule reads `strong`. Passes: the
  finding was wrong.
- A caught replay makes the rule `strong`. No fresh bug is planted after it.
- A wrong finding is replaced once. Wrong again: the rule reads `spot-checked`, with the
  reason, and nothing more is asked.
- A dropped bug leaves no trace in the evidence.
- A proof too loose to write the assertion from stops the build, which proposes a sharper one.
- The 12 loose proofs are sharpened with the sentences already written. The owner reads them
  after; do not ask about each.

## How the owner works

- Decisions close before anything launches. If a call comes up that the plan does not make and
  that changes what a person reads or does, ask with the question UI, one decision at a time,
  from the root: what the thing is for, in plain words, no file or function name, the
  recommended option first, and everything needed to answer inside the question. A technical
  call the plan does not make is yours: make it and report it.
- Short and plain. No statement about cost and no count of model calls in anything that ships.
- Local agents only, cut by file ownership, each in its own worktree under
  `/Users/richlabarca/LocalCode/purlin-wt/`. No cloud sessions.
- No push, no tag, no `purlin:sign`. `python3 dev/windows_run.py` pushes and deletes its own
  run branch; that is allowed. `purlin:audit` runs against this repository only in step 4 of
  the plan's integration.
- Look at anything visual with playwright from the `.venv` before saying it is done.
- Report outcomes as they are. A finding that did not hold, a test that waits, a thing left
  unbuilt: say so.

## Step 0: the starting state

`git status` is clean. The last commit added plan files, which puts the anchor's 8 rules out of
date: run `python3 scripts/run/purlin_run.py --test --commit --project-root .` once and confirm
it ends `465 rules. 465 pass their tests.` Read each `> Highest-*` line of the specs the plan
touches before a lane takes a number.

## Step 1: the three lanes

Launch `audit`, `proofs` and `words` at once, as section 4 of the plan cuts them, each with the
lane brief. `words` quotes lines lane `audit` builds: its tests that wait on that code are named
in its report and clear at integration. Each lane's tests for a new rule build a sample project
at test time and use the fake `claude`; none audits Purlin's own code and none reaches a real
model.

## Step 2: integration

Section 5 of the plan, in its order. Three things to know from the last round:

- An audit with the real model runs detached, one `--feature` at a time, and a file changed in
  the checkout while it runs stops it. Edit nothing on `main` while one runs.
- A background command is stopped after two hours. Chain long work in a script started with
  `nohup`, and wait on a marker file.
- A reviewer that built none of the code found 11 faults last round. Do not skip step 5.

## Then stop and report

The sweep's and the run's numbers; for each of Purlin's weak rules, which of the three ways it
ended; each proof before and after; every line a person reads that a lane chose; what the
reviewer found and what was fixed; anything left unbuilt; and the calls left for the owner,
which already include: reading `docs/audit.md`; the `together` and `manual` slides not yet
published; the 29 specs never audited; then `purlin:sign`, the tag and the pushes, which are
the owner's.
