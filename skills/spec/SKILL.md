---
name: spec
description: Turn a requirement in any form into rules and proofs
---

# purlin:spec

Turn what someone wants into rules and proofs. The person describes the software; you write
the spec. Nothing here needs a particular input format: a sentence in chat, a product
description, a ticket, a block of pasted acceptance criteria and a screenshot all reach this
skill.

**Paths.** Every `references/` and `scripts/` path below is inside the plugin and is reached
through `${CLAUDE_PLUGIN_ROOT}`. A project carries none of them.

For the syntax, read `references/formats/spec_format.md`. For what makes a rule worth writing,
read `references/spec_quality_guide.md`. Neither is restated here.

## Procedure

1. Call `sync_status` with `project_root` set to the project root, the top folder of the git
   checkout, and read the state of the feature, if it already has one.
2. Read the input whole before writing anything.
3. Decide the feature name and the category folder: `specs/<category>/<name>.md`.
4. Write the metadata, `> Scope:` included, then the rules, then one proof for every rule.
5. Allocate ids as "Ids" below says, never against the working tree alone.
6. Print each rule with its proofs under it and ask whether to change any. Change what the
   person asks and print them again.
7. Save the spec when the person is satisfied, commit it on its own, and name `purlin:build`
   as the next step. This skill never starts building.

## Intake

| What you are given | What you do |
|--------------------|-------------|
| One sentence | Split it into the claims it actually makes. "Users sign in with email and password, and five failures lock the account for fifteen minutes" is two rules, not one |
| A product description or a ticket | Read it whole, then write only the claims a test could settle. Leave the background in `> Description:` |
| Pasted acceptance criteria | One rule per criterion |
| A screenshot | Read the image. Write rules about what a person would see on the screen |
| An existing spec plus a change | Edit in place. Never renumber |

Ask at most one round of questions, and only where a claim no test could settle as written.
"Fast" and "secure" always need a number; most other gaps can wait for the build.

One sentence in, at least three rules out:

> "Users sign in with email and password. After five failed attempts the account is locked for
> fifteen minutes."

becomes at least a rule for the success path, a rule for the wrong password, and a rule for the
lockout, because each of the three can fail on its own and each needs its own test. A single
rule covering all three would pass while two thirds of the behaviour was missing.

## Reconciling

When rules arrive from more than one direction, run this skill on the feature with no new
input. It reads the spec as it now stands, lists what changed since the last time it was
written, and reports three things: rules that lost their proof, proofs that name a rule id
that does not exist, and rules whose text changed since a signature was bound to them. Fix
the first two here. The third is a person's decision, so name the rules and leave them for
`purlin:sign`.

## The shape

```markdown
# Feature: login

> Description: Email and password sign-in with a lockout after repeated failures.
> Requires: security_baseline
> Scope: src/auth.py, src/session.py
> Stack: python/flask, bcrypt

## Rules

- RULE-1: Return 200 and a session cookie for a correct email and password
- RULE-2: Return 401 for a wrong password
- RULE-3: Lock the account for 15 minutes after 5 consecutive failures

## Proof

- PROOF-1 (RULE-1): A known user signs in with the right password; the answer is 200 and it sets a session cookie
- PROOF-2 (RULE-2): A known user signs in with a wrong password; the answer is 401 and it sets no cookie
- PROOF-3 (RULE-3): After 5 wrong passwords in a row, the right password is refused with 423
```

Write `> Scope:` on every spec you create: the files the requirement touches, or the paths
`purlin:build` will create for it. The evidence carries a fingerprint of those files, so a
change to one of them reads `out of date` and selects the feature for the next `purlin:test`,
and a signature is tied to the code it governs. A spec that names no files still has its tests
run and its rules read, but every run includes it, and at the gate `signed` its rules cannot
be signed and no tag is written.

## Rules

One claim per line, in the present tense, saying what the software does rather than how.
Every rule is asked for what the project's gate asks, so a rule line carries the claim and
nothing else.

A rule about what the software must never do is an ordinary rule with a proof that asserts
absence. There is no separate syntax for it.

## Proofs

Draft every proof against `references/spec_quality_guide.md`, "Writing proofs", the one home
of what a good proof is: what is done, what is observed, the expected value, at least one
failure case, and no file path or function name, so a person who cannot read code can judge
it. QA reads every proof you draft. Write each proof as one case, one starting situation and
one action in at most 60 words, and a refusal or a boundary as a proof of its own, as the
guide's "One proof, one case" says. Write at least one proof for every rule: the gate `passed`
lets a rule go without one, and from `strong` up a rule without one reads `no proof`. Several
proofs may name one rule, and one proof may name several rules when it drives a flow through
all of them: `- PROOF-7 (RULE-2, RULE-3, RULE-4): ...`.

Tag a proof `@manual` when only human judgment settles it. A `@manual` proof has no test: a
person checks it and signs with `purlin:sign`, at any gate, writing what they saw when they
choose to.

Add `@env(windows)`, `@env(macos)` or `@env(linux)` when the claim can only be proved on one
operating system. Those three are the whole vocabulary. A proof with no `@env` is satisfied by
a run on any operating system; a proof with one has its passed cell met only when a run on
that system passes it.

## Ids

A new rule takes one more than the highest of `> Highest-Rule:` and every rule number in either
copy of the spec, the working copy and `origin/main`'s, read with `git show origin/main:<spec>`.
Write that number into `> Highest-Rule:`, adding the line after the spec's other `>` lines where
it is missing, so a deleted number is never used again. Proof ids are allocated the same way
against the proof numbers of both copies.

Ids are never reused. A deleted rule leaves its number vacant and every other rule keeps the
number it had. Renumbering would silently repoint every test marker and every signature that
already names the old id, so do not do it by hand.

## Editing a rule during a build

`purlin:build` calls this skill when a rule turns out to be wrong while the code is being
written: the claim contradicts another rule, or it cannot be observed as stated. Fix the rule
text in place, keep the id, and say in the commit what changed and why. Changing rule text
ends any signature bound to it, which is the point: a person has to look again.

## After a merge conflict

Two branches that allocated the same number before either fetched leave a spec with one id
twice. Keep both rules, give the incoming one the next free number, and move its test markers
and its signature filenames with it. When the conflict is two different texts on the same line,
show both versions, ask which survives, and say which signatures that answer ends.

Two branches that advanced the same anchor pin resolve to the newer sha.

## When you are done

Once the person is satisfied with the rules and proofs you printed, write the file, commit it
with the `spec(<name>):` prefix from `references/commit_conventions.md`, then end with exactly
this and nothing after it:

```
Spec saved: <name>. Next: purlin:build <name>
```

Never start the build yourself: the person runs `purlin:build` when they choose to.

When you edited an existing spec rather than creating one, say what moved before the offer:
which rules were added, which text changed, and which signatures that ends.
