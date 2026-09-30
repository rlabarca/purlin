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

The tool opens with `Purlin status: <project>, plugin <version>, gate <gate>`, then the table.
Every spec and every anchor gets a row, sorted attention first: the most rules with work left
at the top. Anchors carry `(anchor)` after the name. Columns exist only when the gate
creates the cell behind them, so a project at `passed` has no strong and no signed column.
The table is the dashboard's board, rendered as text: the same columns, the same text in
each cell. A reader who has learned one has learned the other.

```
  Spec               Rules           Proofs          Tests
  ─────────────────────────────────────────────────────────────────────────────────
  billing            14 (+6 shared)  22 · 2 no test  15 of 20 · 1 partial · 1 failing
  security (anchor)  6               6               6 of 6
```

`Rules` counts the spec's own rules, then ` (+<k> shared)` for those it proves from an anchor.
`Proofs` counts every proof line and appends `· <k> no test` when no test in the source carries
a proof's marker, run or not; at `passed` the column is there only where the project writes a proof line.
`Tests` is `<passed> of <rules>`, then `· <k> partial` and `· <k> failing` when either is not
zero; `partial` means the tests pass on one operating system and not on another. `Strong` reads
`<n> of <rules>`, then `· <strength>%` where strength was measured; `Signed` reads `<n> of <rules>`.

## Step 3: print the summary and `Left to do`

The tool ends on one sentence and `Left to do`, the words every command ends on in the terminal:

```
40 rules. 35 pass their tests. 30 are strong. 20 are signed.
Left to do:
  5 rules to audit: purlin:audit
  10 rules to sign: purlin:sign
```

The sentence names the steps up to the gate, each containing the next. `Left to do` holds one
line per kind of work, in the order it is done, with its count and its command. When nothing
is left, `Nothing left to do.` follows the sentence instead, at `signed` with the tag's push.
Print the sentence and the `Left to do` lines `sync_status` returned. Never recount them: the
command line and the dashboard must show one answer from one computation.

Anything the tool prints between the table and the sentence is its own: the specs that name
no files, an anchor whose pin is behind, uncommitted spec changes, its warnings and
`→ Run: purlin:init --update`. Print them verbatim, or nothing when the tool returned nothing.

## With a name

Naming a spec shows its rules and their standing. Match `specs/**/<name>.md`, then the name
as part of a spec file name; when several match, list them and ask which one, and when none
does, print the whole table. Read the spec, call `sync_status`, and print its path, its
header, and one line per rule with the cells the gate creates and the proof lines behind it:

```
specs/auth/login.md: 8 rules
  RULE-1  passed  strong  signed      PROOF-1  tests/test_login.py::test_rejects_bad_password
  RULE-3  no test                     PROOF-3  no test carries this marker
```

The next step is the Step 4 row for the first kind of work this spec's rules wait for.

## Step 4: name the next step

The next step is the first line of `Left to do`. Add no line of your own; a
`→ Run: purlin:init --update` the tool printed comes first.

| The first line after the sentence | Next step |
|-----------------------------------|-----------|
| `<n> rules to write a proof for`, or `to tie to their files` | `→ Run: purlin:spec` |
| `<n> test comments to correct` | `→ Run: purlin:build` |
| `<n> rules to fix`, `to write a test for` or `to strengthen` | `→ Run: purlin:build` |
| `<n> rules to test` | `→ Run: purlin:test` |
| `<n> rules to test on <systems>` | `→ Run: purlin:test --remote` |
| `<n> rules to audit` | `→ Run: purlin:audit` |
| `<n> rules to measure` | `→ Run: purlin:audit` |
| `<n> rules to test by hand`, `to sign`, or `the version to tag` | `→ Run: purlin:sign` |
| `Nothing left to do. Push the tag to release it: ...` | `→ Run: git push origin signed/<version>` |
| `Nothing left to do.` | None: every rule reached every step the gate asks. |
