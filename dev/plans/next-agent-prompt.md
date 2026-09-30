# Prompt for the next session: decision 100, the sanity checks, the owner's review

Paste everything below the line into a new session opened in
`/Users/richlabarca/LocalCode/purlin`.

---

You are continuing Purlin 0.10.0, a Claude Code plugin for spec-driven development that uses
itself. The owner has closed decisions 60 to 99, and all of them are built and proven on `main`:
the product work of decisions 94 to 97, Windows (86 proofs tagged `@env(windows)`, 13 tagged
`@env(macos)`), sanity check 3 applied in phase 4, every page of the docs read again against
the code with the screenshots retaken, and the five answers of decision 99. Every rule
passes on the Mac and, where tagged, on Windows. Decision 100 is closed and not built. Your job
is what is left before the handover: decision 100, the further sanity checks, and getting the
owner's review done.

## Read first, in this order, in full

1. `dev/plans/handoff.md`: where the tree is, what is left, the words for the owner to read,
   the small things known and not fixed, and how the owner wants work done.
2. `dev/plans/three-levels.md`, decisions 60 to 99 (search `60. **`). Later decisions amend
   earlier ones; the later holds.
3. `dev/plans/phase4-interfaces.md`: what phase 4 built, where it differs from
   `dev/plans/phase4-contracts.md`, the calls left, "The pages", what fan-out 2 and its
   integration did to `README.md` and `docs/`, and "Decision 99", what its lanes built and left.
4. `dev/plans/sanity-3.md`, sections 1, 2 and 9 to 11: how sanity check 3 was run and what the
   next check must add.
5. `dev/plans/windows-untagged-failures.txt`: the tests that fail on Windows and that no rule is
   tagged for.
6. `CLAUDE.md`, `references/spec_quality_guide.md`, `references/writing_style.md`.

## How to work

- Maximum parallelization, cut by ownership of files, as the memory file
  `feedback-parallel-by-file-ownership` and `handoff.md` describe. Use a workflow to fan out
  agents; every agent is Opus. The owner has opted in to workflows for this project. A workflow
  runs about ten agents at a time and queues the rest; say so when you report.
- Before any fan-out that changes files: have a planning agent cut the work into lanes in which
  every file has one owner, and write the contracts between lanes word for word. The shared
  helpers `dev/skill_checks.py`, `dev/mcp_project.py`, `dev/sign_project.py`,
  `dev/run_project.py`, `dev/reports_project.py`, `dev/conftest.py` and `dev/fake_claude.py`
  are frozen during a fan-out.
- Each agent has its own worktree under `/Users/richlabarca/LocalCode/purlin-wt/<name>` and its
  own scratch folder. No lane stages a generated file: `scripts/report/purlin-report.html`,
  `purlin-report.html`, `.purlin/evidence/**`, `.purlin/tests.md`, `.purlin/report-data.js`,
  `.github/workflows/purlin.yml`, `docs/images/**`. Integration rebuilds them once.
- A sanity check is a fresh agent that reads and runs, and changes nothing: it ends in a report
  and questions, and the fixes it finds go through a planned fan-out afterwards.
- An agent that meets a call no decision makes builds the rest, leaves that thing as it is, and
  reports it. Technical calls you rule on and write down; any word a user reads, and any change
  to what the product does, goes to the owner with the question UI.
- Questions are asked from the root: what the thing is for in plain words, then the question,
  then two to four options with what each means for a user, always with the option that removes
  the thing. No function names, no file names, no unexplained term. The question window covers
  the reply, so anything the owner needs to answer goes inside the question.
- `export PATH=/opt/homebrew/opt/dotnet@8/bin:/Users/richlabarca/LocalCode/purlin/.venv/bin:$PATH`
  first, in every shell.
- Before an agent breaks code on purpose to check an assertion, it makes sure the break cannot
  reach the real `claude` program or any real service. A file is restored with
  `git checkout -- <that file>`, never `git checkout -- specs/`.
- A status on a project whose anchor names an `https` source reaches the network; the 0.9.5
  fixture under `dev/fixtures/upgrade-0.9.5/` carries one. Run no status there unless a network
  call is what you want.
- A test tied to a Windows proof stays able to run on a real Windows machine: no Unix-only call
  on its path, paths compared in one spelling, bytes compared with line endings in mind. A rule
  that carries a Windows proof keeps it, with its tag and its marker, through any split.
- Look at anything visual with playwright from the `.venv`, headless, at 1500, 1280, 1024, 768
  and 390 pixels, in both themes, before telling the owner it is done.
- Push nothing but the one temporary run branch a remote run pushes, tag nothing, open no pull
  request, run no `purlin:audit` and no `purlin:sign` against this repository. The owner runs
  the audit and signs.
- Acceptance is the full sweep, `bash dev/run_tests.sh`, with 0 failed, and this repository
  through its own tool, `python3 scripts/run/purlin_run.py --test --all`, with every marker tied
  and every rule passing except those that wait for Windows; then the same with `--commit`.
  Never edit a number to make a sweep pass.

## The work, in order

1. **Decision 100: an anchor is a set of rules for the whole project.** Read it in
   `three-levels.md` and `handoff.md`, "What is left", item 1. The owner asked for a plan
   first. Have a planning agent cut the work into lanes by ownership of files, as phases 3 and
   4 were cut (`phase3-plan.md` section 4 is the ownership), and write word for word every line
   a person would read that this changes: the warning for a spec that still names an anchor,
   the terminal's counts, the dashboard's section, the formats, the release notes, the slide on
   anchors. Put those words and the two things decision 100 leaves open to the owner with the
   question UI, and wait. Then build it, integrate, prove, and run `purlin:test --remote` once:
   it pushes one temporary run branch and nothing else. The 78 tests that fail on Windows and
   that no rule is tagged for stay as they are (decision 99).
2. **The further sanity checks**, each its own fresh agent, in the order the owner picks:
   - `purlin:spec-from-code` run for real on small real projects, one of which carries a test
     that fails before the run, so decision 66's clause about failing tests is tried; the
     agents count existing tests one way (`sanity-3.md` section 9, last line).
   - a QA person writes proofs;
   - an upgrade from a real 0.9.5 project;
   - a hostile reviewer who tries to make an unproven rule read as proven.
   Decision 64 also asks that the docs be read against the rules by a fresh agent before every
   release; the last such reading is phase 4's.
3. **Integrate and prove** whatever the checks and the answers changed, as "How to work" says,
   then bring `handoff.md` up to date and write the prompt for the session after you.

## What the owner still has to read

- `RELEASE_NOTES.md` 0.10.0, `README.md`, every page under `docs/`, and the slides.
- The words agents chose where no decision gave them: the table in `handoff.md` under "Words for
  the owner to read", which points into `phase3-interfaces.md` and `phase4-interfaces.md`.
- The 55 readings of `phase2-questions.md`, to say which to reverse.

Then the handover to the work machine, which is the owner's: `dev/plans/` is deleted (it is
history, and it ships), the work is pushed as a branch, and on the work machine
`dev/manual/check_azure_remote.py` runs against a real Azure DevOps project, then
`purlin:audit`, `purlin:sign`, the push of the tag and the release.

When you have read the files, tell the owner in a few lines what you understand the work to be,
then ask which sanity check comes first.
