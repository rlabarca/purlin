> Format-Version: 7

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
> Type: <optional: design, api, security, brand, schema, legal, prodbrief>

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
| `> Type:` | A suggestion to the reader: `design`, `api`, `security`, `brand`, `schema`, `legal`, `prodbrief`. Not enforced |
| `> Global:` | `true` applies the anchor's rules to every feature spec without `> Requires:` |
| `> Note:` | Free text for the reader: setup a checkout needs, why a source points where it does. Repeatable, and every parser ignores it |

## Part 2: consumer tracking fields

When a project pulls an anchor from somewhere else, `purlin:anchor` writes
tracking metadata into the local copy under `specs/_anchors/`. The author's
file in the source repo does not carry these.

| Field | Description |
|-------|-------------|
| `> Source:` | Where the anchor comes from. Two shapes, below |
| `> Path:` | The path inside the source repo, when `> Source:` carries the URL alone |
| `> Pinned:` | The commit sha of a git source, or the hash of the pinned local files |

### Source shape 1: a git URL plus a path

```markdown
> Source: https://github.com/acme/security-policies.git specs/no_eval.md
> Pinned: abc1234def5678
```

The URL and the path may also be split across `> Source:` and `> Path:`; both
spellings parse the same. A pin is always a commit, never a branch: a branch
moves, and an anchor whose content changed under a project without a diff is
what pinning exists to prevent.

`purlin:drift` runs one cached `git ls-remote` per source per run and reports
`anchor X is behind its pin`. `purlin:anchor sync X` shows the delta, updates
the local copy, copies any designs it references into `designs/<anchor>/` and
advances the pin, all in one commit.

A `> Source:` value is repository-supplied text, so it never reaches git in
option position. A value that begins with `-` or names an `ext::` or `fd::`
transport is refused before any process starts, and the status line says
`(source rejected: begins with "-")`.

### Source shape 2: local file globs

A design anchor pins files in the project instead of a repo:

```markdown
# Anchor: checkout_design

> Description: The checkout screens, as exported.
> Source: designs/checkout/*.png, designs/checkout/*.pdf
> Pinned: 9f2c1ab4e7d0
> Type: design

## Rules

- RULE-1: The checkout page shows the order total above the pay button [origin: design]

## Proof

- PROOF-1 (RULE-1): Load /checkout with one item in the basket; verify the text "Order total" appears above the button labelled "Pay" @e2e
```

`> Pinned:` is the hash of the named files. A new export changes it, which
stales the signatures of that anchor's rules, and the brief shows the mock
beside the screenshot the test captured. A proof for a design rule is an
end-to-end observable (a route, a state, visible text, presence), never a
selector.

### Example: what a consumer's copy looks like

```markdown
# Anchor: security_no_eval

> Description: No eval() calls in production code
> Source: git@github.com:acme/security-policies.git specs/no_eval.md
> Pinned: abc1234def5678
> Type: security

## Rules

- RULE-1: No eval() in source files [risk: high]
- RULE-2: No exec() in source files [risk: high]

## Proof

- PROOF-1 (RULE-1): Grep src/ for "eval("; verify zero matches
- PROOF-2 (RULE-2): Grep src/ for "exec("; verify zero matches
```

The `> Source:` and `> Pinned:` lines were added by Purlin; the author's file
in `acme/security-policies` does not carry them.

## Requires

A feature spec names an anchor:

```markdown
# Feature: checkout

> Requires: security_no_eval, checkout_design
```

Its rules are counted with the feature's own, and its tests must prove both.

## Editing a pinned anchor

A consumer never edits a pinned rule in place: the next sync would overwrite
it. `purlin:anchor propose <name>` drafts the pull request to the anchor repo
instead, and a rule that belongs only to this project goes in a separate
local anchor that `> Requires:` the pinned one.

## Global anchors

An anchor with `> Global: true` applies its rules to every non-anchor feature
spec. Features do not name it; its rules appear in each feature's count with
the label `global`.

## Retired

`figma://` sources, `> Visual-Reference:`, `> Visual-Hash:` and the visual
hash comparison are retired. A design is a versioned file, read and merged by
pull request, never a live tool connection. An anchor that still carries one of
those fields parses; the field is ignored and the file is named once in the
run's warnings.
