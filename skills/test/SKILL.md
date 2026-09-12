---
name: test
description: Run tests and emit proof files with coverage report
---

Run tests (unit tier unless `--all`), emit proof files via write-scoped overwrite, and report coverage per feature.

This skill is the **single owner of test execution**. `purlin:build` and `purlin:verify` delegate
here rather than invoking a runner themselves, which is also why remote execution lives here:
pushing a branch and pulling a runner's proof commits is writing, and `purlin:verify` is a
read-only gate. See `references/remote_verification.md`.

**Pending migrations:** when `sync_status` opens with a pending-migrations advisory, stop and follow `references/purlin_commands.md#pending-migrations` before doing this skill's work.

## Usage

```
purlin:test [feature]           Run tests for a specific feature (unit tier)
purlin:test                     Run all unit-tier tests
purlin:test --all               Run all tests across all tiers
purlin:test --local             Skip the remote path; report platform-scoped proofs as awaiting
purlin:test --platform <id>     Target one platform: run it here if this host satisfies it,
                                otherwise dispatch just that platform's runner
```

## Step 1 — Detect Test Framework

Read `.purlin/config.json` for `test_framework`. If set to a specific framework, use it. If `"auto"` or missing, detect from project files using the same heuristics as `purlin:init` Step 3 (see `references/supported_frameworks.md` for the full detection logic).

## Step 1.5 — Classify Platforms

Before running anything, read the `Platforms:` block `sync_status` prints and show it. It is the
authority on what this host can prove and what needs a runner; do not recompute the split by hand.

```
Platforms: host macos 14.7.1 arm64
  local:  macos-14 (6 proofs); run with PURLIN_PLATFORM=macos-14
  runner: windows-2022 (2 proofs; github workflow purlin-windows-2022-proofs.yml)
```

A proof declares the platforms it must be proved on with a trailing `@on(<id>, ...)` tag; a proof
with no such tag is platform-agnostic and runs wherever the tests run. `local:` lists the declared
ids this host satisfies, with the `PURLIN_PLATFORM` value that makes the proof plugin write the
scoped file. `runner:` lists the declared ids it does not, with how a runner would reach each one.
An id that is neither registered in `.purlin/config.json` nor a family id (`windows`, `macos`,
`linux`) is listed as unregistered rather than dropped.

Three invariants hold whatever the block says:

1. **There is no local substitute for a platform.** A proof declared `@on(windows-2022)` is never
   run here by approximating it. A simulated Windows path is not a Windows proof.
2. **A missing runner warns and never blocks.** A platform with no runner configured, or one whose
   provider cannot be dispatched, leaves its proofs reporting `AWAITING RUNNER` and the run
   continues. Warn, never block.
3. **`PURLIN_PLATFORM` is set for the local run.** Without it the plugins fall back to the OS
   family, so a `macos-14` proof run here would land in `...@macos.json` and satisfy nothing the
   spec declared.

Naming what cannot run here up front is the point. A run that silently skips a platform and then
reports PASSING is the defect this step exists to prevent: the rule read PASS off a local proof
while nothing had ever proved the platform the project claims to support.

With `--platform <id>`, restrict this run to that one id: run it here when the `Platforms:` block
lists it under `local:`, and dispatch only its runner when it lists it under `runner:`.

## Step 2 — Run Tests

### Step 2a — The local run

Run the test command once per declared platform id the `Platforms:` block lists under `local:`,
prefixing each with `PURLIN_PLATFORM=<id>`, and once more with no prefix when the project has
platform-agnostic proofs only. Usually there is exactly one locally-satisfiable id, so this is one
run.

```bash
# pytest, proving the platform this host satisfies
PURLIN_PLATFORM=macos-14 pytest -m "not integration"

# pytest (all tiers with --all)
PURLIN_PLATFORM=macos-14 pytest

# jest (unit tier)
PURLIN_PLATFORM=macos-14 npx jest --testPathPattern="unit"
```

The proof plugins (`scripts/proof/pytest_purlin.py`, `scripts/proof/jest_purlin.js`, `scripts/proof/shell_purlin.sh`) emit `<feature>.proofs-<tier>.json` next to the spec file for a marker that declares no platform, and `<feature>.proofs-<tier>@<id>.json` for one that does, where `<id>` is `PURLIN_PLATFORM`. This is a **write-scoped overwrite** keyed by `(feature, tier, platform, test_file)`: each run replaces the tested feature's entries from the test files it actually executed, reaps entries whose test file no longer exists, and preserves everything else. Two test files covering one feature at one tier can therefore run in any order, in separate processes. See `references/formats/proofs_format.md`.

### Step 2b — The remote path

Run this only when Step 1.5 listed platforms under `runner:` whose proofs have no result, and
`--local` was not passed.

For each such platform, check `platforms.<id>.runner` in `.purlin/config.json`. **If it has a
`runner` block with `provider: github` and the workflow file it names exists**, dispatch it. **If
it has no runner block, or its workflow file is missing**, do not run anything for that platform:
offer setup instead (below). A `runner` block naming a provider other than `github` is reported as
not dispatchable and its proofs stay awaiting.

The dispatchable platforms run as one round:

1. **Push the current branch, once.** `git push -u origin HEAD`. Every runner proves the same
   commit, so this happens once and not once per platform. The runner proves what is on the
   branch, so anything uncommitted is not being verified: commit first, or report the gap.
2. **Dispatch every remote platform's workflow** in parallel and capture each run id:
   `gh workflow run <workflow> --ref <branch>` per platform, then `gh run list` to find the ids.
3. **Await them all** (`gh run watch <id>` per run). Report the wait; a platform runner is minutes,
   not seconds.
4. **Pull once, after every run has completed.** `git pull --ff-only`. Each workflow commits the
   scoped proof files it wrote, stamped with `Purlin-Runner:` and `Purlin-Platform:` trailers. One
   pull, not one per runner: a pull while another runner is still committing races it. If the pull
   reports that the branch moved because a late commit-back landed mid-pull, retry it once. Step 4
   below does not re-commit these files; they arrived already committed.
5. If a workflow failed, report the failing proofs with the diagnosis framework in
   `references/spec_quality_guide.md` ("When Tests Fail") and route to `purlin:build`. Do not fix
   them here.

**Bound the loop at 3 rounds**, matching `skills/audit/SKILL.md` and `skills/verify/SKILL.md`. A
fourth round means the remote failure is not converging; report which platform failed on which
runner and stop rather than spending another CI run on it.

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
⚠ REMOTE VERIFICATION NOT CONVERGING: 3 rounds, <platform> still failing.

  <feature>: PROOF-N (@on(<platform>)) failed on <runner>
  → Run: purlin:build <feature>

Stopping rather than dispatching a fourth run.
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

#### Offering setup for a platform with no runner

Setup is offered per platform, on discovery. **Init is not the place for this.** `purlin:init`
writes the `remote_verification` config field at its default and asks nothing about runners. A
project with no platform-declared proofs has no runner to configure and the question has no answer
yet.

```
2 proofs are declared @on(windows-2022) and no workflow proves that platform.

They will report AWAITING RUNNER until a host that satisfies windows-2022 runs them.
I can scaffold a GitHub Actions workflow that runs them on a windows-2022 runner and
commits the scoped proof file back to this branch, and register that workflow under
platforms.windows-2022 in .purlin/config.json so purlin:test can dispatch it.

→ Set it up? (the template is in references/remote_verification.md)
```

Only on a yes, and for that one platform, write both:

1. `.github/workflows/purlin-<id>-proofs.yml` from the template in
   `references/remote_verification.md`, substituting the platform id, the `runs-on` label, the
   per-framework setup block from the **Runner setup** column of
   `references/supported_frameworks.md`, and the test command.
2. The `runner` block in `platforms.<id>` of `.purlin/config.json`:
   `{"provider": "github", "runs_on": "<runs-on>", "workflow": "purlin-<id>-proofs.yml"}`,
   creating the `platforms.<id>` entry if the id is a family id with no entry yet.

Write neither without consent: a workflow file changes what runs on every push to the repository,
and the config field is the record of what this project dispatches. **This consent path is the one
place a skill other than `purlin:init` writes `.purlin/config.json`**, which is why
`references/drift_criteria.md` records `purlin:test` as the `platforms` field's owner. Write both
or neither: a workflow the config does not name is one this skill will never dispatch.

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

The freshness check applies to the local run only. A proof file a runner wrote arrived by
`git pull`, so its mtime says when it was fetched and proves nothing about when it ran. Provenance
for those comes from the commit trailers, which is what Step 3 reports.

Never write proof JSON files directly. Only the test framework plugin writes proof files.

## Step 3 — Report Coverage

Call `sync_status` after tests complete. Display the full result. **This is not optional** — without `sync_status`, the agent doesn't know if coverage is complete.

Report the platform lines as `sync_status` prints them, which is what distinguishes
**locally-proved** from **remotely-proved**. They were verified on different machines, and the
remote one is the thing the developer cannot check by re-running:

```
Test results:
  auth_login: PASSING (3/3 rules proved)
  static_checks: PASSING (35/35 rules proved)
    ✓ @on(windows-2022) proved remotely 2 hours ago (github-actions/windows-2022)
  locking: PASSING (1/1 rules proved)
    ⚠ AWAITING RUNNER: 1 proof declared @on(macos-14) with no result — PROOF-2
  user_profile: PARTIAL (1/2 rules proved)
    RULE-2: NO PROOF → write a test with @pytest.mark.proof("user_profile", "PROOF-2", "RULE-2")
    → PARTIAL means more tests needed to reach PASSING.
  webhook_delivery: FAILING (2/3 rules proved)
    RULE-1: FAIL → Fix: test_webhook_basic is failing
```

The runner identity and the time come from `sync_status`, which reads them per scoped proof file
from that file's own commit: `git log -1` on the file, the `Purlin-Runner:` trailer for the runner
and the `Purlin-Platform:` trailer cross-checked against the platform in the filename
(`specs/mcp/sync_status.md` RULE-48). Do not claim a proof was proved remotely from the proof entry
alone: the entry says a test passed, and only the commit says where.

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
`Purlin-Runner:` and `Purlin-Platform:` trailers intact. Do not amend or re-commit them: those
trailers are the only record of which runner proved them on which platform.

If `sync_status` reports an **undeclared platform result** (a scoped proof file whose platform no
proof declares), that file counts toward nothing. Offer `git rm` for it, with the reason: it is
usually a platform that was renamed or dropped from an `@on(...)` tag and left a file behind.
Removing a committed record needs consent, so offer rather than do it.

Proof files are project records, not ephemeral build artifacts. Uncommitted proof files make sync_status output inconsistent with what purlin:verify and purlin:drift see.

## Writing Tests with Proof Markers

When tests are missing, write them with proof markers. For marker syntax (pytest, Jest, Shell), see `references/formats/proofs_format.md`. For test quality rules (what makes a proof STRONG vs HOLLOW), see `references/audit_criteria.md`. For the mutation check, which is what catches a proof that passes against broken code, see `references/spec_quality_guide.md#mutation-check`: it runs before the commit that carries the proof when the project sets `mutation_checks: true`.

## Note

This skill does NOT issue verification receipts. That is `purlin:verify`'s job. This skill runs tests, emits proof files, and reports coverage.
