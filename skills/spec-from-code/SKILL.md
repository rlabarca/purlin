---
name: spec-from-code
description: Read an existing codebase and write the specs it already implies
---

# purlin:spec-from-code

Read a codebase that has no specs and write the rules it already implies. Run this once, on
the way in. Afterwards every new rule comes from `purlin:spec`.

**Paths.** Every `references/` and `scripts/` path below is inside the plugin and is reached
through `${CLAUDE_PLUGIN_ROOT}`. A project carries none of them.

**The honest limit.** A rule read off code says what the code does, not what it should do. A
bug becomes a rule if you are not careful, and every rule this skill writes is a draft until a
person reads it. Say so when you hand the result over.

## Before you start

Call `sync_status`. When the project has no `.purlin/config.json`, run `purlin:init` first:
this skill writes specs and nothing can read them until the project is set up.

## Procedure

1. **Survey.** Walk the tree once. Note the entry points, the modules with real branching, the
   configuration surface, and the test files. Ignore generated code, vendored dependencies and
   build output.
2. **Propose a taxonomy.** Group the behaviour into features, one per coherent area, and print
   the list with a one-line description and the files each would carry in `> Scope:`. Twenty
   to forty features is normal for a mid-sized service; two hundred means the grouping is too
   fine.
3. **Let the person edit it.** Show the list and stop. Merge, split and rename until they say
   it is right. Everything after this point is mechanical, so this is the only step worth a
   conversation.
4. **Order by dependency.** Write the shared and lower-level features first, so a later spec
   can say `> Requires: <name>` instead of repeating their rules.
5. **Write one spec at a time**, in that order, committing each on its own with the
   `spec(<name>):` prefix from `references/commit_conventions.md`. Write the position to
   `.purlin/runtime/spec-from-code.json` after each commit, so a session that ends halfway
   resumes at the next feature instead of starting over.
6. **Report.** Print the count of features, the count of rules, how many rules already
   have a passing test, and each proof an existing test already shows, beside that test.

## What the rules look like

Every rule this skill writes carries `[level: passed]`:

```markdown
# Feature: rate_limit

> Description: Per-client request limiting on the public API.
> Scope: src/middleware/rate_limit.py

## Rules

- RULE-1: Reject a client with more than 60 requests in a rolling minute with HTTP 429 [level: passed]
- RULE-2: Include a Retry-After header on every 429 response [level: passed]

## Proof

- PROOF-1 (RULE-1): One client sends 61 requests within one minute; the first 60 return 200 and the 61st returns 429
- PROOF-2 (RULE-2): The 429 answer to a 61st request carries a `Retry-After` header holding a whole number of seconds above 0
```

`passed` is correct because nobody has judged yet whether the rule is worth an audit and a
signature. The level is re-marked later, in one pass, and re-marking it stales no signature.

For the rule and proof grammar read `references/formats/spec_format.md`; for what makes a rule
worth keeping read `references/spec_quality_guide.md`.

## Where the proofs come from

Write every proof to `references/spec_quality_guide.md`, "Writing proofs". When a test
already shows what a proof asks, the proof says what that test shows, in the same words it
would use if no test existed, and never names the test. Then tie the two: offer to add the
marker comment above that test, `purlin: <feature> PROOF-<n>` in the file's own comment
syntax, and write no new test. A test that shows part of what the proof asks is not that
test; leave it unmarked and let `purlin:build` write one.

When nothing tests it, write the proof as if the test existed. The rule then reads `no test`
in its passed cell and `purlin:build` writes the test on the next pass.

Do not invent a proof for a rule you could not state as an observable. Drop the rule instead
and note the behaviour in `> Description:`.

## What not to do

- Do not write a rule for a private helper. Rules describe behaviour someone outside the
  module can see.
- Do not copy an implementation into a rule. "Uses a Redis sorted set" is not a claim about
  the software's behaviour; "rejects the 61st request in a minute" is.
- Do not write `[level: strong]` or `[level: signed]`. That judgment belongs to the people
  who own the product.
- Do not write evidence or signatures. `purlin:test` and `purlin:audit` write the evidence,
  and `purlin:sign` writes signatures.

## When you are done

Report the counts, then name the next step from the state:

- Rules whose existing tests now carry their markers: `→ Next: purlin:test`, which runs
  them and shows what passes.
- Rules with no test at all: `→ Next: purlin:build <name>` on the feature with the most of
  them.
- Every rule written and the team wants the paper trail:
  `→ Next: purlin:init --gate strong`.
