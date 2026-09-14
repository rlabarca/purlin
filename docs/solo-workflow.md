# Solo workflow

For one developer working alone at the `tested` gate.

At `tested`, CI requires one thing before a change can merge: every rule has a passing tagged
test. You write the record yourself, no one approves anything, and no CI workflow is written
unless you ask for one. This is the smallest thing Purlin can be, and everything above it is
additive.

If you have not set the project up yet, read [getting-started.md](getting-started.md) first.

## The setting

```json
{
  "gate": "tested",
  "min_strength": 50,
  "ai_review_at": "never"
}
```

`purlin:init` writes that into `.purlin/config.json` when you answer the one question with
`tested`. `min_strength` is the floor for the test strength, and risk and origin tags stay
optional. Read and change the file with the `purlin_config` tool rather than by hand, so a key
the installed Purlin no longer reads is reported instead of silently kept.

Init skips the CI workflow at this gate, because nothing here needs one. `purlin:init --ci`
writes it anyway when you want the run without the requirement.

## A session

```
purlin:drift eng
```

Start here. Drift reports what moved in the tree that the specs and the tests have not caught up
with: files touched and the rules they affect, rules with no test, tests with no marker. It
writes nothing.

```
purlin:spec <name>
purlin:build <name>
purlin:test <name>
```

Spec when a requirement is new or a rule turns out to be wrong; build to write the code and the
tagged tests; test to run them. `purlin:test` takes seconds and is the one you run constantly.
Loop between build and test until every rule the feature owns has a passing test.

```
purlin:verify
```

Then verify once, before you push.

## Your own record commit

`purlin:verify` runs the tagged tests, breaks the code on purpose, measures the share of those
breaks the tests caught, and writes one file:

```
.purlin/records/login/20260913T142201Z-a1b2c3d-developer.json
```

One record per verify run, per feature, committed. Adding a file never conflicts with another
branch. The commit message is `purlin: record for a1b2c3d`.

The label on the end of the name is not what decides whether a record counts. The last commit
that touched the file decides:

| Label | How it got there | Counts under |
|-------|------------------|--------------|
| ci | Written through the git host's API by the CI identity | `tested`, `recorded`, `approved` |
| developer | A person committed it | `tested` only |
| local | Not committed | Nothing |

At `tested`, your own commit is the record, so `purlin:verify` commits it for you. That is the
one gate where a developer writes the evidence their own change is measured by, and it is the
honest trade for working alone: the point at `tested` is that the tests ran and passed, not that
someone independent watched them run. The moment you raise the gate to `recorded`, only a `ci`
record counts and you stop committing them.

Verify keeps the newest three records per feature per operating system and prunes the rest. A
record named in the message of an annotated `validated/<name>` tag, which `purlin:verify --tag
1.0` writes, is kept for ever. The log of what was proved and when is the git history of
`.purlin/records/`.

## Test strength

Verify prints the test strength as an integer percent: of the deliberate breaks it made to your
code, the share your tests caught. A 40% strength on a feature reading 100% tested means most of
the code could change without a test noticing.

When the strength is below `min_strength`, the next-step line is `→ Run: purlin:build <feature>`
and the thing to add is the case the break escaped, not another assertion on the case you
already have. When no breaks engine is installed for the language, the strength prints `n/a` and
the gate falls back to the free checks.

## The pre-push hook

`purlin:init` offers a pre-push hook. It runs `purlin:test` and nothing else: the tagged tests
into `.purlin/runtime/proofs/`, in seconds, with no breaks and no record, so a push is never
held up by a full verify.

It prints one line either way. It blocks a push only when both of these are true: `pre_push` in
`.purlin/config.json` is `on`, and a tagged test failed. Every other outcome exits 0 and lets the
push through, including a missing Python interpreter, a project with no specs, and a failing test
in a project that left `pre_push` at its default of `off`. `git push --no-verify` skips it
entirely.

The hook is a convenience, not a control. What a change must clear before it merges is the gate,
and the gate is the git host's to enforce.

## When to raise the gate

Raise to `recorded` when any one of these becomes true:

- A second person commits to the repository. Two people means one of you can write a record for
  the other's change, and `recorded` is what stops that.
- Someone outside engineering owns a requirement. A PM's or a designer's rule needs `origin`
  tags and a review list to be worth tagging.
- You need to answer "what was proved at the commit we shipped?" to someone who was not there.
  A CI-written record at a known commit answers it; a developer-written one asks them to trust
  you.

```
purlin:init --gate recorded
```

Raising is additive. It writes the CI workflow (`purlin.yml`), creates `designs/` if it is
missing, prints the branch rules for your git host, and asks before each write. It changes no
rule, deletes no record, and leaves every record you already committed exactly where it is. The
records you wrote yourself stop counting from that point; CI writes the ones that count from the
next push.

[team-workflow.md](team-workflow.md) is the guide for the gate you land on.
[raising-the-gate-and-upgrading.md](raising-the-gate-and-upgrading.md) covers the move itself,
in both directions.
