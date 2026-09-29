# Prompt for the next session: the product work of decisions 94 and 95

Paste everything below the line into a new session opened in
`/Users/richlabarca/LocalCode/purlin`.

---

You are continuing Purlin 0.10.0, a Claude Code plugin for spec-driven development that uses
itself. The owner has closed decisions 60 to 96. Decisions 60 to 93 are built and proven on
`main`. Your job is to build decisions 94, 95 and 96, then run sanity check 3, then the docs.

## Read first, in this order, in full

1. `dev/plans/handoff.md`: where the tree is, what is left, how the owner wants work done.
2. `dev/plans/three-levels.md`, decisions 60 to 96 (search `60. **`). Later decisions amend
   earlier ones; the later holds. Decisions 94, 95 and 96 are your work.
3. `dev/plans/phase2-questions.md`: the section "One sensible reading" is 55 changes the owner
   has approved to be applied; "For the owner" and "Windows" are answered by decisions 94 and 95.
4. `dev/plans/phase2-report.md`: "Where the product does not do what its rule says", "Gaps
   left", and "The rules that must hold on Windows", which holds the list of 90 rules.
5. `CLAUDE.md`, `references/spec_quality_guide.md`, `references/writing_style.md`.

## How to work

- Maximum parallelization, cut by ownership of files, as the memory file
  `feedback-parallel-by-file-ownership` and `handoff.md` describe. Use a workflow to fan out
  agents; every agent is Opus. The owner has opted in to workflows for this project.
- Before any fan-out: have a planning agent cut the work into lanes in which every file has one
  owner, and write the contracts between lanes word for word. The test files are already one
  per spec; `dev/skill_checks.py`, `dev/mcp_project.py`, `dev/sign_project.py`,
  `dev/run_project.py` and `dev/reports_project.py` are shared helpers and are frozen during a
  fan-out.
- Each agent has its own worktree under `/Users/richlabarca/LocalCode/purlin-wt/<name>` and its
  own scratch folder. No lane stages a generated file; integration rebuilds them once.
- A workflow runs about ten agents at a time and queues the rest. Say so when you report.
- An agent that meets a call no decision makes builds the rest, leaves that thing as it is, and
  reports it. Technical calls you rule on and write down; any word a user reads, and any change
  to what the product does, goes to the owner with the question UI.
- Questions are asked from the root: what the thing is for in plain words, then the question,
  then two to four options with what each means for a user, always with the option that removes
  the thing. No function names, no file names, no unexplained term. Put prose and tables in the
  reply before the question UI opens only if the owner can read them without them: the question
  window covers the reply, so anything the owner needs to answer goes inside the question.
- Put `/opt/homebrew/opt/dotnet@8/bin` first on PATH for every test run.
- Before an agent breaks code on purpose to check an assertion, it makes sure the break cannot
  reach the real `claude` program or any real service.
- Look at anything visual with playwright from the `.venv`, headless, at 1500, 1280, 1024, 768
  and 390 pixels, in both themes, before telling the owner it is done.
- Push nothing, tag nothing, run no `purlin:audit` and no `purlin:sign` against this
  repository. The owner runs the audit and signs.

## The work, in order

1. **Decisions 94, 95 and 96**, as product work: the code, the rule, the proof and the marked test
   together; every proof one case of at most 60 words. This includes the 55 readings, the
   product faults they settle, the split of the rules that list several things, and Windows:
   the remote run that runs only tagged tests, the four probable faults, the trimmed and
   extended list with one `@env(windows)` proof per rule, the six tests. Show the owner the
   final Windows list before any rule is marked (decision 82).
2. **Integrate and prove**: full sweep `bash dev/run_tests.sh` with 0 failed; this repository
   through its own tool with every marker tied and every rule passing; then the same with
   `--commit`.
3. **Windows, for real**: `purlin:init` writes the runner file for this repository; run
   `purlin:test --remote` once. This pushes one temporary branch, which is the one push an
   agent may make. Ask the owner before the first remote run.
4. **Sanity check 3** (decision 64): every statement in `README.md` and `docs/` against the
   rules and proofs; `purlin:spec-from-code` run for real on three small real projects with
   tests (Python, JavaScript, C#) at each gate, held to decisions 66 and 81. A statement no rule
   covers gets a rule, a proof and a test by default. It ends in a report and questions.
5. **Every page is read again** (decision 63), with the screenshots retaken last. The slides are
   ahead of the docs in places: the ten-minute path uses `purlin:spec` and `purlin:build`.
6. Bring `handoff.md` up to date, and write the prompt for the session after you.

## What the owner still has to read

- The 55 readings of `phase2-questions.md`, to say which to reverse.
- The words agents chose where no decision gave them: section 9 of `phase1-plan.md`, and the
  list in `handoff.md` under "Words for the owner to read".

When you have read the files, tell the owner in a few lines what you understand the work to be
and how many lanes you expect, then start.
