# The gate

The gate is the one project setting: what CI must see before a change can merge. It is defined
here and nowhere else. A skill, a doc or a script that needs it links to this page rather than
restating it, because three copies of this answer drifted into three different answers once
already.

**A gate is three things**, and all three must exist for it to mean anything:

1. A CI job running `purlin:verify --ci` on every push and pull request.
2. A branch rule on the default branch that blocks a merge unless that job passes.
3. The setting saying what "passes" means.

Setting one without the other two is a preference, not a gate.

## The three levels

`gate` in `.purlin/config.json` is one of three values. `purlin:init` asks the one question
that sets it: what must be true before CI lets a change merge?

| Level | Who it fits | What CI requires before merge |
|-------|-------------|-------------------------------|
| `tested` | One developer | Every rule has a passing tagged test |
| `recorded` | A team: PM, designer, engineers, QA | Every rule has a record written by CI at this commit, with the test strength at or above `min_strength` |
| `approved` | The same team under GxP | Everything `recorded` requires, plus a current approval on every high-risk and medium-risk rule, committed with a signed commit by someone on the approver list. Low risk is auto-approved by CI |

Each level derives defaults you can override: `min_strength` 50 / 70 / 80, AI review at never /
high / medium, and risk and origin tags optional / optional / required.

`purlin:init --gate <level>` changes the level later. Raising it adds what is missing and asks
before each write. Lowering it deletes nothing.

## Which records count

The label on a record comes from the last commit that touched it, never from anything inside the
file. `tested` counts a record committed by CI or by a person. `recorded` and `approved` count a
record committed by CI alone, so a developer cannot write the evidence their own change is
measured by.

| Label | How it got there |
|-------|------------------|
| ci | Created through the git host's API by the CI identity |
| developer | A person committed it |
| local | Not committed |

A pull request from a fork gets no record commit. Verify still runs and the comment still posts;
the job says in one line that nothing was written.

## Branch rules the git host enforces

`purlin:init` prints these; you apply them once. On GitHub, three rulesets, so that the bypass
stays narrow:

1. Require a pull request, and require the status checks, with the Actions app as the only
   bypass actor.
2. Restrict file paths on `.purlin/records/**` and `specs/**/*.approvals/*.ci.json`, with the
   Actions app as the only bypass actor, so a person cannot push a record or a CI approval.
3. Block force pushes and restrict deletions, with no bypass at all.

Under `tested`, only the third is suggested.

On Azure DevOps: the build service alone holds Contribute on those paths through branch
security, plus no force push and no delete. Same effect, through that host's own mechanism.

## The approver list

`approvers` in `.purlin/config.json` holds the emails of the people who may approve. It changes
by pull request like any other file, so git history records who could approve and when.

An approval counts when all four hold:

- The commit that added the approval file is signed and the signature verifies.
- The author's email is on the list as of that commit.
- That author is not the author of the commit that last touched the test.
- The approval's bound hashes still match the current rule text, proof text and test body.

`purlin:init --gate approved` asks for the emails and prints the one-time signing setup for each
person. Under `approved` with no list, `sync_status` and `scripts/ci/verify_gate.py --check`
both print `→ approver list missing: run purlin:init --gate approved` and the check exits 1.
This works with a single QA person, works the same on both git hosts, and needs nothing the git
host has to be configured for.

## Auto-approval

CI approves a rule on its own only when every one of these holds: the risk is low, the test
passes, and the test strength is at or above `min_strength` (or no break engine is installed and
the free checks pass). High and medium risk are never auto-approved. A proof marked `@manual`
is never auto-approved either: its evidence is an approval file with a one-line note, written by
a person.

## What is not a gate

- Writing code without invoking a skill.
- Writing a test with no proof marker. It runs; `sync_status` does not count it.
- Committing without verifying.
- A rule flagged `re-verify pending`. Only the code changed, the approval stands, and CI clears
  it on the next run.
- A proof tagged `@env` for an operating system this host is not. It is listed as
  `needs <os>`, and CI's matrix proves it.

## The pre-push hook is optional and gates nothing

A project may install a pre-push hook. It runs `purlin:test` only: the fast path, no breaks and
no record, so a push is never held up by a full verify. It prints what it found and lets the
push through. `git push --no-verify` skips it. It is a convenience, not a control.

**Nothing in a Claude Code hook gates anything.** The plugin registers no `PreToolUse`, no
`PermissionRequest` and no `UserPromptSubmit` handler, which are the events through which a hook
could stop or steer a turn. Every NEVER in `agents/purlin.md` is an instruction to the agent,
not a mechanism that stops it. What survives an agent ignoring an instruction runs outside the
agent's turn: the CI job, and the branch rule that makes it required.
