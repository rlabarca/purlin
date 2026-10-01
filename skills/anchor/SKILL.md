---
name: anchor
description: Create anchors, pull them from another repository, and keep the pins current
---

# purlin:anchor

An anchor is a set of rules for the whole project: a security policy, an API contract, a brand
rule. Its tests check the whole project, and each of its rules is counted and audited
once. No spec names an anchor. Each rule is written to hold across the project, as "for every
X in the project, Y holds", so a project with no X has nothing to break it;
`references/spec_quality_guide.md` says how.

**Paths.** Every `references/` and `scripts/` path below is inside the plugin and is reached
through `${CLAUDE_PLUGIN_ROOT}`. A project carries none of them. For the format, read
`references/formats/anchor_format.md`; it is not restated here. Pass `project_root` on every
Purlin tool call: the top folder of the git checkout you are working in.

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
`> Description:` and, when it helps the reader, a `> Type:`. An anchor carries no `> Scope:`: its
rules cover the whole project and its tests check the whole project. A rule that cannot be
checked across the whole project is not an anchor's: write it in the spec of each feature that
needs it, with `purlin:spec <feature>`. Rules and proofs follow the grammar in
`references/formats/spec_format.md`.

A test of an anchor that finds nothing to check in this project skips, through the test tool's
own skip, with a reason starting `nothing to check:`, as in `nothing to check: this project has
no screens`. The rule then passes, and `purlin:status` prints the reason.
`references/spec_quality_guide.md`, "A good anchor", is the checklist for an anchor's rules and
proofs, the `@slow` tag for a long whole-project check and the `@manual` tag among them.

Commit it with the `anchor(<name>): create` prefix from `references/commit_conventions.md`.

## add

```bash
sh "${CLAUDE_PLUGIN_ROOT}/scripts/purlin_python.sh" "${CLAUDE_PLUGIN_ROOT}/scripts/anchor/upstream.py" add <git-url> --path <file>
```

Fetches the anchor from another repository and writes the local copy under
`specs/_anchors/`, with two tracking lines the author's own file does not carry. An anchor
brought in this way is a remote anchor: its copy is pinned to one version of its source.

```markdown
> Source: https://github.com/acme/policies.git specs/no_eval.md
> Pinned: abc1234def5678
```

**A pin is always a commit, never a branch.** A branch moves, and an anchor whose rules
changed under a project with no diff to read is exactly what pinning exists to prevent.

The file is a spec in Purlin's format that holds at least one rule, kept in a git repository.
Any other source, a text file, a description in words or a file with no rule, is refused and
nothing is written; the refusal names `purlin:anchor create <name>`, which writes the rules in
this project instead.

## sync

```bash
sh "${CLAUDE_PLUGIN_ROOT}/scripts/purlin_python.sh" "${CLAUDE_PLUGIN_ROOT}/scripts/anchor/upstream.py" sync [<name> | --all] [--check] [--json]
```

`--check` reports without writing, one line per anchor: `security_baseline: the pin abc1234
is behind its source, now 9f8e7d6. Run purlin:anchor sync security_baseline.` It exits 1 when a
pin is behind and 2 when a source could not be read. `purlin:drift` and `purlin:status` run the
same check and say an anchor is behind its source; neither pulls. Only `purlin:anchor sync`
pulls.

Without `--check`, sync rewrites the local copy, advances the pin and prints what moved:
`security_baseline: RULE-3 changed, RULE-6 added. Pin advanced from abc1234 to 9f8e7d6. Commit
it as anchor(security_baseline): sync (9f8e7d6), then run purlin:test.` It commits nothing:
commit the copy in one commit with the `anchor(<name>):` prefix, so the diff shows exactly
which rules moved.

## Changing a remote anchor's rule

**Never edit a remote anchor's rule in place.** The next sync overwrites it and the change is lost with
no trace. A change to the rule is a pull request against the source repository, made in a
checkout of it; once it merges, `sync` brings it here.

A rule that belongs only to this project goes in a local anchor of its own when it holds across
the whole project, and in the spec of each feature it holds for when it does not. The remote
anchor's copy stays untouched. A pulled rule that fails here is a problem to raise with its authors: the
project has no way to set a pulled rule aside.

## When you are done

Name the next step from the state:

- Anchor created: `→ Run: purlin:build <name>`, which writes tests that check the whole project
- Anchor added or synced, rules changed: `→ Run: purlin:test`, whose `Left to do` names the
  rules the change left to test or fix.
- Pin current and nothing moved: say so in one line, `→ Run: purlin:status`
- Anchor refused, its source not a spec: `→ Run: purlin:anchor create <name>`
