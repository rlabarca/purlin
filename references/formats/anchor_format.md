> Format-Version: 12

# Anchor format

An anchor is a set of rules for the whole project, kept under
`specs/_anchors/` or opening `# Anchor:`. No spec names an anchor. An anchor
uses the same two sections every spec uses, `## Rules` and `## Proof`, and the
same rule and proof grammar (`spec_format.md`).

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
> Type: <optional: api, security, brand, schema, legal, prodbrief>

## Rules

- RULE-1: For every <X> in the project, <Y holds>
- RULE-2: <another constraint, written the same way>

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
| `> Stack:` | Language and framework |
| `> Type:` | A suggestion to the reader: `api`, `security`, `brand`, `schema`, `legal`, `prodbrief`. Not enforced |
| `> Note:` | Free text for the reader: setup a checkout needs, why a source points where it does. Repeatable, and every parser ignores it |

### What an anchor covers

Every rule of an anchor holds across the whole project, and its tests check the
whole project. The project is every file git tracks but the records Purlin
writes: the results of a run, and the evidence package and its sign-offs under
`.purlin/evidence/`. Any change to the project ends an anchor's results. A change
to the settings file `.purlin/config.json` ends them as it ends a feature's:
changing a test command does, and changing `version` alone does not. Its
rules are signed with every other rule, in the one sign-off over the evidence
package. No bug is planted for an anchor's proof: the audit reads its tests with
the spot tests and the model alone. A rule that cannot be checked across the
whole project is not an anchor's; write it in the spec of each feature that
needs it, in that feature's words.

### Writing a rule that holds where there is nothing to check

Write each rule as "for every X in the project, Y holds", so a project with no
X has nothing to break it: `For every screen in the project, each input is
escaped before it is shown`. A project with no screens then meets the rule.
This matters most for an anchor other projects pull, since its author cannot
know what each project holds.

When the rule's test finds no X, it skips through its test tool's own skip,
with a reason starting exactly `nothing to check:`:

```python
# purlin: security_baseline PROOF-3
def test_every_screen_escapes_its_input():
    screens = find_screens()
    if not screens:
        pytest.skip('nothing to check: this project has no screens')
```

The proof then reads `nothing to check` in the evidence, with the text after
`nothing to check: ` as its reason, and on an anchor its rule counts as passed.
The status, the dashboard and the evidence package show the reason, so a signer
sees the rule was not exercised:
`security_baseline RULE-3: nothing to check here. It passes: this project has no screens.`
Only an anchor's rule counts such a skip as passed; on any other spec's rule it
reads as not run, its reason kept (`marker_format.md`). A project cannot set
a pulled rule aside: a pulled rule that fails here is a problem to raise with
its authors.

An anchor carries no `> Scope:`, and no spec carries `> Requires:` or
`> Global:`. Each such line is not read, and every status and test run warns of
it with its fix.

An anchor's proof takes the tags any proof takes (`spec_format.md`): `@manual`
for a rule no test can show, `@slow` for a check across the whole project that
takes a long time. `references/spec_quality_guide.md`, "A good anchor", is the
checklist for writing one, with a worked anchor showing all three forms.

## Part 2: consumer tracking fields

When a project pulls an anchor from somewhere else, `purlin:anchor` writes
tracking metadata into the local copy under `specs/_anchors/`. The author's
file in the source repo does not carry these. Such an anchor is a remote
anchor: its copy is pinned to one version of its source.

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

The file at the path is a spec in this format that holds at least one rule.
`purlin:anchor add` refuses any other source and writes nothing:

- a file on disk;
- a description in words;
- a file with no rule.

A copy whose `> Source:` names no repository reads `error` in `purlin:drift`
and in `purlin:anchor sync --check`. A local anchor carries no `> Source:` and
is never checked.

The status and `purlin:drift` check a pin against its source and pull nothing:
one cached `git ls-remote` per source per run reads the source's head, and the
anchor's copy, its pin and the checkout's git objects stay as they were. A pin
behind its source reads, in the status and in drift,
`X: anchor pin behind. The pin <old7> is behind its source, now <new7>. Run purlin:anchor sync X.`
Only `purlin:anchor sync X`
pulls: it shows the rule delta, rewrites the local copy from the source's new
head, keeps every `> Note:` line, and advances the pin. It commits nothing; the
copy is left changed for you to read and commit.

A `> Source:` value is repository-supplied text, so it never reaches git in
option position. A value that begins with `-` or names an `ext::` or `fd::`
transport is refused before any process starts, and the status line says
`X: anchor source refused. Its > Source: line begins with "-". Run purlin:spec X.`

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

## Editing a remote anchor

A consumer never edits a remote anchor's rule in place: the next sync would
overwrite it. A change to the rule is a pull request against the anchor repo, which the
next sync brings back. A rule that belongs only to this project goes in a local
anchor of its own when it holds across the whole project, and in the spec of
each feature it holds for when it does not.

A remote anchor's copy is written as its source holds it; a `> Requires:`, `> Global:` or `> Scope:` line in it is warned of, naming the source's owners as the ones to take it out.

## Fields 0.9.5 wrote

`> Visual-Reference:` and `> Visual-Hash:` are not part of the format. An
anchor that still carries one parses; the field is ignored and the file is
named once in the run's warnings. `purlin:init --update` removes them, and a
`> Source:` naming a `figma://` design together with its `> Pinned:` line.
