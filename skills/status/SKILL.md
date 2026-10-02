---
name: status
description: "Show where the project stands: whether the tests are met, whether it is signed, each rule's two cells, and what is left to do"
---

Show where every feature stands: whether the tests are met, whether this code is signed, how many
rules pass their tests, what is left to do, and what to do next. This skill writes no file you
commit; it refreshes the dashboard's data, which git ignores.

**Paths in this skill:** every `references/`, `templates/`, `scripts/` and `agents/` path below
is relative to the plugin root; see `references/purlin_commands.md#path-resolution`.

## Usage

```
purlin:status                   Every feature and anchor
purlin:status <name>            One spec: its rules and their cells
```

Plain language reaches the same place: "where are we", "what is left", "show the board".

## Step 1: call the tool

Get the status from the tool `mcp__plugin_purlin_purlin__sync_status`, passing `project_root`:
the top folder of the git checkout you are working in. Where the session lists it as a
deferred tool, load it with ToolSearch first. Where the session does not have it, run the
script, which prints the same status:

```bash
sh "${CLAUDE_PLUGIN_ROOT}/scripts/purlin_python.sh" "${CLAUDE_PLUGIN_ROOT}/scripts/run/purlin_status.py" --project-root .
```

Never read `.purlin/report-data.js` or `purlin-report.html` as the status: they hold what the
last command saw.

In a worktree the top folder is the worktree's own, since each checkout has its own results,
status and dashboard.

`No Purlin project root at <folder>: .purlin/config.json is not there. Run purlin:init.` means
this folder is not set up. Say so and name `purlin:init`. Never pass another folder to get an
answer.

## Step 2: print the two facts and the table

Print the status as the tool or the script printed it. Never rebuild it as a table of your own.
It opens on three lines, then the table:

```
Purlin status: labconnect, plugin <version>
Tests: not met
Sign-off: signed 0.1.0, 4 commits since

Spec                            Rules  Proofs          Tests
──────────────────────────────────────────────────────────────
Anchors
security_no_dangerous_patterns  8      21              8 of 8
Specs
billing                         14     22 · 2 no test  12 of 14 · 1 partial · 1 failing
login                           11     20              11 of 11
```

`Tests:` reads `met` when every rule passes its tests on the committed evidence, else `not met`.
`Sign-off:` reads `signed <version> at <sha7>`, `signed <version>, <n> commits since` or
`not signed`. `references/evidence_and_signoff.md` defines both.

The table has a row per spec, most work left first, the anchors under `Anchors` above the rest
under `Specs`. `Rules` counts the spec's rules. `Proofs` counts every proof line, then
`· <k> no test` where no test carries a proof's marker. `Tests` is `<passed> of <rules>`, then
`· <k> by hand`, `· <k> partial` and `· <k> failing` where not zero; `by hand` counts the rules
checked at sign-off, and `partial` means the tests pass on one operating system and not another.
A `Strong` column shows only where the audit read a rule, as `<strong> of <n>`: of the rules
that pass their tests and have a tested proof, the ones it found strong. An anchor's cell reads
one word, `weak`, `out of date` or `spot-checked`, or nothing: no bug is planted for an anchor's
rule.

## Step 3: print the summary and `Left to do`

The tool ends on one sentence and `Left to do`, the words every command ends on in the terminal:

```
40 rules. 35 pass their tests. The audit found 30 of 35 rules strong (85%): 30 strong, 2 weak, 3 spot-checked.
Left to do:
  3 rules to write a test for: purlin:build
  2 rules to test: purlin:test
```

The sentence counts the rules that pass their tests, then the share the audit found strong where
it read any. `Left to do` holds one line per kind of work, in the order it is done, with its count
and its command. Print the lines the status holds. Never recount them: the command line and
the dashboard must show one answer from one computation.

Anything the tool prints between the table and the sentence is its own: a rule of an anchor that
passes with nothing to check, a spec whose scope names files not written yet, an anchor behind its
source, each test comment to correct, its warnings and `→ Run: purlin:init --update`. Print them
as they are, or nothing when the tool returned nothing. Where a warning says a number is written
twice, follow `Renumbering` in `skills/spec/SKILL.md`.

## With a name

Naming a spec shows its rules and their standing. Match `specs/**/<name>.md`, then the name
as part of a spec file name; when several match, list them and ask which one, and when none
does, print the whole table. Read the spec, get the status as Step 1 says, and print its path, its
header, and one line per rule with its two cells and the proof lines behind it:

```
specs/auth/login.md: 8 rules
  RULE-1  passed  strong                PROOF-1  tests/test_login.py::test_rejects_bad_password
  RULE-3  no test                       PROOF-3  no test carries this marker
  RULE-5  checked at sign-off  checked at sign-off   PROOF-6  a hand check
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
| `<n> slow proofs to run` | `→ Run: purlin:test --all` |
| `<n> rules to test on <systems>` | `→ Run purlin:test on <systems>`. It is an instruction, not a command line: do as `skills/test/SKILL.md`, Step 5 says |
| `<n> features whose results are not committed` | `→ Run: purlin:test --commit` |
| `Every rule passes its tests on the committed evidence. To sign it: purlin:sign` | `→ Run: purlin:sign`, when a person chooses to sign |
