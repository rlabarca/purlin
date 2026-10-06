# Prompt for the next session: prompts and skills are tested like anything else

Start it only after the session that wrote this has finished: `dev/plans/handoff.md` then
opens with the state to start from. Paste everything below the line into a new session opened
in `/Users/richlabarca/LocalCode/purlin`.

---

You are continuing Purlin 0.10.0, a Claude Code plugin for spec-driven development that uses
itself. Local `main` is green and not pushed, tagged or signed. You have one job: build
decision 135, so that a project can test and keep evidence for the prompts and skills it
produces, and leave the repository green, audited and current again.

## Read first, in this order

1. `dev/plans/handoff.md`, in full. If it does not say the four audit fixes and the two
   evidence changes of decisions 132 and 134 are merged and the audit is current, stop and
   say so: the last session has not finished.
2. `dev/plans/ai-proofs-plan.md`, in full. It is the plan. Its section 2 holds the owner's
   answers; do not ask them again.
3. `dev/plans/three-levels.md`: decisions 100 to 135 (search `100. **`); later wins. Decision
   44 is the clean release.
4. `CLAUDE.md`; `references/writing_style.md`; `references/glossary.md`;
   `references/spec_quality_guide.md`; `docs/regulated.md`, the model for every doc page.
5. How the audit starts its model (`scripts/review/ai_audit.py`, `COMMAND` and `ask_model`),
   how a slow proof is left out and run (`scripts/mcp/purlin/frameworks.py`, `leave_out`),
   how a result is recorded (`scripts/run/evidence.py`), and how a planted bug is tried and
   settled (`scripts/review/planted_bug.py`, `audit_run.py`).

## How the owner works

- **Decisions close before anything launches.** A call that changes what a person reads or
  does, and that the plan does not make, is asked with the question UI, one decision at a
  time, from the root: what the thing is for, in plain words, with no file or function name
  a person would not know, the recommended option first, and everything needed to answer
  inside the question. A technical call is yours: make it and report it.
- **The least change.** In the owner's words: "make sure we are doing these additions with
  the least amount of change, in an elegant way.. dont just bolt this on.. ask me more
  questions if needed". Before a lane adds a concept, a file format or a command, it checks
  whether something Purlin has already does the job. Where the plan and the code disagree on
  what is least, ask.
- **Short and plain.** The docs are short (decision 133): a heading states the idea, a
  paragraph is two or three sentences, the only pictures are simple flow diagrams with each
  box's name in bold. Not every decision goes in a doc. No statement about cost, no count of
  model calls, no emoji.
- **A sign-off is optional**, and every line that names it says so. The owner has planned no
  signing: do not raise it.
- **The deck and the docs are changed when their source is.** The live deck is the Slides
  artifact `Purlin Overview v0.10.0`; publish a changed slide in the same round.
- **Local only.** No push, no tag, no `purlin:sign` (`sign.py --show` signs nothing and is
  fine), no cloud session. `python3 dev/windows_run.py` pushes and deletes its own run
  branch; that is allowed. Never `pkill` anything but your own process ids. Never touch
  `/Users/richlabarca/LocalCode/RLabGenMusic`.
- **Run with the project's `.venv` first on PATH**:
  `export PATH=/Users/richlabarca/LocalCode/purlin/.venv/bin:/opt/homebrew/opt/dotnet@8/bin:$PATH`.
- **Maximum parallelization, cut by ownership of files.** Each lane has its own worktree
  under `/Users/richlabarca/LocalCode/purlin-wt/` and its own scratch folder, and owns files
  no other lane writes. What one lane makes and another uses is fixed word for word before
  they start. A lane stages nothing under `.purlin/`.
- **Each fix starts from a test that fails first.** No test of the sweep reaches a real
  model.
- **Report outcomes as they are.**

## The job

1. **Fix the contracts**, alone, in one commit: the plan's section 5 names them. Read the
   code first; where a contract in the plan cannot be built as written, say what you changed
   and why.
2. **Build it in lanes**, as section 5 cuts them. Every lane's brief carries: the plan; the
   rules above; its files; that a rule and a proof are written to
   `references/spec_quality_guide.md`, with a proof naming the exact line or value a test can
   hold, since every spec here was just audited; that a format change goes in the same commit
   as its code with its `> Format-Version:` up by 1; and that its acceptance is its own tests
   and `bash dev/run_tests.sh --fast` with 0 failed.
3. **Merge, then the plan's section 6**, to the end: the full sweep; the clean full run and
   the Windows run; the audit of every spec the round changed, each finding worked by the
   build skill's steps (strengthen the test with the value the proof names, then
   `--settle`), never by changing code, rule or proof to clear a finding; the anchor audited
   last; a real session given the goal; `sign.py --show` not refusing.
4. **Rewrite `dev/plans/handoff.md`** for where it stands, delete this file and
   `dev/plans/ai-proofs-plan.md`, update the project memory, and stop.

## Then stop and report

- What was built, piece by piece, against the plan's section 3, and every place it differs.
- Every line a person reads that you chose, word for word.
- The format and schema numbers, before and after.
- What the real session did, and what it showed about the skills.
- The numbers: the sweep, the full run, Windows, the audit's closing sentence, and what
  `sign.py --show` printed.
- What you asked the owner and the answers; what is left.
