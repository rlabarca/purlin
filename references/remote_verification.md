# Remote Verification

Some proofs cannot execute on a developer's machine. A `@windows` proof needs a Windows host; no
amount of simulation on macOS proves it. Purlin calls these tiers **runner-gated**, and a proof
declared at one reports `AWAITING RUNNER` until a host for that tier proves it.

Remote verification is how that proof gets run: `purlin:test` pushes the branch, a CI workflow
runs the runner-gated tiers on a real host, and the workflow commits the proof files it wrote back
to the branch. `purlin:test` pulls them and reports them as proved remotely.

This file is the authoritative reference for that loop. `skills/test/SKILL.md` implements it;
`specs/ci/verify_gate.md` governs the CI side.

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
purlin:test  ->  push branch  ->  CI runs runner-gated tiers  ->  proofs come back
   red  ->  report + "-> Run: purlin:build <feature>"
purlin:build  ->  fixes, commits
purlin:test  ->  ...  ->  green
purlin:verify  ->  reads the returned proofs, issues receipts   (never edits a file)
```

**The loop is bounded at 3 rounds**, matching `skills/audit/SKILL.md` and
`skills/verify/SKILL.md`. A fourth round means the remote failure is not converging; report what
failed and stop rather than spending another CI run on it.

## Setting it up

Setup is offered **on discovery, not at init**. `purlin:init` does not configure a remote: a
project with no runner-gated proofs needs no runner, and asking about one during setup is a
question with no answer yet. When `purlin:test` finds proofs declared at a runner-gated tier and
no workflow configured for that tier, it offers to scaffold one from the template below.

### Workflow template

Substitute `<tier>` (e.g. `windows`), `<runs-on>` (e.g. `windows-latest`), the test command, and
the proof paths.

```yaml
name: purlin-<tier>-proofs

on:
  push:
    # Loop guard, half one: the runner's own proof commit must not retrigger it.
    paths-ignore:
      - '**/*.proofs-<tier>.json'
  workflow_dispatch:

permissions:
  contents: write

jobs:
  <tier>-proofs:
    runs-on: <runs-on>
    steps:
      - uses: actions/checkout@v4
        with:
          persist-credentials: true

      - uses: actions/setup-python@v5
        with:
          python-version: '3.11'

      - name: Install the test runner
        run: pip install pytest

      - name: Run the <tier>-tier proofs
        run: python -m pytest <test files> -v

      - name: Commit the proof file back to the branch
        shell: bash
        run: |
          git config user.name "github-actions[bot]"
          git config user.email "github-actions[bot]@users.noreply.github.com"
          git add '<proof file paths>'
          if git diff --cached --quiet; then
            echo "No proof-file changes to commit."
          else
            # Loop guard, half two, and the runner's identity for sync_status.
            git commit -m "test(<feature>): <tier> proofs from <runs-on> [skip ci]" \
                       -m "Purlin-Runner: github-actions/<runs-on>"
            git push origin HEAD:${GITHUB_REF_NAME}
          fi
```

Three details in that template are load-bearing.

**`Purlin-Runner:` trailer (required).** Proof entries carry no timestamp and no runner field, on
purpose: that absence is what makes `git diff --cached --quiet` an accurate idempotency check, so
a re-run that proves the same things commits nothing. Provenance is read back out of git instead.
`sync_status` runs `git log -1` on the tier file and takes the runner from this trailer
(`sync_status` RULE-48). Without it the report reads `runner not recorded`, which is a gap, not a
valid state. `specs/ci/verify_gate.md` RULE-7 enforces the trailer.

**The loop guard, both halves.** `paths-ignore` stops a `push` trigger; `[skip ci]` stops the
trigger paths `paths-ignore` does not cover. Either alone eventually loops.
`specs/ci/verify_gate.md` RULE-8 enforces both.

**`git diff --cached --quiet`.** Commit only when something changed. A workflow that commits
unconditionally produces one empty commit per push forever.

## Mode: declaration and enforcement are different things

`.purlin/config.json` carries a `remote_verification` field:

| Value | Meaning |
|-------|---------|
| `"required"` | The project declares that runner-gated proofs must be proved before a merge |
| `"optional"` | The loop is available and reported; findings never block |
| `"off"` | No remote verification; runner-gated proofs report `AWAITING RUNNER` and stay there |

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
| Specs, proof files, receipts | yes | yes |
| `.purlin/config.json` | yes | yes |
| `.purlin/config.local.json` | gitignored | no |
| `.purlin/cache/audit_cache.json` (Proof Integrity) | gitignored | **no** |
| `.purlin/cache/design_cache.json` (Proof Design) | gitignored | **no** |

Both quality gauges are therefore **per-machine**. A CI run starts with no cache and reports both
as unmeasured, which is honest but not useful. Two recommendations:

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
    @windows: proved remotely 2 hours ago (github-actions/windows-latest)
  locking: PASSING (1/1 rules proved)
    ⚠ AWAITING RUNNER: 1 proof declared @windows with no result — PROOF-2
```

"Proved remotely" is read from the commit trailer, never claimed from the proof entry: the entry
says a test passed, and only the commit says where.

## See also

- `references/formats/proofs_format.md`: the merge key that makes a commit-back safe
- `specs/ci/verify_gate.md`: the gate script and the runner-workflow rules
- `specs/mcp/sync_status.md` RULE-47/48: `AWAITING RUNNER` and runner provenance
- `specs/skills/skill_test.md`: the skill rules this file backs
- `references/hard_gates.md`: why CI gating is project policy and not a framework gate
