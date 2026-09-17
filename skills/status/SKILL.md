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
Every feature and every anchor gets a row, sorted attention first: the most rules short of the
gate at the top. Anchors carry `(anchor)` after the name. Columns exist only when the gate
creates the cell behind them, so a project at `passed` has no strength and no signature column.

```
  Feature      Rules  Spec                   Tests                            Run
  ────────────────────────────────────────────────────────────────────────────────────
  billing         14  12 ready · 2 drafted   9 passed · 0 failing · 5 no test  ci linux
  login (anchor)   8  8 ready · 0 drafted    8 passed · 0 failing · 0 no test  ci linux
  export           5  0 ready · 5 drafted    0 passed · 0 failing · 5 no test  none
```

Under `strong` two columns follow `Run`: `Strength`, the test strength as an integer percent
or `n/a` when no break engine is installed, and `Strong`, `<n> of <m>` rules whose strong cell
is met. Under `signed` a `Signed` column follows those two, in the same `<n> of <m>` form.

Print the numbers `sync_status` returned. Never recount them: the command line and the
dashboard must show one answer from one computation.

## Step 3: print the summary line and what stands in the way

The summary is two lines. The first is `<met> of <rules> rules meet the gate <gate>.` The
second carries the feature count and, as the gate creates them, the failing count, the minimum
test strength, the risk the model review starts at, how many rules need a person, how many are
held, the risk a signature starts at, and how many signatures are stale. Print both with their
denominators intact: a percentage without the count it was taken over is the thing to avoid.

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
| A rule has a failing test, or no test | `→ Next: run purlin:build.` with the count |
| A rule is waiting for the record that counts | `→ Next: push the branch.` under `strong` and above, `→ Next: run purlin:test.` under `passed` |
| A rule is weak | `→ Next: run purlin:build.` naming what each one is short of |
| A rule reads `manual test`, `manual audit` or `held`, or is unsigned or stale | `→ Next: run purlin:sign.` with the count |
| Every rule meets the gate | `→ Next: nothing is outstanding at gate <gate>.` |
| The review list is not empty | `→ Review list: <n> rules need a person. Run purlin:sign.` |
