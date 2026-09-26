# The gate

The gate is the one project setting: what CI must see before a change can merge. It is defined
here and nowhere else. A skill, a doc or a script that needs it links to this page rather than
restating it, because three copies of this answer drifted into three different answers once
already.

**A gate is three things**, and all three must exist for it to mean anything:

1. A CI job running `purlin:audit --ci` where the evidence is decided: on a pull request, on
   the protected branch and on a run branch. Every run ends with `gate_check.py --check` and
   fails when the gate is not met.
2. A branch rule on the protected branch that blocks a merge unless that job passes.
3. The setting saying what "passes" means.

Setting one without the other two is a preference, not a gate.

## The three levels

A rule answers up to three questions, one per level, and each answer is a **cell**. `gate` in
`.purlin/config.json` says how many of the three the project asks. A rule **meets the gate**
when every cell up to the gate's level is met. `purlin:init` asks the one question that sets it:
what must be true before CI lets a change merge?

| Gate | Who it fits | Cells that exist | What CI requires before merge |
|------|-------------|------------------|-------------------------------|
| `passed` | One developer | spec, passed | Every rule's passed cell is met. A pass from any source counts |
| `strong` | A team: PM, designer, engineers, QA | + strong | Every rule's strong cell is met: a CI pass, the test strength at or above `min_strength`, no finding, no hold. Only a record CI wrote counts |
| `signed` | The same team under GxP | + signed | Every rule's signed cell is met, and the signer list is set |

Each level derives defaults you can override:

| Derived | `passed` | `strong` | `signed` |
|---------|----------|----------|----------|
| `min_strength` | unused | 70 | 80 |
| `ai_review_at` | never | high | medium |
| `sign_at` | n/a | n/a | medium |
| The breaks | off | on | on |
| Risk and origin tags | optional | optional | required |

`purlin:init --gate <level>` changes the level later. Raising it adds what is missing and asks
before each write. Lowering it deletes nothing.

Under `passed` no strength is measured, no risk is read, no review list exists and no signature
is asked for. Raising the gate to `strong` turns the breaks on, locally and in CI.

## Which records count

The source of a record comes from the last commit that touched it, never from anything inside
the file. `passed` counts a record CI wrote, a record a person committed, and the last run in
this checkout. `strong` and `signed` count a record CI wrote alone, so a developer cannot write
the evidence their own change is measured by. A local `purlin:audit` under those two gates is a
preview, and it says so.

| Source | How it got there |
|--------|------------------|
| `ci` | Created through the git host's API by the CI identity |
| `developer` | A person committed it |
| `local` | Not committed |

A record describes the checkout while its commit is HEAD or its scope tree still hashes the
same. A CI pass that is no longer current makes the passed cell read `code changed`, and CI
clears it on the next run.

## Where CI runs and what it writes

The workflow `purlin:init` writes triggers on three things and nothing else: a pull request, a
push to the protected branch, and a push to a `run/*` branch, which is the branch
`purlin:audit --remote` creates and deletes around one run. A push to any other branch starts
nothing.

What a run writes depends on where it runs. A pull request run does the tests, posts the
comment and uploads the dashboard, and commits nothing: a record on a branch nobody merges from
is evidence of a branch that will not exist. It prints `Pull request run: the records stay on
the runner; the run on <protected> writes them.` A run on the protected branch, or on a run
branch, commits its records and briefs there.

Every run ends with `scripts/ci/gate_check.py --check`, and the job fails when the gate is not
met. That is what makes the required check mean the gate held.

**CI publishes its own evidence; a person pushes theirs.** A push is a person's act: a
developer's record commit prints `Run: git push` and stops, no skill opens a pull request, and
the pre-push hook refuses a push made from an agent session unless `PURLIN_REMOTE_RUN=1` marks
it as the remote run. `purlin:audit --remote` is the one push Purlin makes, and it pushes a run
branch rather than the branch you are on.

A pull request from a fork gets no record commit. The audit still runs and the comment still
posts; the job says in one line that nothing was written.

## Branch rules the git host enforces

`purlin:init` prints these; you apply them once. On GitHub, three rulesets, so that the bypass
stays narrow:

1. Require a pull request, and require the `purlin` workflow's checks, with the Actions app as
   the only bypass actor. Every run ends with the gate check, so a green check means the gate
   held.
2. Restrict file paths on `.purlin/records/**` and `.purlin/briefs/**`, with the Actions app as
   the only bypass actor, so a person cannot push a record or a brief.
3. Block force pushes and restrict deletions, with no bypass at all.

Under `passed`, only the third is suggested.

On Azure DevOps: the build service alone holds Contribute on those two paths through branch
security, plus no force push and no delete. Same effect, through that host's own mechanism.

## The signer list

`signers` in `.purlin/config.json` holds the emails of the people who may sign. It changes by
pull request like any other file, so git history records who could sign and when.

A signature counts when all five hold:

- The commit that added the signature file is signed and the signature verifies.
- The author's email is on `signers` as of that commit.
- That author is not the author of the commit that last touched the test file.
- The signature's bound hashes still match the current rule text, proof text and test body.
- Under `signed`, the commit is on the protected branch.

`purlin:init --gate signed` asks for the emails and prints the one-time signing setup for each
person. Under `signed` with no list, `sync_status` and `scripts/ci/gate_check.py --check` both
print `→ signer list missing: run purlin:init --gate signed` and the check exits 1. This works
with a single QA person, works the same on both git hosts, and needs nothing the git host has to
be configured for.

`sign_at` says which rules need one. It defaults to `medium`, so a low-risk rule meets the
`signed` gate at strong and its signed cell reads `not required`. `sign_at: low` asks for a
signature on every rule.

## CI writes no signature file

CI runs the tests and the breaks, measures the strength, runs the free checks, runs the model
review where risk asks, and writes the record and the briefs. It signs nothing. A signature
directory holds only files a person wrote.

What CI cannot settle it says out loud. A `@manual` proof, and a model review that could not
tell whether the test observes what the proof names, both make the strong cell read `needs a
person`. A signature file for the current hashes clears it: from anyone under `strong`, from a
counting signer under `signed`. The signer writes the one line with `--note`.

## Holds

A **hold** is how a person who read the brief says the test does not prove the proof as written:

```
purlin:sign <feature> RULE-N --hold "<the missing case>"
```

That commits one file bound to the rule's hashes. While the hold is current both the strong
cell and the signed cell read `held`, whatever the risk, so the rule does not meet the gate at
`strong` or `signed`. A signature by a person for the current hashes outranks
the hold. Changing the rule, the proof or the test ends the hold, as it stales a signature.

## What is not a gate

- Writing code without invoking a skill.
- Writing a test with no proof marker. It runs; `sync_status` does not count it.
- Committing without running an audit.
- A rule whose passed cell reads `code changed`. Only the code changed; CI clears it on the next
  run.
- A proof tagged `@env` for an operating system this host is not. It is listed as
  `<os>: no record yet`, and CI's matrix proves it.

## The pre-push hook is optional and gates nothing

A project may install a pre-push hook. It runs `purlin:test` only: the fast path, no breaks and
no record, so a push is never held up by a full audit. It prints what it found and lets the push
through. `git push --no-verify` skips it. It is a convenience, not a control.

The hook refuses one push outright, which is the one thing in it that is not a convenience: a
push from an agent session. With `CLAUDE_CODE_SESSION_ID` in the environment and
`PURLIN_REMOTE_RUN` unset it prints `purlin: an agent does not push. A person runs git push.`
and exits 1, before it runs anything. `--no-verify` is a person's override, not an agent's.

**Nothing in a Claude Code hook gates anything.** The plugin registers no `PreToolUse`, no
`PermissionRequest` and no `UserPromptSubmit` handler, which are the events through which a hook
could stop or steer a turn. Every NEVER in `agents/purlin.md` is an instruction to the agent,
not a mechanism that stops it. What survives an agent ignoring an instruction runs outside the
agent's turn: the CI job, and the branch rule that makes it required.
