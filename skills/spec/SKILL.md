---
name: spec
description: "Write or change a spec: turn a requirement into rules and proofs, or add, sharpen, reword or remove a rule, a case or a proof of an existing spec. Use it for any change to a file under specs/, instead of editing the file by hand"
---

# purlin:spec

Turn what someone wants into rules and proofs. The person describes the software; you write
the spec. Nothing here needs a particular input format: a sentence in chat, a product
description, a ticket, a block of pasted acceptance criteria and a screenshot all reach this
skill.

**Paths.** Every `references/` and `scripts/` path below is inside the plugin and is reached
through `${CLAUDE_PLUGIN_ROOT}`. A project carries none of them.

A line marked **Stop and ask** is a question for the person: print it, end your turn, and act
only on their answer. Never answer it yourself.

For the syntax, read `references/formats/spec_format.md`. For what makes a rule worth writing,
read `references/spec_quality_guide.md`. Neither is restated here.

## Procedure

1. Get the status from the tool `mcp__plugin_purlin_purlin__sync_status`, passing `project_root`:
   the top folder of the git checkout you are working in. Where the session lists it as a
   deferred tool, load it with ToolSearch first. Where the session does not have it, run the
   script, which prints the same status:

   ```bash
   sh "${CLAUDE_PLUGIN_ROOT}/scripts/purlin_python.sh" "${CLAUDE_PLUGIN_ROOT}/scripts/run/purlin_status.py" --project-root .
   ```

   Never read `.purlin/report-data.js` or `purlin-report.html` as the status: they hold what the
   last command saw.

   Read the state of the feature, if it already has one.
2. Read the input whole before writing anything.
3. Decide the feature name and the category folder: `specs/<category>/<name>.md`, never
   `specs/<name>.md`. `references/formats/spec_format.md` says what a name may hold.
4. Write the metadata, `> Scope:` included, then the rules, then one proof for every rule.
5. Allocate ids as "Ids" below says, never against the working tree alone.
6. Print each rule with its proofs under it. **Stop and ask** whether to change any. Change
   what the person asks and print them again.
7. Save the spec when the person is satisfied, then check it:

   ```bash
   sh "${CLAUDE_PLUGIN_ROOT}/scripts/purlin_python.sh" "${CLAUDE_PLUGIN_ROOT}/scripts/run/purlin_status.py" --project-root . --spec <name>
   ```

   It prints each mistake Purlin sees in the spec first and exits 1, or, with none, opens on the
   spec's path and its rule count and exits 0. Fix every mistake and run it again. Only then commit the spec on its own and
   name `purlin:build` as the next step. This skill never starts building.

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
that does not exist, and numbers written twice or test comments whose proof's wording changed
after the test last changed. Fix the first two here, a number written twice as "Renumbering"
below says, and a reworded proof's test with `purlin:build`.

## The shape

```markdown
# Feature: login

> Description: Email and password sign-in with a lockout after repeated failures.
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
change to one of them reads `out of date` and selects the feature for the next `purlin:test`.
A spec written before its code is the normal order: until the files exist the status prints one
line of information naming them, with `purlin:build <name>` first.

A spec that carries `> Requires:` or `> Global:`, or an anchor that carries `> Scope:`, is warned
of: take the line out. Where a rule of an anchor holds only for some features, write it in each
of their specs instead.

## Rules

One claim per line, in the present tense, saying what the software does rather than how. A
rule line carries the claim and nothing else.

A rule about what the software must never do is an ordinary rule with a proof that asserts
absence. There is no separate syntax for it.

## Proofs

Draft every proof against `references/spec_quality_guide.md`, "Writing proofs", the one home
of what a good proof is: what is done, what is observed, the expected value, at least one
failure case, and no file path or function name, so a person who cannot read code can judge
it. QA reads every proof you draft. Write each proof as one case, one starting situation and
one action in at most 60 words, and a refusal or a boundary as a proof of its own, as the
guide's "One proof, one case" says. Write at least one proof for every rule: a rule without
one is left to write a proof for. Several
proofs may name one rule, and one proof may name several rules when it drives a flow through
all of them: `- PROOF-7 (RULE-2, RULE-3, RULE-4): ...`.

A tag stands at the end of the proof line, after the text, never before the rule ids:

```
- PROOF-7 (RULE-7): A technician reads the rejection message and finds it clear @manual
- PROOF-8 (RULE-8): A batch of 500 samples is taken in; every sample has a result @slow
```

Tag a proof `@manual` when only human judgment settles it. A `@manual` proof has no test: a
person checks it in the sign-off walk of `purlin:sign` and may type what they saw. Until then
it reads `checked at sign-off`.

Tag a proof `@slow` when its test takes a long time, like an integration test or an
acceptance test;
`references/spec_quality_guide.md`, "A test that takes a long time", says when, and
`references/purlin_commands.md` which run starts it.

Add `@env(windows)`, `@env(macos)` or `@env(linux)` when the claim can only be proved on one
operating system. Those three are the whole vocabulary. A proof with no `@env` is satisfied by
a run on any operating system; a proof with one has its passed cell met only when a run on
that system passes it.

## Ids

A new rule takes one more than the highest of these:

- `> Highest-Rule:`;
- every rule number in the working copy of the spec;
- every rule number in `origin/main`'s copy, read with `git show origin/main:<spec>`.

Write that number into `> Highest-Rule:`, so a deleted number is never used again.

A new proof takes one more than the highest of `> Highest-Proof:` and every proof number in
either copy. Write that number into `> Highest-Proof:`.

In a spec that has neither line, both go after the last `>` line of the header:
`> Highest-Rule:` first, then `> Highest-Proof:`. Where one is there, the other goes beside it.

Ids are never reused. A deleted rule leaves its number vacant and every other rule keeps the
number it had. Renumbering by hand would silently repoint every test comment that already names
the old id, so a number moves only as "Renumbering" below says.

## Editing a rule during a build

`purlin:build` calls this skill when a rule turns out to be wrong while the code is being
written: the claim contradicts another rule, or it cannot be observed as stated. Fix the rule
text in place, keep the id, and say in the commit what changed and why.

## After a merge conflict

Two branches that took the same number before either merged leave a spec with one id twice,
often inside a conflict git could not merge. The number already on the default branch keeps
it; the rule or proof from the branch not yet merged moves to the next free number.

Do not edit git's conflict lines yourself. The renumbering resolves them: where both sides
only added lines it keeps both sides, it takes the higher `> Highest-` line, and then it
renumbers. Run it as "Renumbering" says.

A conflict it prints as `is left` is one it will not decide, such as one line both sides
changed. Show the person both versions. **Stop and ask** which survives. Edit that conflict
alone, and run the renumbering again.

Then stage the spec and the test files and commit. Where a merge is in progress, that commit
finishes it. Tell the person whose line moved, so the test comments on their branch move with
it. A moved rule's audit is read again.

Two branches that advanced the same anchor pin resolve to the newer sha.

## Renumbering

Where `purlin:drift`, the status, `purlin:build` or this skill finds a number written twice, or a
test comment whose proof's old wording now stands under another id, run the dry run first:

```bash
sh "${CLAUDE_PLUGIN_ROOT}/scripts/purlin_python.sh" "${CLAUDE_PLUGIN_ROOT}/scripts/spec/renumber.py" <name> --dry-run
```

It reads this checkout alone, fetches nothing and changes nothing. Show every line it prints: the
spec line that moves to the next free number, the side not already on the default branch; each
proof line that follows a moved rule; each test comment in this checkout that moves; the raised
`> Highest-` line; and each comment on another branch that names the moved id. Where it prints
`<name>: nothing to renumber.`, say so and ask nothing. Otherwise **Stop and ask**, exactly:

```
Do it? [y/N]
```

On yes, run it with `--yes`:

```bash
sh "${CLAUDE_PLUGIN_ROOT}/scripts/purlin_python.sh" "${CLAUDE_PLUGIN_ROOT}/scripts/spec/renumber.py" <name> --yes
```

It makes the edits, commits nothing, and ends on `Renumbered in <name>: ...` or `Resolved <n>
conflicts in <name>. Nothing is committed.` On anything else, renumber nothing. Run without
`--yes` the script asks the same question itself and, with nobody at a terminal, changes
nothing.

## When you are done

Once the person is satisfied with the rules and proofs you printed, write the file, check it as
step 7 says, commit it with the `spec(<name>):` prefix from `references/commit_conventions.md`, then end with exactly
this and nothing after it:

```
Spec saved: <name>. Next: purlin:build <name>
```

Never start the build yourself: the person runs `purlin:build` when they choose to.

When you edited an existing spec rather than creating one, say what moved before the offer:
which rules were added and which text changed.
