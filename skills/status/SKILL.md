---
name: status
description: Show every rule's cells and what blocks the gate
---

Show where every feature stands: how many rules reached each step, what is left to do, and
what to do next. This skill writes nothing.

**Paths in this skill:** every `references/`, `templates/`, `scripts/` and `agents/` path below
is relative to the plugin root; see `references/purlin_commands.md#path-resolution`.

## Usage

```
purlin:status                   Every feature and anchor
purlin:status <name>            One spec: its rules and their cells
```

Plain language reaches the same place: "where are we", "what is left", "show the board".

## Step 1: call the tool

Call `sync_status` with `project_root` set to the project root, the top folder of the git checkout.

## Step 2: print the table

The tool opens with `Purlin status: <project>, plugin <version>, gate <gate>`, then the table: a
row per spec, most work left first, the anchors under `Anchors` above the rest under `Specs`, and
`Strong` only where the audit found a rule strong or weak. It is the dashboard's board as text.

```
  Spec                            Rules  Proofs          Tests
  ─────────────────────────────────────────────────────────────
  Anchors
  security_no_dangerous_patterns  8      91              8 of 8
  Specs
  billing                         14     22 · 2 no test  12 of 14 · 1 partial · 1 failing
  login                           11     20              11 of 11
  ─────────────────────────────────────────────────────────────
```

`Rules` counts the spec's rules. `Proofs` counts every proof line, then `· <k> no test` where no
test carries a proof's marker; at `passed` it shows only where a proof line is written. `Tests` is
`<passed> of <rules>`, then `· <k> partial` and `· <k> failing` where not zero; `partial` means
the tests pass on one operating system and not another. `Strong` reads `<n> of <rules>` the audit
found strong, then `· <strength>%` where measured.

## Step 3: print the summary and `Left to do`

The tool ends on one sentence and `Left to do`, the words every command ends on in the terminal:

```
40 rules. 35 pass their tests. The audit found 30 strong and 2 weak.
Left to do:
  3 rules to write a test for: purlin:build
  2 rules to strengthen: purlin:build
```

The sentence counts the rules that pass their tests, then what the audit found where it read any.
`Left to do` holds one line per kind of work, in the order it is done, with its count and its
command. When nothing is left, one line naming the release step follows the sentence instead.
Print the sentence and the `Left to do` lines `sync_status` returned. Never recount them: the
command line and the dashboard must show one answer from one computation.

Anything the tool prints between the table and the sentence is its own: the specs that name
no files, an anchor whose pin is behind, uncommitted spec changes, its warnings and
`→ Run: purlin:init --update`. Print them verbatim, or nothing when the tool returned nothing.
Where a warning says a number is written twice, follow `Renumbering` in `skills/spec/SKILL.md`.

## With a name

Naming a spec shows its rules and their standing. Match `specs/**/<name>.md`, then the name
as part of a spec file name; when several match, list them and ask which one, and when none
does, print the whole table. Read the spec, call `sync_status`, and print its path, its
header, and one line per rule with the cells the gate creates and the proof lines behind it:

```
specs/auth/login.md: 8 rules
  RULE-1  passed  strong              PROOF-1  tests/test_login.py::test_rejects_bad_password
  RULE-3  no test                     PROOF-3  no test carries this marker
```

The next step is the Step 4 row for the first kind of work this spec's rules wait for.

## Step 4: name the next step

The next step is the first line of `Left to do`. Add no line of your own; a
`→ Run: purlin:init --update` the tool printed comes first.

| The first line after the sentence | Next step |
|-----------------------------------|-----------|
| `<n> specs to repair` or `<n> rules to write a proof for` | `→ Run: purlin:spec` |
| `<n> test comments to correct` | `→ Run: purlin:build` |
| `<n> rules to fix`, `to write a test for` or `to strengthen` | `→ Run: purlin:build` |
| `<n> rules to test` | `→ Run: purlin:test` |
| `<n> rules to test on <systems>` | `→ Run: purlin:test --remote` |
| `Nothing left to do. To release a version: purlin:test --release` | `→ Run: purlin:test --release` |
| `... purlin:test --release, then purlin:sign` | `→ Run: purlin:test --release`, then `purlin:sign` |
| `Nothing left to do. Push the tag to release it: ...` | `→ Run: git push origin <tag>` |
