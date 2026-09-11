---
name: test
description: Run tests and emit proof files with coverage report
---

Run tests (unit tier unless `--all`), emit proof files via write-scoped overwrite, and report coverage per feature.

This skill is the **single owner of test execution**. `purlin:build` and `purlin:verify` delegate
here rather than invoking a runner themselves, which is also why remote execution lives here:
pushing a branch and pulling a runner's proof commits is writing, and `purlin:verify` is a
read-only gate. See `references/remote_verification.md`.

## Usage

```
purlin:test [feature]           Run tests for a specific feature (unit tier)
purlin:test                     Run all unit-tier tests
purlin:test --all               Run all tests across all tiers
purlin:test --local             Skip the remote path; report runner-gated proofs as awaiting
```

## Step 1 — Detect Test Framework

Read `.purlin/config.json` for `test_framework`. If set to a specific framework, use it. If `"auto"` or missing, detect from project files using the same heuristics as `purlin:init` Step 3 (see `references/supported_frameworks.md` for the full detection logic).

## Step 1.5 — Classify Tiers

Before running anything, split the tiers this run covers into two groups and say so.

1. Read the declared tier of every proof in scope from the spec's `## Proof` section (the `@unit`,
   `@integration`, `@e2e`, `@windows` tags).
2. A tier is **runner-gated** when it cannot execute on an arbitrary developer machine. `windows`
   is the only one (`specs/_anchors/schema_proof_format.md` RULE-4). Everything else is
   **locally-runnable**.
3. Report the split before the first test runs:

```
Tiers in scope:
  locally-runnable: unit (41 proofs), integration (12 proofs)
  runner-gated:     windows (2 proofs), which cannot run on darwin
```

Naming what cannot run here up front is the point. A run that silently skips a platform and then
reports PASSING is the defect this step exists to prevent: the rule read PASS off a local proof
while nothing had ever proved the platform the project claims to support.

Runner-gated proofs are **never** run locally by substituting something else. A simulated Windows
path is not a Windows proof. If no runner is available they report `AWAITING RUNNER` and the run
continues. Warn, never block.

## Step 2 — Run Tests

### Step 2a — Locally-runnable tiers

```bash
# pytest (unit tier)
pytest -m "not integration"

# pytest (all tiers with --all)
pytest

# jest (unit tier)
npx jest --testPathPattern="unit"

# jest (all tiers with --all)
npx jest
```

The proof plugins (`scripts/proof/pytest_purlin.py`, `scripts/proof/jest_purlin.js`, `scripts/proof/shell_purlin.sh`) emit `<feature>.proofs-<tier>.json` next to the spec file. This is a **write-scoped overwrite** keyed by `(feature, tier, test_file)`: each run replaces the tested feature's entries from the test files it actually executed, reaps entries whose test file no longer exists, and preserves everything else. Two test files covering one feature at one tier can therefore run in any order, in separate processes. See `references/formats/proofs_format.md`.

### Step 2b — Runner-gated tiers (the remote path)

Run this only when Step 1.5 found runner-gated proofs with no result at their tier, and
`--local` was not passed.

**If no workflow is configured for that tier**, do not run anything. Offer setup:

```
2 proofs are declared @windows and no workflow proves that tier.

They will report AWAITING RUNNER until a Windows host runs them. I can scaffold a
GitHub Actions workflow that runs them on windows-latest and commits the proof file
back to this branch.

→ Set it up? (the template is in references/remote_verification.md)
```

Scaffold from the template in `references/remote_verification.md` only on a yes. Never write a
workflow file unasked: it changes what runs on every push to the repository.

**Init is not the place for this.** `purlin:init` writes the `remote_verification` config field
at its default and asks nothing about runners. Setup is offered on discovery, because a project
with no runner-gated proofs has no runner to configure and the question has no answer yet.

**If a workflow is configured**, run the remote loop:

1. **Push the current branch.** `git push -u origin HEAD`. The runner proves what is on the
   branch, so anything uncommitted is not being verified: commit first, or report the gap.
2. **Dispatch the workflow** for the runner-gated tier and capture its run id
   (`gh workflow run <name> --ref <branch>`, then `gh run list` to find the id).
3. **Await it** (`gh run watch <id>`). Report the wait; a Windows runner is minutes, not seconds.
4. **Pull the proof commits it pushed back.** `git pull --ff-only`. The workflow commits the proof
   files it wrote, stamped with a `Purlin-Runner:` trailer. Step 4 below does not re-commit them;
   they arrived already committed.
5. If the workflow failed, report the failing proofs with the diagnosis framework in
   `references/spec_quality_guide.md` ("When Tests Fail") and route to `purlin:build`. Do not fix
   them here.

**Bound the loop at 3 rounds**, matching `skills/audit/SKILL.md` and `skills/verify/SKILL.md`. A
fourth round means the remote failure is not converging; report what failed and stop rather than
spending another CI run on it.

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
⚠ REMOTE VERIFICATION NOT CONVERGING: 3 rounds, <tier> still failing.

  <feature>: PROOF-N (@<tier>) failed on <runner>
  → Run: purlin:build <feature>

Stopping rather than dispatching a fourth run.
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

### Proof File Freshness Check

After tests run, before reporting results, verify that proof files (`*.proofs-*.json`) were modified AFTER the test command started.

**First check whether any test ran at all.** If the runner collected zero tests, the proof
plugin is working perfectly — there was simply nothing to emit. Report that instead, because
sending someone to re-scaffold working infrastructure wastes their time and teaches them to
distrust the warning:

```
No tests found. The proof plugin is fine — there is nothing to emit yet.
→ Run: purlin:build <feature> to write code and tests from the spec
```

Only if tests DID run and proof files are still stale or absent has the plugin failed to emit:

```
WARNING: <N> tests ran but proof files were not updated. The proof plugin may not be loaded.
→ Check: is the proof plugin registered in conftest.py / jest.config.js?
→ Run: purlin:init --force to re-scaffold the proof plugin
```

The freshness check applies to locally-runnable tiers only. A runner-gated tier's proof file was
written on another machine and arrived by `git pull`, so its mtime says when it was fetched and
proves nothing about when it ran. Provenance for those comes from the commit trailer, which is
what Step 3 reports.

Never write proof JSON files directly. Only the test framework plugin writes proof files.

## Step 3 — Report Coverage

Call `sync_status` after tests complete. Display the full result. **This is not optional** — without `sync_status`, the agent doesn't know if coverage is complete.

Distinguish **locally-proved** from **remotely-proved**. They were verified on different machines,
and the remote one is the thing the developer cannot check by re-running:

```
Test results:
  auth_login: PASSING (3/3 rules proved)
  static_checks: PASSING (35/35 rules proved)
    @windows: proved remotely 2 hours ago (github-actions/windows-latest)
  locking: PASSING (1/1 rules proved)
    ⚠ AWAITING RUNNER: 1 proof declared @windows with no result — PROOF-2
  user_profile: PARTIAL (1/2 rules proved)
    RULE-2: NO PROOF → write a test with @pytest.mark.proof("user_profile", "PROOF-2", "RULE-2")
    → PARTIAL means more tests needed to reach PASSING.
  webhook_delivery: FAILING (2/3 rules proved)
    RULE-1: FAIL → Fix: test_webhook_basic is failing
```

The runner identity and the time come from `sync_status`, which reads them from the proof commit's
`Purlin-Runner:` trailer via `git log -1` (`specs/mcp/sync_status.md` RULE-48). Do not claim a
proof was proved remotely from the proof entry alone: the entry says a test passed, and only the
commit says where.

## Step 4 — Commit proof files (mandatory)

After proof files are written, commit them:

```
git add specs/**/*.proofs-*.json
git commit -m "test(<feature>): <passed>/<total> rules proved"
```

For multi-feature runs:
```
git commit -m "test: run unit tier (<passed>/<total> features fully proved)"
```

Proof files a runner committed back are already committed: `git pull` brought them in with their
`Purlin-Runner:` trailer intact. Do not amend or re-commit them: the trailer is the only record of
which runner proved them.

Proof files are project records, not ephemeral build artifacts. Uncommitted proof files make sync_status output inconsistent with what purlin:verify and purlin:drift see.

## Writing Tests with Proof Markers

When tests are missing, write them with proof markers. For marker syntax (pytest, Jest, Shell), see `references/formats/proofs_format.md`. For test quality rules (what makes a proof STRONG vs HOLLOW), see `references/audit_criteria.md`.

## Note

This skill does NOT issue verification receipts. That is `purlin:verify`'s job. This skill runs tests, emits proof files, and reports coverage.
