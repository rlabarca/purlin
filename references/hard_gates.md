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
| `passed` | One person working alone | spec, passed | Every rule's passed cell is met, on every platform a counting run covered. A pass from any source counts |
| `strong` | A team: PM, designer, engineers, QA | + strong | Every rule whose bar is `strong` has a strong cell that is met: an audit wrote a record, the test strength at or above `min_strength`, no finding, nothing unsettled, no hold. A record from either source counts |
| `signed` | The same team under GxP | + signed | Every rule that needs a signature has one, and the signer list is set |

Each level derives defaults you can override:

| Derived | `passed` | `strong` | `signed` |
|---------|----------|----------|----------|
| `min_strength` | unused | 70 | 80 |
| The default bar | `passed` | `strong` | `strong` |
| `sign_at` | n/a | n/a | `strong`, asked by init |
| The breaks | off | on | on |
| Origin tags | optional | optional | required |

`purlin:init --gate <level>` changes the level later. Raising it adds what is missing and asks
before each write. Lowering it deletes nothing.

Under `passed` no strength is measured, no bar is read, no list exists and no signature is
asked for. Raising the gate to `strong` turns the breaks on, locally and in CI.

## The bar

Every rule carries a **bar**, `passed` or `strong`: the evidence it must have before it can
be signed. A rule tagged `[bar: passed]` or `[bar: strong]` carries what it names, and a rule
with no tag takes the project's gate, so `passed` at the gate `passed` and `strong` at
`strong` and at `signed`.

The bar decides three things and nothing else decides them:

- **What the rule must clear.** A rule has **cleared its bar** when its bar is `passed` and
  its passed cell is met, or its bar is `strong` and its strong cell is met.
- **Whether the AI audit runs on it.** It runs on every rule whose bar is `strong`, and on no
  other.
- **Whether it needs a signature.** At the gate `signed` a rule needs one when `sign_at` is
  `all`, or when its bar is `strong`. `purlin:init` asks which at the `signed` gate; the
  default is `strong`.

A rule is **signable** when it has cleared its bar, needs a signature and does not have a
counting one. That is what the board's `Signable` column counts and what the `Sign` list
holds.

## Which evidence counts

**At `passed` the evidence is the test results.** `purlin:test` runs the tagged tests, writes
`.purlin/tests/<feature>.json` and `.purlin/tests.md`, and commits both itself under the
person's own identity. A teammate reads them on the git host without running anything.

**At `strong` and above the evidence is the record, and an audit writes it.** `purlin:audit`
runs the tests and the breaks, writes one record per feature under
`.purlin/records/local/<feature>/` with its briefs beside it, and commits both under your own
identity. It never pushes. The CI job does the same under `.purlin/records/ci/`.

**The folder is the source.** A record's own `source` field must say the same word as the
folder it sits in, and a file where the two disagree is ignored with one warning naming it.
What keeps the ci folder honest is the git host's file-path rule, which only the build identity
may write.

| Source | The folder | Counts under |
|--------|------------|--------------|
| `ci` | `.purlin/records/ci/<feature>/`, written by the CI identity through the git host's API | `passed`, `strong`, `signed` |
| `local` | `.purlin/records/local/<feature>/`, written by `purlin:audit` on anyone's machine, and the test results `purlin:test` commits | `passed`, `strong` |

**Only `signed` requires CI, and there it requires it for the tests and the audit both.** The
run on the protected branch after the merge is what a signature attaches to; a local run there
is a preview, and `purlin:audit` says so on its last line.

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
2. Restrict file paths on `.purlin/records/ci/**` and `.purlin/briefs/ci/**`, with the Actions
   app as the only bypass actor, so a person cannot push a record or a brief as CI's. The
   `local/` folders beside them are anyone's.
3. Block force pushes and restrict deletions, with no bypass at all.

Under `passed`, only the third is suggested.

On Azure DevOps: the build service alone holds Contribute on those two paths through branch
security, plus no force push and no delete. Same effect, through that host's own mechanism.

## The signer list

`signers` in `.purlin/config.json` holds the emails of the people who may sign. It changes by
pull request like any other file, so git history records who could sign and when.

A signature counts under `signed` when all five hold. Under `strong`, where what a signature
clears is a question the machine could not settle, a committed signature from anyone counts.

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

`sign_at` says which rules need one, and `purlin:init --gate signed` asks for it. `strong`,
the default, asks for a signature on every rule whose bar is `strong`; `all` asks for one on
every rule. A rule that needs none carries `required` false on its signed cell and meets the
level whichever way that cell reads.

## CI writes no signature file

CI runs the tests and the breaks, measures the strength, runs the free checks, runs the AI
audit on every rule whose bar is `strong`, and writes the record and the briefs. It signs
nothing. A signature directory holds only files a person wrote.

What CI cannot settle it says out loud. A `@manual` proof makes the strong cell read `manual
test`, and an AI audit that could not tell whether the test observes what the proof names
makes it read `unsettled`. A rule whose bar is `strong` that no audit has reached reads `not
audited`, and what moves that one is `purlin:audit`, not a person. A signature file for the
current hashes clears the first two: from anyone under `strong`, from a counting signer under
`signed`. The signer writes the one line with `--note`.

## Holds

A **hold** is how a person who read the brief says the test does not prove the proof as written:

```
purlin:sign <feature> RULE-N --hold "<the missing case>"
```

That commits one file bound to the rule's hashes. While the hold is current both the strong
cell and the signed cell read `held`, whatever the bar, so the rule does not meet the gate at
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

## Platforms

A record and a set of test results each name the operating system they ran on. The passed cell
lists one **platform** per operating system a counting run named, each with its own word, its
source and when it ran, and the cell's own word rolls them up. Where the platforms disagree the
cell reads `partial`: a rule whose tests pass on Linux and fail on Windows is neither passed nor
failed, `partial` is not met, and it blocks the gate exactly as a failure does. A rule tagged for
one platform that has not run there still reads `not run`. Test strength is platform independent,
because the breaks are measured once per feature.

## The pre-push hook is optional and gates nothing

A project may install a pre-push hook. It runs `purlin:test`: the tagged tests only, no
breaks and no audit, so a push is never held up by an audit. It prints what it found, and it
writes and commits the test results as any `purlin:test` run does. It lets the push through in
every case but one: with `pre_push` set to `on` in `.purlin/config.json` and a tagged test
failing, it blocks and names the failure. At the default, `off`, a failing test is printed and
the push goes ahead. `git push --no-verify` skips the hook. What a change must clear before it
merges is the gate, and the gate is the git host's; this is a convenience in front of it, not a
control.

The hook refuses one push outright, which is the one thing in it that is not a convenience: a
push from an agent session. With `CLAUDE_CODE_SESSION_ID` in the environment and
`PURLIN_REMOTE_RUN` unset it prints `purlin: an agent does not push. A person runs git push.`
and exits 1, before it runs anything. `--no-verify` is a person's override, not an agent's.

**Nothing in a Claude Code hook gates anything.** The plugin registers no `PreToolUse`, no
`PermissionRequest` and no `UserPromptSubmit` handler, which are the events through which a hook
could stop or steer a turn. Every NEVER in `agents/purlin.md` is an instruction to the agent,
not a mechanism that stops it. What survives an agent ignoring an instruction runs outside the
agent's turn: the CI job, and the branch rule that makes it required.
