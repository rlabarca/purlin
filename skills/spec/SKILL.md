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
4. Write the metadata, `> Scope:` included, then the rules, then one proof for every rule.
5. Allocate ids against `origin/main`, never against the working tree.
6. Commit the spec on its own, then offer the build.

## Intake

| What you are given | What you do |
|--------------------|-------------|
| One sentence | Split it into the claims it actually makes. "Users sign in with email and password, and five failures lock the account for fifteen minutes" is two rules, not one |
| A product brief or a ticket | Read it whole, then write only the claims a test could settle. Leave the background in `> Description:` |
| Pasted acceptance criteria | One rule per criterion |
| Screens or mocks | Read the images. Write rules about what a person would see on the screen |
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
that no longer exists, and rules whose text changed since a signature was bound to them. Fix
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

One claim per line, in the present tense, saying what the software does rather than how. One
tag sits at the end of the line and is read off it, so the claim text stays clean:

| Tag | Values | Default | What it decides |
|-----|--------|---------|-----------------|
| `[level: ...]` | `passed`, `strong`, `signed` | the project's gate | What the rule must have to meet the gate, in the gate's own words: tests; tests and the audit; tests, the audit and a signature. The gate is the ceiling, so a mark above it is read as the gate |

A rule with no tag takes the project's gate, so leave it off unless the rule needs less than
the rest.

**Write no level tag at the gate `passed`.** Nothing reads one there, and a tag a reader
cannot act on is a tag they have to ask about. At `strong` and above leave every rule
unmarked and mark the exceptions: a rule whose evidence is its tests alone takes
`[level: passed]`, and under `signed` a rule that needs the audit and no signature takes
`[level: strong]`. A signature logs the rule's level and does not lock it, so re-marking a
rule stales no signature.

A rule about what the software must never do is an ordinary rule with a proof that asserts
absence. There is no separate syntax for it.

## Proofs

Write every proof to `references/spec_quality_guide.md`, "Writing proofs", the one home of
what a good proof is. Write at least one proof for every rule. Several proofs may name one
rule, and one proof may name several rules when it drives a flow through all of them:
`- PROOF-7 (RULE-2, RULE-3, RULE-4): ...`.

Tag a proof `@manual` when only human judgment settles it. A `@manual` proof has no test: its rule reads `manual test` until a signature
carrying a one-line note settles it, and that note is always written by a person.

Add `@env(windows)`, `@env(macos)` or `@env(linux)` when the claim can only be proved on one
operating system. Those three are the whole vocabulary. A proof with no `@env` is satisfied by
a record from any system; a proof with one has its passed cell met only when a record from
that system passes it.

## Ids

Rule and proof ids are allocated against `origin/main`, not against the working tree, so two
branches cut from the same commit do not both take RULE-9. The next id is one past the highest
in either copy of the spec:

```bash
git show origin/main:specs/auth/login.md | grep -o 'RULE-[0-9]*' | sort -t- -k2 -n | tail -1
```

Ids are never reused. A retired rule leaves its number vacant and every other rule keeps the
number it had. Renumbering would silently repoint every test marker and every signature that
already names the old id, so do not do it by hand.

## Editing a rule during a build

`purlin:build` calls this skill when a rule turns out to be wrong while the code is being
written: the claim contradicts another rule, or it cannot be observed as stated. Fix the rule
text in place, keep the id, and say in the commit what changed and why. Changing rule text
stales any signature bound to it, which is the point: a person has to look again.

## After a merge conflict

Two branches that allocated the same number before either fetched leave a spec with one id
twice. Keep both rules, give the incoming one the next free number, and move its test markers
and its signature filenames with it. When the conflict is two different texts on the same line,
show both versions, ask which survives, and say which signatures that answer stales.

Two branches that advanced the same anchor pin resolve to the newer sha.

## When you are done

Write the file, commit it with the `spec(<name>):` prefix from
`references/commit_conventions.md`, then end with exactly this and nothing after it:

```
Spec created: <name>. Build it now?
```

When you edited an existing spec rather than creating one, say what moved before the offer:
which rules were added, which text changed, and which signatures that stales.
