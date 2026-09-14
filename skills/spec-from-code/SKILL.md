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
   `spec(<name>):` prefix from `references/commit_conventions.md`. Record the position in
   `.purlin/runtime/spec-from-code.json` after each commit, so a session that ends halfway
   resumes at the next feature instead of starting over.
6. **Report.** Print the count of features, the count of rules, and how many rules already
   have a passing test.

## What the rules look like

Every rule this skill writes carries `[origin: eng]` and `[risk: low]`:

```markdown
# Feature: rate_limit

> Description: Per-client request limiting on the public API.
> Scope: src/middleware/rate_limit.py

## Rules

- RULE-1: Reject a client with more than 60 requests in a rolling minute with HTTP 429 [origin: eng] [risk: low]
- RULE-2: Include a Retry-After header on every 429 response [origin: eng] [risk: low]

## Proof

- PROOF-1 (RULE-1): Send 61 requests in one minute from one client; verify the 61st returns 429 @integration
- PROOF-2 (RULE-2): Read the 429 response headers; verify Retry-After is present and is a positive integer @integration
```

`eng` is correct because you derived the rule, not a PM: `purlin:drift pm` then shows these as
engineer-added rules rather than as requirements nobody asked for. `low` is correct because
nobody has judged the cost of getting it wrong yet. Both are re-tagged later, in one pass, and
re-tagging never stales an approval.

For the rule and proof grammar read `references/formats/spec_format.md`; for what makes a rule
worth keeping read `references/spec_quality_guide.md`.

## Where the proofs come from

When a test already exercises the behaviour, write the proof to describe what that test
asserts and say so, so `purlin:build` can add the marker instead of writing a new test:

```
- PROOF-4 (RULE-4): tests/test_rate_limit.py::test_burst already asserts this @integration
```

When nothing tests it, write the proof as if the test existed. The rule then lands in the
Drafted state and `purlin:build` writes the test on the next pass.

Do not invent a proof for a rule you could not state as an observable. Drop the rule instead
and note the behaviour in `> Description:`.

## What not to do

- Do not write a rule for a private helper. Rules describe behaviour someone outside the
  module can see.
- Do not copy an implementation into a rule. "Uses a Redis sorted set" is not a claim about
  the software's behaviour; "rejects the 61st request in a minute" is.
- Do not tag anything `[origin: pm]`. No PM said any of this.
- Do not add risk tags above `low`. That judgment belongs to the people who own the product.
- Do not write approvals or records. Those come from `purlin:verify` and `purlin:approve`.

## When you are done

Report the counts, then name the next step from the state:

- Rules whose behaviour is already tested: `→ Next: purlin:test`, which tags the existing
  tests and shows what passes.
- Rules with no test at all: `→ Next: purlin:build <name>` on the feature with the most of
  them.
- Everything drafted and the team wants the paper trail:
  `→ Next: purlin:init --gate recorded`.
