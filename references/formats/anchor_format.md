> Format-Version: 10

# Anchor format

An anchor is a spec for something shared across features. Features reference
it with `> Requires:`, or it applies to all of them with `> Global: true`. An
anchor uses the same two sections every spec uses, `## Rules` and `## Proof`,
and the same rule and proof grammar (`spec_format.md`).

This document has two parts:

1. **Authoring**: what you write when you create an anchor, locally or in an
   anchor repo for other projects to consume.
2. **Consumer tracking**: what Purlin writes into the local copy when a
   project pulls an anchor from somewhere else. You do not write these.

## Part 1: authoring

### Template

```markdown
# Anchor: <name>

> Description: <what cross-cutting concern this anchor defines>
> Scope: <file paths this anchor governs>
> Type: <optional: api, security, brand, schema, legal, prodbrief>

## Rules

- RULE-1: <constraint that applies to every feature requiring this anchor>
- RULE-2: <another constraint>

## Proof

- PROOF-1 (RULE-1): <how compliance is observed>
- PROOF-2 (RULE-2): <how compliance is observed>
```

### Location

A local anchor lives in:

```
specs/_anchors/<name>.md
```

Name it what you like. There are no enforced prefixes. An anchor authored in
a separate repo lives wherever that repo puts it; the consuming project names
it by repo URL plus path.

### Metadata fields you write

| Field | Description |
|-------|-------------|
| `> Description:` | Plain-language description. Continuation lines start with `>`. Displayed in the dashboard |
| `> Scope:` | File paths this anchor governs |
| `> Stack:` | Language and framework |
| `> Type:` | A suggestion to the reader: `api`, `security`, `brand`, `schema`, `legal`, `prodbrief`. Not enforced |
| `> Global:` | `true` applies the anchor's rules to every feature spec without `> Requires:` |
| `> Note:` | Free text for the reader: setup a checkout needs, why a source points where it does. Repeatable, and every parser ignores it |

## Part 2: consumer tracking fields

When a project pulls an anchor from somewhere else, `purlin:anchor` writes
tracking metadata into the local copy under `specs/_anchors/`. The author's
file in the source repo does not carry these.

| Field | Description |
|-------|-------------|
| `> Source:` | Where the anchor comes from: a git URL plus a path, below |
| `> Path:` | The path inside the source repo, when `> Source:` carries the URL alone |
| `> Pinned:` | The commit sha of the source |

### The source: a git URL plus a path

```markdown
> Source: https://github.com/acme/security-policies.git specs/no_eval.md
> Pinned: abc1234def5678
```

The URL and the path may also be split across `> Source:` and `> Path:`; both
spellings parse the same. A pin is always a commit, never a branch: a branch
moves, and an anchor whose content changed under a project without a diff is
what pinning exists to prevent.

The file at the path is a spec in this format that holds at least one rule. `purlin:anchor add` refuses any other source, a file on disk, a description in words or a file with no rule, and writes nothing. A copy whose `> Source:` names no repository reads `error` in `purlin:drift` and in `purlin:anchor sync --check`. A local anchor carries no `> Source:` and is never checked.

`purlin:drift` runs one cached `git ls-remote` per source per run and reports
`anchor X: the pin <old7> is behind its source, now <new7>. Run purlin:anchor sync X.`
`purlin:anchor sync X` shows the delta, updates the local copy and advances the
pin, all in one commit.

A `> Source:` value is repository-supplied text, so it never reaches git in
option position. A value that begins with `-` or names an `ext::` or `fd::`
transport is refused before any process starts, and the status line says
`(source rejected: begins with "-")`.

### Example: what a consumer's copy looks like

```markdown
# Anchor: security_no_eval

> Description: No eval() calls in production code
> Source: git@github.com:acme/security-policies.git specs/no_eval.md
> Pinned: abc1234def5678
> Type: security

## Rules

- RULE-1: No eval() in source files
- RULE-2: No exec() in source files

## Proof

- PROOF-1 (RULE-1): The project's source files are searched for a call to `eval`; the search finds 0 calls
- PROOF-2 (RULE-2): The project's source files are searched for a call to `exec`; the search finds 0 calls
```

The `> Source:` and `> Pinned:` lines were added by Purlin; the author's file
in `acme/security-policies` does not carry them.

## Requires

A feature spec names an anchor:

```markdown
# Feature: checkout

> Requires: security_no_eval
```

Its rules are counted with the feature's own, and its tests must prove both.

## Editing a pinned anchor

A consumer never edits a pinned rule in place: the next sync would overwrite
it. A change to the rule is a pull request against the anchor repo, which the
next sync brings back, and a rule that belongs only to this project goes in a
separate local anchor that `> Requires:` the pinned one.

## Global anchors

An anchor with `> Global: true` applies its rules to every non-anchor feature
spec. Features do not name it; its rules appear in each feature's count with
the label `global`.

## Fields 0.9.5 wrote

`> Visual-Reference:` and `> Visual-Hash:` are not part of the format. An
anchor that still carries one parses; the field is ignored and the file is
named once in the run's warnings. `purlin:init --update` removes them, and a
`> Source:` naming a `figma://` design together with its `> Pinned:` line.
