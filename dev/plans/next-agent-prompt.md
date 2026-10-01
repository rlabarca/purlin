# Prompt for the next session: finish decision 115's specs, then build decisions 100 to 115

Paste everything below the line into a new session opened in `/Users/richlabarca/LocalCode/purlin`.

---

You are continuing Purlin 0.10.0, a Claude Code plugin for spec-driven development that uses
itself. The specs on local `main` describe decisions 100 to 115; the code and tests still describe
decision 103. Your job: finish decision 115's spec rules, plan the build, run it with the lanes in
the cloud and integration on this Mac, then stop and report.

## Read first, in this order

1. `dev/plans/three-levels.md`: decisions 100 to 115 (search `100. **`); later wins. Earlier
   decisions carry "Reversed by" notes.
2. `dev/plans/handoff.md`: "Where the tree is" and "What is left".
3. `CLAUDE.md`, `references/spec_quality_guide.md`, `references/writing_style.md`,
   `references/review_criteria.md` ("Heuristic spot tests" is the owner's official text).
4. `dev/plans/d105-plan.md` for its contracts and lines a person reads; it predates decisions
   111 to 115 and was written when specs were still to change, so re-cut it (below).

## Step 1: decision 115's specs (alone, local, small)

Add, in the shape of the existing specs, with new numbers and raised `> Highest-*` lines:
- `specs/dashboard/purlin_report.md`: the header names the branch and commit the data describes
  and the time it was written, as in `main at a1b2c3d, written 10:42`.
- `specs/instructions/purlin_agent.md`: after merging work from a worktree, the agent runs
  `purlin:status` in the main checkout.
- `specs/mcp/server.md`: a tool call that names no `project_root` is refused with a one-line fix,
  not answered from the folder the session started in.
- `specs/instructions/purlin_docs.md`: the working-together page holds one paragraph saying each
  checkout has its own results and dashboard, and merging plus `purlin:status` updates the main one.
Commit them with the uncommitted decision 115 text if it is still uncommitted. Then
`python3 scripts/run/purlin_run.py --test` (no `--all`) to refresh the dashboard.

## Step 2: the build plan (one planning agent, local)

The specs are written; the build makes code and tests meet them. The planning agent cuts lanes by
file ownership of CODE and TEST files (each spec's `> Scope:` names its code), fixes every shared
interface word for word (reuse `d105-plan.md` section 2 where it still holds), and lists:
- which tests to delete (proofs cut in decisions 100 to 112), which to rewrite, which to add;
- the roughly 1,600 test comments to correct, each lane fixing those in the files it owns, the
  test changed and never the proof;
- the lines a person reads, in the shape of decisions 94 to 115;
- questions for the owner only where decisions 100 to 115 do not settle something.
Write `dev/plans/d115-plan.md` and commit it. Ask the owner any questions before Step 3.

## Step 3: the build, lanes in the cloud, integration local

- **Check the cloud credits first** (claude.ai settings, usage, "Cloud session credits"; they
  expire 2026-11-05). Budget about $5 to $8 per lane; tell the owner the planned spend before
  launching. If credits are short, run the remaining lanes locally.
- Push `main` as branch `d115/base`; launch each lane as its own cloud session with
  `claude --cloud "<prompt>" --model claude-opus-5-5`, run from a worktree checked out at
  `d115/base`. It needs a TTY: `script -q <log> claude --cloud ...`, then read
  `View: https://claude.ai/code/session_...` from the log. Never a routine, never the Agent tool's
  `isolation: "remote"` (it ran locally). Each lane pushes `lane/d115-<lane>` only.
- Watch for the branches with a Monitor on `git ls-remote origin 'refs/heads/lane/d115-*'`.
- Integration runs locally on this Mac as one agent: fast-forward merges in the plan's order,
  the full sweep `bash dev/run_tests.sh` to 0 failed, `python3 scripts/run/purlin_run.py --test
  --all` with every marker tied and nothing failed, then `--commit`, the dashboard looked at with
  playwright from the `.venv` (dark and light, 1500, 1024, 390), `dev/plans/handoff.md` updated.
- After integration, archive the cloud sessions in the claude.ai sidebar (the owner asked; use
  the Chrome extension; leave sessions that are not this work).

## Rules that hold throughout

- Environment: `export PATH=/opt/homebrew/opt/dotnet@8/bin:$PWD/.venv/bin:$PATH`.
- No push but the build's branches, no tag, no `purlin:audit` or `purlin:sign` against this
  repository, no real `claude` in tests, no network in tests (the `install` spec's one cheap model
  call is the exception, run only when its scope changes).
- Clean release (decision 44): retired things are deleted outright; only `RELEASE_NOTES.md` keeps
  history; only the 0.9.5 upgrade keeps what it needs.
- The deck is `dev/plans/deck/build_deck.py`, published to
  https://claude.ai/artifact/Rifxf2KXfH4CTzfQ9pZ9is; read the live slides before publishing (the
  owner edits them); `dev/plans/deck/check_deck.py` and `check_overlap.py` check fit and overlap.

## Then stop and report

Report the sweep's and the run's numbers, what the dashboard look found, the cloud spend, every
line a person reads that a lane chose, and anything left unbuilt. Then ask the owner whether to run
the real-skills QA check (three real Claude sessions with the plugin, one feature, one collision).
