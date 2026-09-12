# Remote Verification

Some proofs cannot execute on a developer's machine. A proof declared `@on(windows-2022)` needs a
Windows host; no amount of simulation on macOS proves it. Purlin calls the thing a proof is
declared on a **platform**, and a proof declared on one reports `AWAITING RUNNER` until a host that
satisfies that platform proves it.

Remote verification is how that proof gets run: `purlin:test` pushes the branch, a CI workflow runs
the proofs for one platform on a real host of that platform, and the workflow commits the
platform-scoped proof files it wrote back to the branch. `purlin:test` pulls them and reports them
as proved remotely, naming the platform.

This file is the authoritative reference for that loop. `skills/test/SKILL.md` implements it;
`specs/ci/verify_gate.md` governs the CI side.

## Platforms

A tier says what kind of test a proof is (`@unit`, `@integration`, `@e2e`). A platform says where
it must run. They are orthogonal, and a proof carries both:

```
- PROOF-2 (RULE-2): msvcrt locks a file a second process cannot write @unit @on(windows-2022)
- PROOF-3 (RULE-3): the file watcher fires on an APFS rename @integration @on(macos-14, macos-15)
```

`@on(...)` takes one or more platform ids. An id is `[a-z0-9][a-z0-9-]*`, because it becomes a
filename, a workflow name and an environment value. The grammar lives in
`references/formats/spec_format.md`, "Platform tags".

**Family ids need no configuration.** `windows`, `macos` and `linux` are built in, so a small
project writes `@on(windows)` with an empty config and gets a working report. A result on any
registered platform whose `os` is that family satisfies a family declaration: a `windows-2022`
result satisfies `@on(windows)`, and not the other way round.

**Anything more specific is a registry entry.** `.purlin/config.json` carries an optional
top-level `platforms` object:

```json
"platforms": {
  "windows-2022": {
    "os": "windows",
    "version": ">=10.0.20348",
    "arch": "x86_64",
    "label": "Windows Server 2022",
    "runner": {"provider": "github", "runs_on": "windows-2022",
               "workflow": "purlin-windows-2022-proofs.yml"}
  }
}
```

`purlin:init` never writes this field. `purlin:test` writes the `runner` block, and only with
consent, when it offers to scaffold a workflow (`references/drift_criteria.md`, Config Field
Ownership). A malformed entry is dropped, named in the `sync_status` preamble, and exits the CI
gate `2` in every mode: evidence read through a broken registry is unreadable evidence.

**`PURLIN_PLATFORM` is how a host says what it is.** The proof plugins read it: a marker that
declares platforms writes `<feature>.proofs-<tier>@<id>.json`, where `<id>` is `PURLIN_PLATFORM`
when set and the detected OS family otherwise. A marker that declares no platform writes the
agnostic `<feature>.proofs-<tier>.json`, whatever `PURLIN_PLATFORM` says. The runner sets the
variable once, in the job env; nothing else in a plugin branches on the host. That is what makes
"a simulated Windows path is not a Windows proof" true without a second code path
(`specs/proof/proof_common.md` RULE-16, RULE-17).

**Provenance is per file, from the commit.** Proof entries carry no timestamp and no runner field,
so a re-run that proves the same things commits nothing. `sync_status` runs `git log -1` on each
scoped proof file and reads two trailers off that commit: `Purlin-Runner:` for the runner identity,
`Purlin-Platform:` for the platform the runner was told it was. The filename claims a platform and
the trailer records one; when they disagree the report says `trailer says <id>` rather than
believing either silently.

## Where it lives, and why

Remote execution belongs to **`purlin:test`**. It is the only skill that runs tests:
`purlin:build` and `purlin:verify` delegate to it rather than invoking a runner themselves, so
both inherit the remote path with no change of their own.

That placement is not a preference. `purlin:verify` is a read-only gate: "NEVER modify code or
test files", and it must stay one. Pushing a branch, awaiting a workflow and pulling its commits
is writing. Putting it in `purlin:test`, which already commits proof files as its Step 4, keeps
verify's contract intact: verify reads the proofs a runner returned, and issues receipts.

## The loop

```
purlin:test  ->  push branch once  ->  dispatch one workflow per remote platform
             ->  await them all    ->  one pull  ->  proofs come back
   red  ->  report + "-> Run: purlin:build <feature>"
purlin:build  ->  fixes, commits
purlin:test  ->  ...  ->  green
purlin:verify  ->  reads the returned proofs, issues receipts   (never edits a file)
```

The branch is pushed **once**, not once per platform: every runner proves the same commit. The
workflows are dispatched in parallel and awaited together, and a single `git pull --ff-only`
follows all of them, because a pull per runner races the runners that are still committing. If a
late commit-back lands during the pull, retry the pull once.

**The loop is bounded at 3 rounds**, matching `skills/audit/SKILL.md` and
`skills/verify/SKILL.md`. A fourth round means the remote failure is not converging; report which
platform failed on which runner and stop rather than spending another CI run on it.

**An absent runner warns and never blocks.** A platform with no `runner` block, or one whose
provider `purlin:test` cannot dispatch, leaves its proofs reading `AWAITING RUNNER`. That is a
recorded gap, not a failure (`references/hard_gates.md`).

## Setting it up

Setup is offered **on discovery, not at init**. `purlin:init` does not configure a remote: a
project with no platform-declared proofs needs no runner, and asking about one during setup is a
question with no answer yet. When `purlin:test` finds proofs declared on a platform this host
cannot satisfy and no workflow configured for it, it offers, per platform, to write
`.github/workflows/purlin-<platform-id>-proofs.yml` from the template below **and** to add the
`runner` block to `platforms.<platform-id>` in `.purlin/config.json`. Both, or neither: a workflow
the config does not name is one `purlin:test` will never dispatch.

### Workflow template

Substitute `<platform-id>` (e.g. `windows-2022`), `<runs-on>` (e.g. `windows-2022`), `<VERSION>`
(the Purlin release to pin, from this repo's `VERSION` file), and the per-framework setup block and
test command for the project's `test_framework`.

```yaml
name: purlin-<platform-id>-proofs

on:
  push:
    # Loop guard, half one: the runner's own proof commit must not retrigger it.
    paths-ignore:
      - '**/*.proofs-*@<platform-id>.json'
  workflow_dispatch:

permissions:
  contents: write

jobs:
  proofs:
    runs-on: <runs-on>
    env:
      # The only per-runner input any proof plugin reads. It names the scoped
      # proof file the plugins write; without it they fall back to the OS
      # family and this runner's results would land under `windows`.
      PURLIN_PLATFORM: <platform-id>
      # Where the Purlin tooling is checked out. In the purlin repository
      # itself set this to `.` and delete the "Install Purlin tooling" step
      # below: that repository is the plugin.
      PURLIN_PLUGIN_ROOT: ${{ runner.temp }}/purlin
    steps:
      - uses: actions/checkout@v4
        with:
          persist-credentials: true

      - uses: actions/setup-python@v5
        with:
          python-version: '3.11'

      - name: Install Purlin tooling
        # A consumer checkout holds specs, proofs, receipts and `.purlin/`, and
        # no Purlin `scripts/`. Pin the tag: an unpinned clone changes what the
        # preflight enforces between one run and the next.
        shell: bash
        run: |
          git clone --depth 1 --branch v<VERSION> \
            https://github.com/rlabarca/purlin.git "$PURLIN_PLUGIN_ROOT"

      - name: Preflight
        # Fails the job when the project's `.purlin/plugins/` copies are stale
        # or a legacy migration is pending. Stale copies predate platform
        # scoping and write agnostic files that satisfy no platform, so the run
        # would look green and prove nothing.
        # -> Run: purlin:init --update and commit
        shell: bash
        run: python3 "$PURLIN_PLUGIN_ROOT/scripts/update/migrate.py" --check --project-root .

      - name: Install the test runner
        # Per-framework setup block, chosen from `test_framework`. See
        # references/supported_frameworks.md, "Runner setup".
        #   pytest        pip install pytest
        #   jest, vitest  npm ci
        #   xunit         dotnet restore
        #   php           composer install
        #   c             the platform's C toolchain (gcc via the image's
        #                 package manager on linux, Xcode command line tools on
        #                 macos, the MSVC build tools on windows)
        #   shell, sql    nothing beyond python3; `actions/setup-python` above
        #                 puts `python3` on PATH on all three runner OSes, which
        #                 is what those two plugins' embedded interpreter needs
        shell: bash
        run: pip install pytest

      - name: Run the <platform-id> proofs
        shell: bash
        run: python3 -m pytest <test files> -v

      - name: Commit the proof files back to the branch
        # Every `run:` step in this template is `shell: bash` on purpose.
        # PowerShell is the default shell on windows runners and it parses a
        # leading `@` in a path as a splat, so `'**/*.proofs-*@<id>.json'` is
        # not the argument you wrote. Git Bash ships on the windows images.
        shell: bash
        run: |
          git config user.name "github-actions[bot]"
          git config user.email "github-actions[bot]@users.noreply.github.com"
          # This platform's files only. The same run also writes agnostic
          # proof files for the markers that declare no platform, and those
          # must not travel back: they would overwrite the developer's own
          # results with this runner's.
          git add '**/*.proofs-*@<platform-id>.json'
          if git diff --cached --quiet; then
            echo "No proof-file changes to commit."
          else
            # Loop guard, half two, and the provenance sync_status reads back.
            # Both trailers in ONE -m, joined by a newline through printf.
            # Each -m is a separate paragraph and git parses trailers out of
            # the LAST paragraph only, so two -m flags leave `Purlin-Runner`
            # unreadable to `git log --format=%(trailers:key=Purlin-Runner)`
            # and the report says `runner not recorded` after a green run.
            # printf rather than a literal newline inside the argument: a bare
            # newline there would end the YAML block scalar.
            git commit -m "test: <platform-id> proofs from <runs-on> [skip ci]" \
                       -m "$(printf 'Purlin-Runner: github-actions/<runs-on>\nPurlin-Platform: <platform-id>')"
            # Several platform runners may commit to this branch at once, so
            # the first push can lose a race it did nothing wrong to lose.
            for attempt in 1 2 3; do
              if git pull --rebase origin "$GITHUB_REF_NAME" && \
                 git push origin "HEAD:$GITHUB_REF_NAME"; then
                exit 0
              fi
              echo "push attempt $attempt lost a race; retrying"
            done
            echo "could not push the proof commit after 3 attempts"
            exit 1
          fi
```

### What is load-bearing in that template

**`PURLIN_PLATFORM` in the job env (required).** It is the only thing that tells the proof plugins
which scoped file to write. Without it a `windows-2022` runner writes `...@windows.json`, which
satisfies `@on(windows)` but not `@on(windows-2022)`, and the report reads `AWAITING RUNNER` after
a green CI run.

**Both trailers, in one `-m` (required).** `Purlin-Runner:` is the only record of which runner
proved a file; without it the report reads `runner not recorded`, which is a gap, not a valid
state. `Purlin-Platform:` is what lets `sync_status` cross-check the platform the filename claims
against the one the runner was told. They must share a single `-m` argument: git builds one
paragraph per `-m` and parses trailers out of the last paragraph only, so a trailer in its own
`-m` is invisible to `git log --format=%(trailers:key=...)` while looking perfectly correct in
the workflow file and in `git log`. `specs/ci/verify_gate.md` RULE-7 enforces both trailers and
the single `-m`.

**The loop guard, both halves.** `paths-ignore` stops a `push` trigger; `[skip ci]` stops the
trigger paths `paths-ignore` does not cover. Either alone eventually loops.
`specs/ci/verify_gate.md` RULE-8 enforces both.

**`git diff --cached --quiet`.** Commit only when something changed. A workflow that commits
unconditionally produces one empty commit per push forever.

**The narrowed `git add`.** The runner proves the platform's proofs and, in the same test run, the
agnostic ones. Only the scoped files are this runner's to report. A `git add specs/` here sends the
runner's agnostic results back over the developer's.

**The pull-rebase-retry loop.** One branch, several platform workflows, one push target. A plain
`git push` fails when another runner committed first, and the job goes red over a race rather than
a proof. Three attempts, then exit `1`, so a genuinely broken push is still a failure.
`specs/ci/verify_gate.md` RULE-10 enforces the loop and the trailers together.

**`shell: bash` on every `run:` step.** PowerShell is the default on windows runners and reads a
leading `@` in a path as a splat, which silently mangles every scoped proof path.

**`PURLIN_PLUGIN_ROOT` and the pinned tag.** A consumer project's checkout contains no Purlin
`scripts/`, so every reference to Purlin tooling goes through `$PURLIN_PLUGIN_ROOT` and the clone
pins a tag. This repository's own workflows are the exception: they set `PURLIN_PLUGIN_ROOT: .` and
drop the install step, because this repository is the plugin.

**The `migrate.py --check` preflight.** A project whose `.purlin/plugins/` copies predate platform
scoping writes agnostic files from a platform runner, which satisfies nothing while looking green.
The preflight fails the job instead, naming `purlin:init --update`.

## Mode: declaration and enforcement are different things

`.purlin/config.json` carries a `remote_verification` field:

| Value | Meaning |
|-------|---------|
| `"required"` | The project declares that platform-declared proofs must be proved before a merge |
| `"optional"` | The loop is available and reported; findings never block |
| `"off"` | No remote verification; platform-declared proofs report `AWAITING RUNNER` and stay there |

**The field declares the mode. It does not enforce it.** `config.json` is a file in the repository
that the agent can edit, so it can never be the gate. `docs/regulated-environments.md` states the
principle: "Policy lives outside the repo ... not by config files the agent can edit." Enforcement
is **branch protection**: marking the `verify-gate` job a required check, and enabling auto-merge
only when it passes. That setting lives in the forge, not in the tree, which is exactly why it is
the enforcement.

So the two layers read:

- `remote_verification: "required"` in config tells `scripts/ci/verify_gate.py` to exit `1` on an
  unverified or awaiting-runner feature, and tells every Purlin surface to report the project as
  requiring remote verification.
- Branch protection is what makes that exit code matter. Without it, `"required"` is a statement of
  intent that a `git push` can ignore.

State the split whenever you report the mode. "Remote verification: required" alone invites the
reading that the field is the gate.

## What travels with a branch, and what does not

| Artifact | Committed? | Travels |
|----------|-----------|---------|
| Specs, agnostic proof files, receipts | yes | yes |
| Platform-scoped proof files (`<feature>.proofs-<tier>@<id>.json`) | yes, by the runner that wrote them | yes, with the `Purlin-Runner:` and `Purlin-Platform:` trailers that are their provenance |
| `.purlin/config.json` | yes | yes |
| `.purlin/config.local.json` | gitignored | no |
| `.purlin/runtime/test_run.json` | gitignored | no |
| `.purlin/cache/audit_cache.json` (Proof Integrity) | gitignored | **no** |
| `.purlin/cache/design_cache.json` (Proof Design) | gitignored | **no** |

A scoped proof file is the one artifact that is written somewhere else and travels to the
developer rather than from them. Its provenance is not in the file, which is why the trailers are
required and why `purlin:test` never amends or re-commits a file a runner committed.

Both quality gauges are **per-machine**. A CI run starts with no cache and reports both as
unmeasured, which is honest but not useful. Two recommendations:

- **Proof Design is deterministic and free.** It grades proof *descriptions*, needs no test code,
  and costs no LLM calls. CI can recompute it from scratch on every run and publish the result as a
  job artifact. That gives the project one authoritative Design figure rather than a different one
  per clone.
- **Proof Integrity costs LLM calls.** Recompute it in CI only where `audit_llm` is configured, and
  publish it as an artifact rather than committing it. Committing a cache would make a gauge that
  is advisory by design look like a tracked contract.

## Reporting

`purlin:test` distinguishes the two kinds of pass, because they were verified on different
machines and one of them is the thing the developer cannot check:

```
Test results:
  static_checks: PASSING (35/35 rules proved)
    ✓ @on(windows-2022) proved remotely 2 hours ago (github-actions/windows-2022)
  locking: PASSING (1/1 rules proved)
    ⚠ AWAITING RUNNER: 1 proof declared @on(macos-14) with no result — PROOF-2
```

"Proved remotely" is read from the commit trailer, never claimed from the proof entry: the entry
says a test passed, and only the commit says where.

## See also

- `references/formats/proofs_format.md`: scoped file names, the merge key that makes a commit-back safe
- `references/formats/spec_format.md`: the `@on(...)` grammar and the family ids
- `references/supported_frameworks.md`: the per-framework "Runner setup" cell the template needs
- `references/drift_criteria.md`: who owns the `platforms` config field
- `specs/ci/verify_gate.md`: the gate script and the runner-workflow rules
- `specs/mcp/sync_status.md` RULE-47/48/52: `AWAITING RUNNER`, per-file provenance, the `Platforms:` block
- `specs/skills/skill_test.md`: the skill rules this file backs
- `references/hard_gates.md`: why CI gating is project policy and not a framework gate
