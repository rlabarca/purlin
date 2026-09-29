---
name: anchor
description: Create anchors, pull them from another repository, and keep the pins current
---

# purlin:anchor

An anchor is a spec for something shared across features: a security policy, an API contract,
a brand rule. Feature specs name it with `> Requires: <name>` and its
rules are counted with theirs.

**Paths.** Every `references/` and `scripts/` path below is inside the plugin and is reached
through `${CLAUDE_PLUGIN_ROOT}`. A project carries none of them. For the format, read
`references/formats/anchor_format.md`; it is not restated here.

## One repository is the default

Most projects need nothing but `specs/_anchors/`. Product, a developer or QA changes a file in
that folder like any other spec, and nothing is pinned or synced. Reach for an anchor
repository only when two or more projects must share the same rules, and say so plainly when
someone asks: a second repository is a cost, and one project does not need it.

## create

```bash
purlin:anchor create <name>
```

Writes `specs/_anchors/<name>.md` with the same two sections every spec uses. The folder
`specs/_anchors/` is created with the first anchor, written here or brought in by `add`. Give it a
`> Description:`, a `> Scope:` and, when it helps the reader, a `> Type:` of `api`, `security`,
`brand`, `schema` or `legal`. Rules and proofs follow the grammar in
`references/formats/spec_format.md`.

Commit it with the `anchor(<name>): create` prefix from `references/commit_conventions.md`.
Then add `> Requires: <name>` to every feature spec the anchor governs, or `> Global: true` to
the anchor itself when it governs all of them.

## add

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/anchor/upstream.py" add <git-url> --path <file>
```

Fetches the anchor from another repository and writes the local copy under
`specs/_anchors/`, with two tracking lines the author's own file does not carry:

```markdown
> Source: https://github.com/acme/policies.git specs/no_eval.md
> Pinned: abc1234def5678
```

**A pin is always a commit, never a branch.** A branch moves, and an anchor whose rules
changed under a project with no diff to read is exactly what pinning exists to prevent.

When the source file is free text rather than rules, the script writes the text and prints
`<name>: written to <path>, pinned <sha7>` and then `the source is free text: no rules written
yet. Run purlin:anchor create <name>.` Write the rules from the text with `purlin:anchor create`
and say so in the local copy's `> Description:`, so nobody mistakes your reading for the
author's words.

## sync

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/anchor/upstream.py" sync [<name> | --all] [--check] [--json]
```

`--check` reports without writing, one line per anchor: `security_baseline: the pin abc1234
is behind its source, now 9f8e7d6. Run purlin:anchor sync security_baseline.` It exits 1 when a
pin is behind and 2 when a source could not be read. `purlin:drift` runs the same check, one
cached lookup per source per run, so a developer sees a pin that is behind at the start of a
session without asking for it.

Without `--check`, sync rewrites the local copy, advances the pin and prints what moved:
`security_baseline: RULE-3 changed, RULE-6 added. Pin advanced from abc1234 to 9f8e7d6.` It
commits nothing: commit the copy in one commit with the `anchor(<name>):` prefix, so the diff
shows exactly which rules moved. A signature on a rule whose text moved ends, and the rule is
back to `to sign`.

## Changing a pinned rule

**Never edit a pinned rule in place.** The next sync overwrites it and the change is lost with
no trace. A change to the rule is a pull request against the source repository, made in a
checkout of it; once it merges, `sync` brings it here.

A rule that belongs only to this project goes in a separate local anchor that says
`> Requires: <the pinned one>`, and the pinned copy stays untouched.


## When you are done

Name the next step from the state:

- Anchor created, no feature requires it yet: name the features that should and offer to add
  `> Requires:` to each, `→ Run: purlin:spec <feature>`
- Anchor added or synced, rules changed: `→ Run: purlin:test`, whose `Left to do` names what
  the change sent back to be audited or signed.
- Pin current and nothing moved: say so in one line, `→ Run: purlin:status`
