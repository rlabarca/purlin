---
name: spec-from-code
description: Read an existing codebase and write the specs it already implies
---

# purlin:spec-from-code

Read a codebase that has no specs and write the rules it already implies. Run this once, on
the way in. Afterwards every new rule comes from `purlin:spec`.

**Paths.** Every `references/` and `scripts/` path below is inside the plugin and is reached
through `${CLAUDE_PLUGIN_ROOT}`. A project carries none of them.

**The honest limit.** Every rule is written from what its test expects, passing or not, and
no test is run first: a failing test keeps its rule failing until the code is fixed. Where no
test covers the code, the rule says what the code does, not what it should do, so every rule
this skill writes is a draft until a person reads it. Say so when you hand the result over.

## Before you start

Call `sync_status` with `project_root` set to the project root, the top folder of the git
checkout. When the project has no `.purlin/config.json`, run `purlin:init` first. Run
`git branch --show-current`; when it prints nothing the checkout is on no branch, so make one
with `git switch -c <name>` before the first commit.

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
4. **Order by dependency.** Where features share rules, write those rules once in an anchor
   with `purlin:anchor create <name>`, first, and have each feature name it with
   `> Requires: <name>`. `> Requires:` names anchors only.
5. **Write one spec at a time**, in that order, committing each spec with the comments it adds
   above existing tests, on its own, with the `spec(<name>):` prefix from
   `references/commit_conventions.md`. After each commit write
   `.purlin/runtime/spec-from-code.json`,
   `{"features": [<the agreed list, in order>], "written": [<each feature committed so far>]}`;
   a session that finds it goes on with the first feature not in `written`.
6. **Report.** Print one line per feature: its rules, its proofs, how many proofs an existing
   test already shows, and how many have no test. Then each test left untied, with its reason,
   and last the source files that got no rule, for a person or an agent to decide.

## What the rules look like

A spec this skill writes:

```markdown
# Feature: rate_limit

> Description: Per-client request limiting on the public API.
> Scope: src/middleware/rate_limit.py
> Highest-Rule: 2

## Rules

- RULE-1: Reject a client with more than 60 requests in a rolling minute with HTTP 429
- RULE-2: Include a Retry-After header on every 429 response

## Proof

- PROOF-1 (RULE-1): One client sends 61 requests within one minute; the first 60 return 200 and the 61st returns 429
- PROOF-2 (RULE-2): The 429 answer to a 61st request carries a `Retry-After` header holding a whole number of seconds above 0
```

For the rule and proof grammar read `references/formats/spec_format.md`; for what makes a rule
worth keeping read `references/spec_quality_guide.md`.

## Where the proofs come from

Write every proof to `references/spec_quality_guide.md`, "Writing proofs". When a test
already shows what a proof asks, the proof says what that test shows, in the same words it
would use if no test existed, and never names the test. Then tie the two: offer to add the
marker comment above that test, `purlin: <feature> PROOF-<n>` in the file's own comment
syntax, and write no new test.

Tie every test the project already has. A test is left untied for one of five reasons, and the
report lists each such test with its reason: it shows only part of what a rule needs, it
repeats a test already tied, it tests code the project does not own, it cannot carry a comment
(an example inside a function's documentation), or it tests code no caller can reach. A test
of the test suite's own helpers tests code no caller can reach. A test that is commented out,
or a benchmark the project's test command does not run, is not a test: leave it and count it
nowhere. `purlin:build` writes the test a rule still lacks.

When nothing tests it, write the proof as if the test existed. The rule then reads `no test`
in its passed cell and `purlin:build` writes the test on the next pass.

Do not invent a proof for a rule you could not state as an observable. Drop the rule instead
and note the behaviour in `> Description:`.

## What not to do

- Do not write a rule for code no caller outside the project can reach: list its files among
  the files with no rule. A caller reaches what the package exports: in Python, the names a
  module's `__all__` lists, or with no `__all__` the names with no leading underscore in a
  module whose own name has none; in JavaScript, what `package.json`'s `main` or `exports`
  reaches; in C#, the `public` types of a project that is not a test project.
- Do not copy an implementation into a rule. "Uses a Redis sorted set" is not a claim about
  the software's behaviour; "rejects the 61st request in a minute" is.
- Do not write evidence or signatures. `purlin:test` and `purlin:audit` write the evidence,
  and `purlin:sign` writes signatures.

## When you are done

Report the counts, then name the first of these that applies:

1. Rules whose existing tests now carry their comments: `→ Run: purlin:test`, which suggests
   the test command and runs them.
2. Rules with no test at all: `→ Run: purlin:build <name>` on the feature with the most of
   them.
3. At the gate `passed`, with every rule passing and the team wanting the paper trail:
   `→ Run: purlin:init --gate strong`.
