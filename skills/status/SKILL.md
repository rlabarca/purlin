---
name: status
description: Show every rule's cells and what blocks the gate
---

Show where every feature stands: how many of its rules meet the gate, what blocks the rest,
and what to do next. This skill writes nothing.

**Paths in this skill:** every `references/`, `templates/`, `scripts/` and `agents/` path below
is relative to the plugin root; see `references/purlin_commands.md#path-resolution`.

## Usage

```
purlin:status                   Every feature and anchor
```

Plain language reaches the same place: "where are we", "what is left", "show the board".

## Step 1: call the tool

```
sync_status()
```

## Step 2: print the table

The tool opens with `Purlin status: <project>, plugin <version>, gate <gate>`, then the table.
Every spec and every anchor gets a row, sorted attention first: the most rules short of the
gate at the top. Anchors carry `(anchor)` after the name. Columns exist only when the gate
creates the cell behind them, so a project at `passed` has no strong and no signed column.

The table is the dashboard's board, rendered as text: the same six columns, the same text in
each cell. A reader who has learned one has learned the other.

```
  Spec           Rules  Proofs                 Tests
  ──────────────────────────────────────────────────────────────────────
  billing           14  16 · 2 without a test  9 of 14 · 1 partial · 1 failing
  login (anchor)     8  8                      8 of 8
```

`Proofs` counts every proof line and appends `· <k> without a test` when a proof has nothing
tagged against it. `Tests` is `<passed> of <rules>`, then `· <k> partial` and `· <k> failing`
when either is not zero; `partial` means the tests pass on one operating system and not on
another. Under `strong` a `Strong` column follows, `<n> of <rules> · <strength>`; under
`signed` a `Signed` column follows that, `<n> of <rules>`.

Print the numbers `sync_status` returned. Never recount them: the command line and the
dashboard must show one answer from one computation.

## Step 3: print the summary line and what stands in the way

The summary is three lines: `<met> of <rules> rules meet the gate <gate>.`, then the buckets
the gate reaches in the tiles' own words and order (`Untested <n> · Failing <n> · Partial <n>
· Passing <n> · Strong <n> · Signed <n>`), then the feature and proof counts with whatever the
gate creates beside them. Print them with their denominators intact.

Anything the tool prints after the table and before the directives is its own: an anchor whose
pin is behind, uncommitted spec changes, and its warnings. Print them verbatim, or nothing
when the tool returned nothing.

## Step 4: name the next step

Print the `→` lines the tool returned and add none of your own. There is one `→ Next:` line,
computed from the lowest cell that blocks the gate, and one more line when the review list is
not empty:

| What blocks the gate | The line the tool prints |
|----------------------|--------------------------|
| A rule's spec status is `drafted` | `→ Next: run purlin:spec.` with the count |
| A rule has a failing test | `→ Next: run purlin:build.` with the count |
| A rule's tests pass on one operating system and not another | `→ Next: run purlin:build.` with the `partial` count |
| A rule has no test | `→ Next: run purlin:build.` with the count |
| A rule is waiting for the record that counts | `→ Next: run purlin:test --remote.` under `strong` and above, `→ Next: run purlin:test.` under `passed` |
| No audit has measured a rule | `→ Next: run purlin:audit.` with the count |
| A rule is weak | `→ Next: run purlin:build.` naming what each one is short of |
| A rule reads `manual test`, `manual audit` or `held`, or is unsigned or stale | `→ Next: run purlin:sign.` with the count |
| Every rule meets the gate | `→ Next: nothing is outstanding at gate <gate>.` |
| The review list is not empty | `→ Review list: <n> rules need a person. Run purlin:sign.` |
