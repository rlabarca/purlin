# Rules shared by every lane brief

Each brief repeats the rules that matter to it. This file is the full list, kept once.

## Where you work

- Create your worktree from the repository with
  `git worktree add /Users/richlabarca/LocalCode/purlin-wt/<lane> -b lane/<lane> evidence-workflow`
  and do every edit, test run and commit inside it. Never edit
  `/Users/richlabarca/LocalCode/purlin` (the main tree) except where your brief names an
  on-disk path there.
- Read only `dev/plans/evidence-workflow.md` (in full, first), `design/readme.md` where your
  brief says so, and your brief. Do not read `dev/plans/evidence-workflow-plan.md` or any
  other lane's brief.
- `specs/` is frozen: touch only the files your brief names.
- Do not push. Do not tag. Do not run `dev/bump_version.sh`. Do not edit `dev/plans/`.

## Vocabulary

- These words must not appear in any file you write, comments and strings included: audit,
  gauge, HOLLOW, PROVABLE, receipt, platform, `@on`, mode, mutation score, caught score,
  records branch, Pages, forge, queue, CODEOWNERS, approver rule. One exception: the Python
  name `sys.platform` where the operating system must be read.
- No emoji anywhere, including CLI output, PR comments and test fixtures.
- Names to use: git host (GitHub or Azure DevOps), test strength, review list, approver list,
  "breaks" in prose with `mutation_engine` in config and code, `purlin.yml` for the workflow,
  `@env(windows|macos|linux)` for OS-scoped proofs, record, approval, gate.
- Prose follows `design/readme.md` "Content fundamentals": plain, declarative, second person
  for the reader, third person for the system, exact numbers, limits stated, sentence case.

## Code

- Python 3.9 floor; every `open()` passes `encoding='utf-8'`; stdlib only, no third-party
  package anywhere under `scripts/`.
- Purlin is loaded two ways and both must work: `claude --plugin-dir <this checkout>` for
  framework development, and installed from the marketplace, where the plugin is a copy under
  `~/.claude/plugins/cache/purlin/purlin/<version>/`. A consumer project carries no
  `scripts/` and no `dev/`; anything a consumer runs lives under `scripts/` and is reached
  through `${CLAUDE_PLUGIN_ROOT}` or the project's own `.purlin/` copies. Nothing under
  `scripts/`, `skills/`, `agents/`, `references/` or `templates/` may cite `dev/` or this
  repository's own `specs/`.
- Before any test run: `export PATH=/Users/richlabarca/LocalCode/purlin/.venv/bin:$PATH`
  (the repository's virtualenv with pytest and the proof plugins lives in the main tree, not
  in a worktree). Before any xUnit run: `export PATH=/opt/homebrew/opt/dotnet@8/bin:$PATH`.
- Never `git checkout -- specs/`. The old proof plugins still write
  `specs/**/*.proofs-*.json` when tests run until phase 2 lands: never add or commit those
  files; remove them with `git clean -f specs/` (untracked files only) before committing.
- When you change a proof plugin under `scripts/proof/`, re-copy it to
  `dev/fixtures/consumer-ci/.purlin/plugins/` and to `.purlin/plugins/`.
- Never recreate a path the plan deleted in phase 0 (your brief lists the ones near your
  work).

## Commits

- Prefix from `references/commit_conventions.md` (`feat(<name>):`, `fix(<name>):`,
  `test(<name>):`, `docs:`, `chore:`), one logical change per commit, and end every message
  with these two lines:

```
Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01PA1RaoK77G1rNdVdQbavg6
```

- Set `PURLIN_SKIP_DIGEST=1` in the environment of every `git commit`.

## Finishing

1. Run the acceptance command from your brief; it must pass.
2. `git rebase evidence-workflow` inside your worktree, then run the acceptance command again.
3. `git status` clean (after `git clean -f specs/`).
4. End your final message with the DONE note in this shape:

```
DONE <lane>
branch: lane/<lane>  head: <sha>
files: <created / rewritten / deleted, one line each with line counts before and after>
tests: <acceptance command> -> <pytest summary line or pass/fail>
decisions: <each choice not settled by the brief, one line with the reason>
blocked: <none, or the last failure output verbatim>
```
