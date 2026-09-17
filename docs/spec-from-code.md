# Specs from existing code

For an engineer bringing a codebase that predates its specs into Purlin.

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
   position is written under `.purlin/runtime/`, so a session that ends halfway resumes at
   the next feature instead of starting over.
5. **A report**: how many features, how many rules, and how many of those rules already have
   a passing test.

## What it writes

Every rule carries `[origin: eng]` and `[risk: low]`:

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

`eng` is correct because an engineer derived the rule and no PM asked for it: `purlin:drift
pm` then shows these as engineer-added rather than as requirements out of nowhere. `low` is
correct because nobody has judged the cost of getting it wrong yet. Both are re-tagged later,
in one pass, and re-tagging never stales a signature.

Where a test already exercises the behaviour, the proof says so, and `purlin:build` adds the
marker to that test instead of writing a new one:

```
- PROOF-4 (RULE-4): tests/test_rate_limit.py::test_burst already asserts this @integration
```

Where nothing tests it, the proof is written as if the test existed. The rule lands Drafted
and `purlin:build` writes the test on the next pass.

## What it does not write

- No rule for a private helper. Rules describe behaviour someone outside the module can see.
- No implementation in a rule. "Uses a sorted set in the cache" is not a claim about
  behaviour; "rejects the 61st request in a minute" is.
- Nothing tagged `[origin: pm]`. No PM said any of this.
- No risk above `low`. That judgment belongs to the people who own the product.
- No records and no signatures. Those come from `purlin:audit` and `purlin:sign`.
- No rule for behaviour that could not be stated as an observable. The behaviour is noted in
  `> Description:` and the rule is dropped.

## What to do next

The skill names the next step from what it found:

| What it left | What to run |
|--------------|-------------|
| Rules a test already exercises | `purlin:test`, which tags those tests and shows what passes |
| Rules with no test at all | `purlin:build <name>` on the feature with the most of them |
| Everything drafted, and the team wants the paper trail | `purlin:init --gate strong` |

Then read the drafts. Retag the risk and the origin of anything a PM or a designer actually
owns, and delete the rules that turned out to describe a bug.

## Next

- The format the drafts are written in: [specs-and-anchors.md](specs-and-anchors.md)
- Who owns which rule from here on: [working-together.md](working-together.md)
