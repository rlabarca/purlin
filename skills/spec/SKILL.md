---
name: spec
description: Turn a requirement in any form into rules and proofs
---

# purlin:spec

Turn what someone wants into rules and proofs. The person describes the software; you write
the spec. Nothing here needs a particular input format: a sentence in chat, a product brief, a
ticket, a block of pasted acceptance criteria and a folder of mocks all reach this skill.

**Paths.** Every `references/` and `scripts/` path below is inside the plugin and is reached
through `${CLAUDE_PLUGIN_ROOT}`. A project carries none of them.

For the syntax, read `references/formats/spec_format.md`. For what makes a rule worth writing,
read `references/spec_quality_guide.md`. Neither is restated here.

## Procedure

1. Call `sync_status` and read the state of the feature, if it already has one.
2. Read the input whole before writing anything.
3. Decide the feature name and the category folder: `specs/<category>/<name>.md`.
4. Write the metadata, then the rules, then one proof for every rule.
5. Allocate ids against `origin/main`, never against the working tree.
6. Commit the spec on its own, then offer the build.

## Intake

| What you are given | What you do |
|--------------------|-------------|
| One sentence | Split it into the claims it actually makes. "Users sign in with email and password, and five failures lock the account for fifteen minutes" is two rules, not one |
| A product brief or a ticket | Read it whole, then write only the claims a test could settle. Leave the background in `> Description:` |
| Pasted acceptance criteria | One rule per criterion, each tagged `[criterion: <id>]` so the author can find their own line again |
| Mocks in `designs/<feature>/` | Read the images. Write rules about what a person would see on the screen, tagged `[origin: design]` |
| An existing spec plus a change | Edit in place. Never renumber. See "Whose rule is it" below |

Ask at most one round of questions, and only where a claim cannot be tested as written. "Fast"
and "secure" always need a number; most other gaps can wait for the build.

One sentence in, three rules out:

> "Users sign in with email and password. After five failed attempts the account is locked for
> fifteen minutes."

becomes a rule for the success path, a rule for the wrong password, and a rule for the
lockout, because each of the three can fail on its own and each needs its own test. A single
rule covering all three would pass while two thirds of the behaviour was missing.

## Reconciling

When rules arrive from more than one direction, run this skill on the feature with no new
input. It reads the spec as it now stands, lists what changed since the last time it was
written, and reports three things: rules that lost their proof, proofs that name a rule id
that no longer exists, and rules whose text changed since an approval was bound to them. Fix
the first two here. The third is a person's decision, so name the rules and leave them for
`purlin:review`.

## The shape

```markdown
# Feature: login

> Description: Email and password sign-in with a lockout after repeated failures.
> Requires: security_baseline
> Scope: src/auth.py, src/session.py
> Stack: python/flask, bcrypt

## Rules

- RULE-1: Return 200 and a session cookie for a correct email and password [risk: high] [origin: pm] [criterion: US-12]
- RULE-2: Return 401 for a wrong password [risk: high] [origin: pm]
- RULE-3: Lock the account for 15 minutes after 5 consecutive failures [risk: medium] [origin: pm] [criterion: US-13]

## Proof

- PROOF-1 (RULE-1): POST /login with a known user; verify 200 and a Set-Cookie header @integration
- PROOF-2 (RULE-2): POST /login with the wrong password; verify 401 and no cookie @integration
- PROOF-3 (RULE-3): POST /login 5 times with a wrong password, then once with the right one; verify 423 @integration
```

`> Scope:` earns its place: a record carries the git tree hash of those files, which is what
lets Purlin tell a code change (the approval stands, re-verify pending) from a rule change
(the approval goes stale and a person must look). A spec with no `> Scope:` cannot make that
distinction.

## Rules

One claim per line, in the present tense, saying what the software does rather than how. Three
tags sit at the end of the line and are read off it, so the claim text stays clean:

| Tag | Values | Default | What it decides |
|-----|--------|---------|-----------------|
| `[risk: ...]` | `high`, `medium`, `low` | `low` | Under the `approved` gate, high and medium need a human approval and low is auto-approved by CI |
| `[origin: ...]` | `pm`, `design`, `qa`, `eng` | `eng` | Who owns the rule. `purlin:drift` routes a change by it |
| `[criterion: ...]` | any id | none | The upstream acceptance criterion the rule came from |

Under the `approved` gate, risk and origin are required and an untagged rule is reported.
Re-tagging a rule never stales an approval, so add a missing tag freely.

A rule about what the software must never do is an ordinary rule with a proof that asserts
absence. There is no separate syntax for it.

## Proofs

A proof says what a test asserts, not how the test is written. Name a route, an input, and the
observable that settles the claim. Every rule needs at least one proof. Several proofs may
name one rule, and one proof may name several rules when it drives a flow through all of them:
`- PROOF-7 (RULE-2, RULE-3, RULE-4): ...`.

Tag a proof that is not a plain unit test: `@integration` for a database, the network, the
filesystem or an external service; `@e2e` for a browser or the full stack; `@manual` for human
judgment. A `@manual` proof has no test: its evidence is an approval carrying a one-line note,
always written by a person and never auto-approved.

Add `@env(windows)`, `@env(macos)` or `@env(linux)` when the claim can only be proved on one
operating system. Those three are the whole vocabulary. A proof with no `@env` is satisfied by
a record from any system; a proof with one is Recorded only when a record from that system
passes it.

A design rule's proof is an end-to-end observable: a route, a state, visible text, presence.
Never a selector, never a pixel comparison. The test writes its capture under
`.purlin/runtime/attachments/<feature>/<PROOF-N>.png` and the review brief puts the mock
beside it.

## Ids

Rule and proof ids are allocated against `origin/main`, not against the working tree, so two
branches cut from the same commit do not both take RULE-9:

```bash
python3 -c "import sys; sys.path.insert(0, '${CLAUDE_PLUGIN_ROOT}/scripts/mcp'); \
from purlin import ids; print(ids.next_ids('.', 'specs/auth/login.md'))"
```

Ids are never reused. A retired rule leaves its number vacant and every other rule keeps the
number it had. Renumbering would silently repoint every test marker and every approval that
already names the old id, so do not do it by hand.

## Whose rule is it

A rule tagged `[origin: pm]`, `[origin: design]` or `[origin: qa]` belongs to that person. You
may add a rule beside it, tag yours `[origin: eng]`, and say in the pull request why the
neighbouring rule looks wrong. You may not rewrite theirs and you may not delete it. Leave the
proposal as a pull request comment naming the rule id and the replacement text, and let the
owner take it or leave it.

A rule tagged `[origin: eng]`, or carrying no origin at all, is yours to edit.

## Editing a rule during a build

`purlin:build` calls this skill when a rule turns out to be wrong while the code is being
written: the claim contradicts another rule, or it cannot be observed as stated. Fix the rule
text in place, keep the id, and say in the commit what changed and why. Changing rule text
stales any approval bound to it, which is the point: a person has to look again.

## After a merge conflict

```bash
purlin:spec <name> --resolve
```

Run this when `sync_status` warns that a spec carries a duplicate rule or proof id, which
happens when two branches allocated the same number before either fetched. `--resolve` keeps
both rules, renumbers the incoming one, and rewrites its test markers and its approval
filenames to match. When the conflict is two different texts on the same line, it shows both
versions, asks which survives, and says which approvals that answer stales.

Two branches that advanced the same anchor pin resolve to the newer sha.

## When you are done

Write the file, commit it with the `spec(<name>):` prefix from
`references/commit_conventions.md`, then end with exactly this and nothing after it:

```
Spec created: <name>. Build it now?
```

When you edited an existing spec rather than creating one, say what moved before the offer:
which rules were added, which text changed, and which approvals that stales. When the gate is
`approved` and a rule still has no risk or origin tag, name those rules first: the gate cannot
be met until they are tagged.
