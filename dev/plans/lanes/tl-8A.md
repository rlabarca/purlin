# Lane 8A: CI runs where evidence is decided, and a push is a person's act

Plan: `dev/plans/three-levels.md` (in full; decisions 25, 26 and 27 are yours). Rules:
`dev/plans/lanes/tl-_rules.md` (in full). Worktree `/Users/richlabarca/LocalCode/purlin-wt/8A`,
branch `lane/8A` off `three-levels`. **Do not push this branch. Ever.** The orchestrator merges
from your local branch.

## What you own

### The workflow (decision 26)

- `templates/purlin.yml` and this repository's `.github/workflows/purlin.yml` (they must match;
  `dev/test_init_scaffold.py` or `dev/test_consumer_ci.py` may already compare them):
  `on:` becomes `pull_request:` plus `push:` with `branches: [<protected>, 'run/**']`, where
  `<protected>` is the default branch init reads at scaffold time (`main` in the template,
  substituted the way the release pin is). Add a last step, `Check the gate`, that runs
  `python3 "$PURLIN_ROOT/scripts/ci/gate_check.py" --check` and fails the job when it exits 1.
  Keep the fork guard, the artifact and the matrix.
- `templates/purlin.azure-pipelines.yml`: the same triggers (`trigger: branches: include:
  [<protected>, run/*]`, `pr:` on) and the same last step.
- `scripts/run/purlin_run.py` `--ci`: commit records and briefs only when the run is on the
  protected branch or a `run/*` branch (read `GITHUB_REF_NAME` / `GITHUB_HEAD_REF` /
  `BUILD_SOURCEBRANCHNAME`); on a pull request run write nothing to git, still post the comment
  and publish the dashboard, and print `Pull request run: the records stay on the runner; the
  run on <protected> writes them.` `scripts/run/ci.py` and `records.py` follow.
- `scripts/init/scaffold.py`: the workflow text, the branch rules it prints (rule 1 now says
  the `purlin` check is required and fails when the gate is not met), the summary line under
  `passed` (RULE-13 stands: no workflow unless `--ci`). `scripts/init/update.py`: an existing
  `purlin.yml` with the old `on: push:` is refreshed to the new triggers and the gate step;
  the migration table names what it detects.

### The push (decision 27)

- `scripts/run/remote.py`: `run_remote` pushes to a run branch `run/<branch>-<sha7>` with
  `PURLIN_REMOTE_RUN=1` in the push's environment, watches the run, pulls the run branch's
  record commit onto the local branch (`git pull --ff-only origin run/...` or a fetch and
  merge that leaves the records as one commit on the local branch), then deletes the remote
  run branch. On a detached head or a dirty tree it refuses before pushing. Azure keeps its
  `TODO(ado-remote)` and prints the URL, but pushes to a run branch the same way.
- `scripts/hooks/pre-push.sh`: before it runs the tests, refuse when `CLAUDE_CODE_SESSION_ID`
  is set and `PURLIN_REMOTE_RUN` is not: print `purlin: an agent does not push. A person runs
  git push.` and exit 1. `--no-verify` still skips the hook (document it as the person's
  override, not the agent's). `.purlin/hooks/pre-push` (the shim) is unchanged.
- `agents/purlin.md` NEVER list: never push, never open a pull request, never delete or
  rewrite a remote branch; the one exception is the remote run, which the audit skill owns.
- `skills/audit/SKILL.md` (`--remote`: the run branch, what comes back, what is deleted);
  `skills/init/SKILL.md` (triggers, the gate step, the three branch rules); `skills/status`
  and `skills/drift` if they name pushing. `references/purlin_commands.md` (the `--remote`
  row), `references/hard_gates.md` (the CI section: triggers, where records are written, the
  gate step, the pre-push guard; the sentence "CI publishes its own evidence; a person pushes
  theirs"), `references/glossary.md` (push, remote run, run branch, protected branch),
  `references/commit_conventions.md` (the record commit lands on the protected branch or a run
  branch only). Lane 8B rewrites the docs; you touch none under `docs/`.

### Tests and specs

- `dev/test_init_scaffold.py`, `dev/test_init_update.py`, `dev/test_run_script.py`,
  `dev/test_records.py`, `dev/test_consumer_ci.py` (the fixture's workflow if it carries one),
  `dev/test_init_e2e.sh` (the gate walk: a CI record on the protected branch, a pull request
  run that commits nothing, a `run/*` run that commits), `dev/test_pre_push_hook.py` (the
  guard: refused with the session variable, allowed with the remote-run variable, allowed with
  neither), and a new test for `run_remote`'s branch, pull and delete with `git` and `gh`
  standing in.
- Specs: `specs/init/scaffold.md` (the workflow rules and the printed rules), `specs/init/update.md`,
  `specs/run/records.md` (RULE-4 stands from 7B; add the where-CI-commits rule and the
  pull-request-commits-nothing rule; RULE-12 `--remote` rewritten), `specs/run/run_script.md`
  (the gate step is the workflow's, but the `--ci` commit condition is the run script's),
  `specs/hooks/pre_push_hook.md` or wherever the hook's rules live (the guard), and
  `specs/instructions/purlin_agent.md` (the NEVER rows). Keep every marker aligned.

## Acceptance

```
pytest dev/test_init_scaffold.py dev/test_init_update.py dev/test_run_script.py dev/test_records.py dev/test_consumer_ci.py dev/test_pre_push_hook.py dev/test_skills.py dev/test_vocabulary.py
bash dev/test_init_e2e.sh
CLAUDE_CODE_SESSION_ID=x sh scripts/hooks/pre-push.sh </dev/null; echo "exit $?"     (1, with the line)
bash dev/run_tests.sh
```

Report in the DONE shape of `tl-_rules.md`, with the spec maxima per touched spec, the test
delta, and the exact trigger block and gate step as written, so lane 8B can quote them.
