---
name: status
description: Show every rule's state and the project's test strength
---

Show where every feature stands: how many of its rules are in each state, its test strength,
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
at the top. Anchors carry `(anchor)` after the name. Columns exist only when the artifact
behind them exists, so a project at the `tested` gate has no records or approvals column.

```
  Feature                    Rules   Tested   Recorded   Approved   strength
  ─────────────────────────────────────────────────────────────────────────
  billing                       14        9          9          0        62%
  login (anchor)                 8        8          8          6        81%
  export                         5        0          0          0        n/a
```

`strength` is the test strength as an integer percent, or `n/a` when no break engine is
installed. Print the numbers `sync_status` returned. Never recount them: the command line and
the dashboard must show one answer from one computation.

## Step 3: print the summary line and the operating systems

Print the summary line exactly as the tool returned it, with its denominators intact. A
percentage without the count it was taken over is the thing to avoid.

When some proof carries `@env`, one line follows it naming each operating system and what it
still owes, for example `windows: no record yet`. Print it verbatim, or nothing when the tool
returned nothing: a project that scopes no proof has no such standing to report.

## Step 4: name the next step

Print the `→` directives the tool returned, then one closing line for the project as a whole:

| What the table shows | The line to print |
|----------------------|-------------------|
| A rule is Drafted | `→ Run: purlin:spec <feature>` |
| A rule is Proof ready | `→ Run: purlin:build <feature>` |
| Every rule Tested, no record | `→ Run: purlin:verify` |
| Rules waiting on a person | `→ Run: purlin:review` |
| A rule is Stale | `→ Run: purlin:review <feature>` |
| Only `re-verify pending` remains | `→ Push; CI clears it.` |
