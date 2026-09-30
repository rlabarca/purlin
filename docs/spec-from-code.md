# Specs from existing code

For a developer bringing a codebase that predates its specs into Purlin.

```
purlin:spec-from-code
```

Run it once, on the way in. It reads the tree, proposes a grouping of the behaviour into
features, and writes one spec per feature. Afterwards every new rule comes from
`purlin:spec`.

Set the project up first. On a project with no `.purlin/config.json` the skill runs
`purlin:init` before anything else, because a test run stops without it:

```
No .purlin/config.json here, so nothing ran. Run purlin:init to write it.
```

`purlin:status` reads the specs either way. Setup on a project that holds code ends by naming
this skill:

```
No specs found under specs/.
→ Run: purlin:spec-from-code to write the specs this code already implies.
```

The skill commits as it goes, so it checks that the checkout is on a branch first. When
`git branch --show-current` prints nothing, it makes one with `git switch -c <name>` before the
first commit.

## The honest limit

Where a test exists, each rule is written from what the test expects, whether that test passes
or not, and no test is run first: a failing test keeps its rule failing until the code is
fixed. Where no test covers the code, the rule says what the code does, not what it should do.
Every rule this skill writes is a draft until a person reads it, and the skill says so when it
hands the result over.

## What happens

1. **Survey.** It walks the tree once and notes the entry points, the modules with real
   branching, the configuration surface and the test files. Generated code, vendored
   dependencies and build output are ignored.
2. **A proposed list of features.** It prints the features it would write, each with a
   one-line description and the files it would carry in `> Scope:`. Twenty to forty features
   is normal for a mid-sized service. Two hundred means the grouping is too fine.
3. **Your edits.** It stops there and waits. Merge, split and rename until the list is right.
   This is the only step worth a conversation; everything after it is mechanical.
4. **Shared rules first.** Rules that hold across the whole project, it writes once in an
   anchor, with `purlin:anchor create <name>`. A rule that several features share and that does
   not hold everywhere is written in each of their specs.
5. **One spec at a time**, in that order. Each spec is committed on its own with the comments
   the skill adds above existing tests, as `spec(<name>):`. After each commit it writes
   `.purlin/runtime/spec-from-code.json`:

   ```json
   {"features": ["rate_limit", "export"], "written": ["rate_limit"]}
   ```

   `features` is the agreed list in order and `written` each feature committed so far, so a
   session that ends halfway goes on with the first feature not in `written`.
6. **A report.** One line per feature: its rules, its proofs, how many proofs an existing test
   already shows, and how many have no test. Then each test left untied, with its reason, and
   last the source files that got no rule, for a person or an agent to decide.

## What it writes

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

Where a test already shows what a proof asks, the proof says what that test shows, in the words
it would use if no test existed, and never names the test. The skill then offers to add the
marker comment above that test and writes no new test:

```python
# purlin: rate_limit PROOF-1
def test_burst():
```

Where nothing tests a rule, the proof is written as if the test existed. The rule's passed cell
reads `no test`, and `purlin:build` writes the test on the next pass.

## The tests it leaves untied

It ties every test the project already has, except a test that:

- shows only part of what a rule needs;
- repeats a test already tied;
- tests code the project does not own;
- cannot carry a comment, such as an example inside a function's documentation;
- tests code no caller can reach, the test suite's own helpers among them.

The report lists each such test with its reason. A test that is commented out, or a benchmark
the project's test command does not run, is not a test: it is left alone and counted nowhere.

## What it does not write

- No rule for code no caller outside the project can reach. Its files are listed among the
  files with no rule. A caller reaches what the package exports: in Python, the names a
  module's `__all__` lists, or with no `__all__` the names with no leading underscore in a
  module whose own name has none; in JavaScript, what `package.json`'s `main` or `exports`
  reaches; in C#, the `public` types of a project that is not a test project.
- No implementation in a rule. "Uses a sorted set in the cache" is not a claim about
  behaviour; "rejects the 61st request in a minute" is.
- No evidence and no signatures. Those come from `purlin:test`, `purlin:audit` and
  `purlin:sign`.
- No rule for behaviour that could not be stated as an observable. The behaviour is noted in
  `> Description:` and the rule is dropped.

## What to do next

The skill reports the counts, then names the first of these that applies:

| What it left | What it names |
|--------------|---------------|
| Rules whose existing tests now carry their comments | `→ Run: purlin:test`, which suggests the test command and runs them |
| Rules with no test at all | `→ Run: purlin:build <name>` on the feature with the most of them |
| At the gate `passed`, every rule passing, and the team wanting the paper trail | `→ Run: purlin:init --gate strong` |

Before the first test run the status already counts the marked tests as work to run:

```
2 rules. 0 pass their tests.
Left to do:
  1 rule to write a test for: purlin:build
  1 rule to test: purlin:test
```

The first `purlin:test` finds no test command, suggests one for each test tool it recognises,
and runs once you confirm it. Then read the rules. A rule that reads `failed` stays: it says
what its test expects, and it reads `failed` until the code is fixed.
`references/spec_quality_guide.md`, "When a test fails, fix the code", says how to tell a bug in
the code from a bug in the test.

## Next

- The format the rules are written in: [specs-and-anchors.md](specs-and-anchors.md)
- Who owns which rule from here on: [working-together.md](working-together.md)
