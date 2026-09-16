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

Every feature and every anchor gets a row, sorted attention first: the most rules needing work
at the top. Anchors carry `(anchor)` after the name. Columns exist only when the gate creates
the cell behind them, so a project at `passed` has no strength and no signature column.

```
  Feature                    Rules   Spec             Tests                 Run
  ──────────────────────────────────────────────────────────────────────────────────
  billing                       14   12 ready         9 passed · 5 no test  ci · linux · 2h
  login (anchor)                 8   8 ready          8 passed             ci · linux · 2h
  export                         5   5 drafted        no test               none
```

Under `strong` two columns follow `Run`: `Strength`, the test strength as an integer percent
or `n/a` when no break engine is installed, and `Strong`, the rules whose strong cell is met
out of the rules total. Under `signed` a `Signed` column follows those two, with the stale
count beside it.

Print the numbers `sync_status` returned. Never recount them: the command line and the
dashboard must show one answer from one computation.

## Step 3: print the summary line and the operating systems

Print the summary line exactly as the tool returned it, with its denominators intact:
`<met> of <rules> meet the gate <gate>`. A percentage without the count it was taken over is
the thing to avoid.

When some proof carries `@env`, one line follows it naming each operating system and what it
still owes, for example `windows: no record yet`. Print it verbatim, or nothing when the tool
returned nothing: a project that scopes no proof has no such standing to report.

## Step 4: name the next step

Print the `→ Next:` directive the tool returned, then one closing line for the project as a
whole. The directive comes from the lowest cell a rule is blocked at:

| What blocks the gate | The line to print |
|----------------------|-------------------|
| A rule's spec status is `drafted` | `→ Next: purlin:spec <feature>` |
| A rule has no test, or a test failed | `→ Next: purlin:build <feature>` |
| A rule is weak | `→ Next: purlin:build <feature>` (the brief names what the break escaped) |
| A rule reads `code changed`, or its record is not from `ci` under `strong` or above | `→ Next: push; CI writes the record.` |
| A rule needs a person, is unsigned, stale or held | `→ Next: purlin:sign` |
| Every rule meets the gate | `→ Nothing is outstanding at gate <gate>.` |
