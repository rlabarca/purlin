# The gate

The gate is the one project setting: what CI must see before a change can merge. It is defined
here and nowhere else. A skill, a doc or a script that needs it links to this page rather than
restating it, because three copies of this answer drifted into three different answers once
already.

**A gate is three things**, and all three must exist for it to mean anything:

1. A CI job where the evidence is decided: on a pull request, on the protected branch and on
   a run branch. It runs the tagged tests, then at `strong` and above the audit and the
   record. Every run ends with `gate_check.py --check` and fails when the gate is not met.
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
| `passed` | One person working alone | spec, passed | Every rule's passed cell is met. A pass from any source counts |
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

## Which evidence counts

**At `passed` the evidence is the test results.** `purlin:test` runs the tagged tests, writes
`.purlin/tests/<feature>.json` and `.purlin/tests.md`, and commits both itself under the
person's own identity. A teammate reads them on the git host without running anything.

**At `strong` and above the evidence is the record, and the record is CI's.** Nothing on a
person's machine writes one: `purlin:audit` measures how good the tests are and writes nothing
at all, saying so on its last line. The source of a record comes from the last commit that
touched it, never from anything inside the file.

| Source | How it got there | Counts under |
|--------|------------------|--------------|
| `ci` | Created through the git host's API by the CI identity | `passed`, `strong`, `signed` |
| `local` | Anything else: not committed, or committed by somebody other than the git host | `passed` only |

A record describes the checkout while its commit is HEAD or its scope tree still hashes the
same. A CI pass that is no longer current makes the passed cell read `code changed`, and CI
clears it on the next run.

## Where CI runs and what it writes

The workflow `purlin:init` writes triggers on three things and nothing else: a pull request, a
push to the protected branch, and a push to a `run/*` branch, which is the branch
`purlin:test --remote` creates and deletes around one run. A push to any other branch starts
nothing.

What a run writes depends on the gate and on where it runs. At `passed` it runs the tagged
tests, posts the comment, uploads the dashboard and writes no record. At `strong` and above it
audits what it ran and writes one record per feature plus the briefs. A pull request run
commits nothing either way: a record on a branch nobody merges from is evidence of a branch
that will not exist. It prints `Pull request run: the records stay on the runner; the run on
<protected> writes them.` A run on the protected branch, or on a run branch, commits its
records and briefs there.

Every run ends with `scripts/ci/gate_check.py --check`, and the job fails when the gate is not
met. That is what makes the required check mean the gate held.

**CI publishes its own evidence; a person pushes theirs.** A push is a person's act:
`purlin:test` commits the results and stops, no skill opens a pull request, and the pre-push
hook refuses a push made from an agent session unless `PURLIN_REMOTE_RUN=1` marks it as the
remote run. `purlin:test --remote` is the one push Purlin makes, and it pushes a run branch
rather than the branch you are on.

A pull request from a fork gets no record commit. The run still happens and the comment still
posts; the job says in one line that nothing was written.

## The remote runner

`purlin:init` explains a remote runner in three reasons and no others: your tests need another
operating system; proof from a clean machine that ran exactly the pushed code; no merge while
red. Teammates see your results without one, from the test results `purlin:test` commits. At
`passed` init asks `Run the tests on a remote runner too? [y/n]` and writes the workflow on a
yes; at `strong` and above it always writes it, and the three reasons are the explanation.

Before any workflow is written init checks the prerequisites: a remote exists, its URL names
GitHub or Azure DevOps, and the protected branch is on that remote. The first that fails is
named in one line with what to do, and no workflow is written. The host CLI, `gh` or `az`, is
reported as present or absent either way.

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

What CI cannot settle it says out loud. A `@manual` proof makes the strong cell read `manual
test`, and a model review that could not tell whether the test observes what the proof names
makes it read `manual audit`. A signature file for the current hashes clears either one: from
anyone under `strong`, from a counting signer under `signed`. The signer writes the one line
with `--note`.

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

A project may install a pre-push hook. It runs the tagged tests only: the fast path, no breaks
and no audit, so a push is never held up by one. It prints what it found and lets the push
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
