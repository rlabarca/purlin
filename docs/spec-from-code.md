# Specs from existing code

For a developer bringing a codebase that predates its specs into Purlin.

```
purlin:spec-from-code
```

Run it once, on the way in. It reads the tree, proposes a grouping of the behaviour into
features, and writes one spec per feature. Afterwards every new rule comes from
`purlin:spec`.

Run `purlin:init` first. This skill writes specs and nothing can read them until the project
has a `.purlin/config.json`.

## The honest limit

A rule read off code says what the code does, not what it should do. A bug becomes a rule if
nobody is careful. Every rule this skill writes is a draft until a person reads it, and the
skill says so when it hands the result over.

## What happens

1. **Survey.** It walks the tree once and notes the entry points, the modules with real
   branching, the configuration surface and the test files. Generated code, vendored
   dependencies and build output are ignored.
2. **A proposed taxonomy.** It prints the features it would write, each with a one-line
   description and the files it would carry in `> Scope:`. Twenty to forty features is normal
   for a mid-sized service. Two hundred means the grouping is too fine.
3. **Your edits.** It stops there and waits. Merge, split and rename until the list is right.
   This is the only step worth a conversation; everything after it is mechanical.
4. **One spec at a time**, shared and lower-level features first so a later spec can say
   `> Requires: <name>` instead of repeating their rules. Each is committed on its own. The
   position is written to `.purlin/runtime/spec-from-code.json`, so a session that ends
   halfway resumes at the next feature instead of starting over.
5. **A report**: how many features, how many rules, how many of those rules already have a
   passing test, and each proof an existing test already shows, beside that test.

## What it writes

Every rule carries `[level: passed]`:

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

Where a test already shows what a proof asks, the proof says what that test shows, in the words
it would use if no test existed, and never names the test. The skill then offers to add the
marker comment above that test and writes no new test:

```python
# purlin: rate_limit PROOF-1
def test_burst():
```

A test that shows part of what the proof asks is left unmarked. Where nothing tests it, the
proof is written as if the test existed. The rule's passed cell
reads `no test`, and `purlin:build` writes the test on the next pass.

## What it does not write

- No rule for a private helper. Rules describe behaviour someone outside the module can see.
- No implementation in a rule. "Uses a sorted set in the cache" is not a claim about
  behaviour; "rejects the 61st request in a minute" is.
- No level above `passed`. That judgment belongs to the people who own the product.
- No evidence and no signatures. Those come from `purlin:test`, `purlin:audit` and `purlin:sign`.
- No rule for behaviour that could not be stated as an observable. The behaviour is noted in
  `> Description:` and the rule is dropped.

## What to do next

The skill names the next step from what it found:

| What it left | What to run |
|--------------|-------------|
| Rules whose existing tests now carry their markers | `purlin:test`, which runs them and shows what passes |
| Rules with no test at all | `purlin:build <name>` on the feature with the most of them |
| Every rule written, and the team wants the paper trail | `purlin:init --gate strong` |

Then read the rules. Re-mark the level of anything product asked for, and delete the rules that
turned out to describe a bug.

## Next

- The format the rules are written in: [specs-and-anchors.md](specs-and-anchors.md)
- Who owns which rule from here on: [working-together.md](working-together.md)
