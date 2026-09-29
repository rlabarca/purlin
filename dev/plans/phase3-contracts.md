# Phase 3 contracts: what lanes produce and consume, word for word

Written by the planning agent on 2026-09-29 for decisions 94, 95 and 96. Every agent builds to
this file and none chooses. `phase3-plan.md` says who owns what; each brief under
`phase3-lanes/` repeats the parts its lane needs.

The owner answered every question of `phase3-plan.md` section 8, 1 to 25, on 2026-09-29
(decision 97 of `three-levels.md`), and the words below are the words chosen. A mark `(OQ<n>)`
names the question whose answer a line carries. No question is open.

In the strings below, `<feature>`, `<RULE-N>`, `<PROOF-N>`, `<n>`, `<version>`, `<System>`
(`Windows`, `macOS`, `Linux/Unix`) and `<path>` are filled in; everything else is literal.

## C1. Interfaces landed before the fan-out

These land in P1 or P2 (plan section 3), alone. No lane changes their names or shapes.

### C1.1 The breaks, called with the scope alone (P1)

- P1: `mutation.run_breaks(project_root, engine, scope_by_feature, tests_by_rule=None)`. The
  fourth argument is accepted and ignored. `scripts/run/purlin_run.py` calls
  `run_breaks(project_root, engine, scope_by_feature(features, selected))` and its
  `tests_by_rule()` is deleted.
- Lane `mutation` then deletes the fourth parameter, so the final signature is
  `run_breaks(project_root, engine, scope_by_feature)`.

### C1.2 The engine's answer (lane `mutation` produces, lane `run` consumes)

```
{"engine": "<stryker | stryker_net | mutmut | none>",
 "available": <bool>,
 "reason": "<sentence, or ''>",
 "features": {"<feature>": {"scope_score": {"score": <int or null>,
                                            "killed": <int>, "survived": <int>},
                            "missing": "<sentence, or ''>"}},
 "log": "<text>"}
```

- The `rules` key under each feature goes, with `attribution`. `scope_score` keeps its name
  and shape.
- `missing` is the sentence saying why the engine the settings selected measured nothing for
  that feature, and `''` otherwise:
  - The selected engine is not installed: `engine` names that engine (not `none`),
    `available` is false, `reason` is its not-installed sentence (C3.2), and every feature's
    `missing` is that same sentence.
  - One feature's invocation ran past the time limit: `available` is true, that feature's
    score is null and its `missing` is the timeout sentence (C3.2).
  - The engine ran and wrote no report for a feature: that feature's `missing` is the
    no-report sentence (C3.2; OQ10).
  - A feature whose spec names no code files is not handed to the engine, as today, and has no
    `missing`: lane `core` reads that case from the spec itself (C4.2; OQ10).
  - The engine cannot run on this operating system (`runs_here` is false, C1.3): `engine` is
    `none`, `available` is false, `reason` is the not-on-this-system sentence (C3.2; OQ12),
    and every `missing` is `''`: it counts as no engine.
  - `mutation_engine` is `none`, or names no engine: as today, and every `missing` is `''`.
- Lane `run` reads `features[f].get('missing') or ''`, so it builds against either shape.

### C1.3 Can this engine run here (P1)

`mutation.runs_here(engine, os_name=None) -> bool`: false when `engine == 'mutmut'` and the
system is Windows (`os_name == 'windows'`, or with no `os_name` given, `os.name == 'nt'`);
true otherwise. Consumed by lane `mutation` (mutmut's run), lane `scaffold` (whether setup asks
the breaking question) and lane `update` (the same in the upgrade).

### C1.4 One program start of that form (P1)

`scripts/run/mutation/__init__.py` `execute` starts the engine with
`subprocess.Popen([*command], cwd=..., ...)`, the form `purlin_run._run` and `remote.py`
already use. Lane `anchors` then holds every `subprocess.Popen(` to a list written in place.

### C1.5 The comments that name nothing (P1)

`marker_problems(scan, features) -> list[str]`, `NAMES_NOTHING` and `RULE_HAS_PROOFS` move
from `scripts/run/reports.py` into `scripts/mcp/purlin/markers.py`, unchanged.
`scripts/run/reports.py` imports the three names from `markers`, so `reports.marker_problems`
still answers. Lane `core` calls `markers.marker_problems` from the payload.

### C1.6 The spec mistakes (P1 stub, P2 body)

`specs.spec_mistakes(project_root, features) -> list[str]`. P1 lands it returning `[]`, and
`payload.build_payload` appends each line it returns to `warnings`, after the lines for
unnumbered rules, in the order returned. P2 fills it (C3.3). `fingerprint` is imported inside
the function, since `fingerprint` imports `specs`.

### C1.7 The host line and the gate line (P1)

- `scripts/run/workflow.py`: `UNKNOWN_HOST = 'This git host cannot run tests remotely.
  Everything on this machine works.'` (decision 96). `prerequisites()` returns it as today.
- `scripts/init/scaffold.py`: `NOT_A_GATE = 'purlin: "%s" is not a gate; reading it as %s.'`,
  used by setup's `main` in place of its inline string. Lane `update` prints it (Q18).

### C1.8 The settings template (P1)

`templates/config.json` holds six keys, in this order: `gate`, `mutation_engine`,
`min_strength`, `audit_parallel`, `tests`, `ci`. Setup writes a project's settings in the order
`version`, `gate`, `mutation_engine`, `min_strength`, `audit_parallel`, `tests`, `ci`, with
`version` read from the plugin's `VERSION` file, as today. The bump script's derived locations
are `.claude-plugin/plugin.json` and `.purlin/config.json`.

### C1.9 The settings file that cannot be read (P2; OQ1)

`config_engine.config_problem(project_root) -> str | None`: the sentence C3.4 when
`.purlin/config.json` exists and cannot be read, and None when it reads or does not exist.
"Cannot be read" means any of: not UTF-8, not valid JSON, JSON that is not an object, or an
`OSError` on open. Consumers, each in its own lane:

| Lane | Where | What it does with the sentence |
|---|---|---|
| `core` | `status.sync_status` | returns the sentence alone, no table |
| `run` | `purlin_run.settings_stop` | prints it, writes nothing, exits 1 |
| `settings` | every tool of the server; `update_config` | the tool answers it; a write is refused |
| `host` | `remote.py`, where it reads the settings | prints it, exits 1 |
| `scaffold` | setup, before anything is written | prints it, writes nothing, exits 1 |
| `update` | the upgrade, before anything is written | prints it, writes nothing, exits 1 |
| `signing` | `sign.py` `main`, after the command line is read and before anything else is read or written | prints it, writes nothing, exits 1 |
| `package` | `package.py` `main`, after the command line is read and before anything else is read or written (`--check` included) | prints it, writes nothing, exits 1 |
| `drift` | `drift.drift`, before anything is read | returns the sentence alone as the tool's text, in place of the JSON, and writes nothing (a tool has no exit code) |
| `review` | `ai_audit.py` `main`, the audit reader, after the command line is read and before the payload is built | prints it, writes nothing, exits 1 |

`markers.load_config` keeps its own reading: a run stops in `settings_stop` before it asks.
Each lane above adds one rule, or one proof under an existing rule where one already says what
the command does when it cannot start, to the spec it owns, with a test whose settings file
holds a trailing comma.

### C1.10 The unknown rule (P2; OQ15)

`scripts/review/sign.py` `NOT_A_RULE` holds C3.6's line as a `%`-format string with three
values (feature, rule, feature), and P2 adds beside it `def not_a_rule(feature, rule) -> str`,
which returns that line filled in. Every print of the
line, P2's own and each lane's, calls `sign.not_a_rule(feature, rule)` and never formats
`sign.NOT_A_RULE` itself. Lane `signing` prints it last, above the summary; lane `review`
imports `not_a_rule` from `scripts/review/sign.py` and prints `sign.not_a_rule(feature, rule)`
from `ai_audit.py --rule`.

### C1.11 Setup's line for an engine that cannot run here (P2; OQ12)

`scripts/init/scaffold.py`: `NO_ENGINE_HERE = 'Mutation testing is off: mutmut does not run on Windows, so the AI audit alone judges test strength.'`
Lane `scaffold` prints it from setup and lane `update` from the upgrade, each where
`mutation.runs_here(engine)` is false, in place of `NO_ENGINE`.

### C1.12 The systems a runner file names (P2; decision 97)

`scripts/run/workflow.py`: `foreign_tags(env_tags, host_os) -> list[str]`, the `@env` tags,
lower-cased and sorted, that name a system other than `host_os` (the machine running setup or
the upgrade, `evidence.host_os()`). `wanted()` computes its foreign set through it, unchanged in
behaviour. P2 adds it and changes nothing else in the file. Lanes `scaffold` and `update` hand
`foreign_tags(tags, evidence.host_os())` to `render_workflow` and `runners_for` in place of
every tag, so the runner file names one job per system some proof is tagged for that this
machine is not (scaffold RULE-13 already writes the file for that reason alone; RULE-15 and host
RULE-19 are reworded to it, C14). Lane `host` owns the rest of `workflow.py`.

## C2. Kinds of `Left to do`

`scripts/mcp/purlin/summary.py` `KINDS`, final order (lane `core` owns it):

| # | Kind | One / many | Command | Carried by |
|---|---|---|---|---|
| 1 | `no_proof` | as today | `purlin:spec` | a rule |
| 2 | `to_correct` (OQ3) | `test comment to correct` / `test comments to correct` | `purlin:build` | the project |
| 3 | `to_fix` | as today | `purlin:build` | a rule |
| 4 | `no_test` | as today | `purlin:build` | a rule |
| 5 | `to_test` | as today | `purlin:test` | a rule |
| 6 | `to_test_remote` | as today | `purlin:test --remote` | a rule |
| 7 | `to_test_by_hand` | as today | `purlin:sign` | a rule |
| 8 | `to_audit` | as today | `purlin:audit` | a rule |
| 9 | `to_measure` (OQ9) | `rule to measure` / `rules to measure` | `purlin:audit` | a rule |
| 10 | `to_strengthen` | as today | `purlin:build` | a rule |
| 11 | `no_scope` (when it counts: OQ10, below) | as today | `purlin:spec` | a rule |
| 12 | `to_sign` | as today | `purlin:sign` | a rule |
| 13 | `to_tag` | as today | `purlin:sign` | the project |

- `to_correct` (Q22; OQ3): its count is the number of lines
  `markers.marker_problems` returns over the test files the settings' suites name, at every
  gate: a comment naming something no spec has (`NAMES_NOTHING`) and a comment naming a rule
  that has proofs (`RULE_HAS_PROOFS`), since both fail the run. No rule carries it. The terminal line reads
  `  1 test comment to correct: purlin:build` for one and
  `  <n> test comments to correct: purlin:build` for any other count. The payload item's
  `text` follows the same rule as every kind (`summary._words`): `"1 test comment to correct"`
  for one, `"<n> test comments to correct"` otherwise, so the item is
  `{"kind": "to_correct", "count": 1, "text": "1 test comment to correct", "command": "purlin:build"}`
  for one and `{"kind": "to_correct", "count": 3, "text": "3 test comments to correct", "command": "purlin:build"}`
  for three. `to_tag` appears only when kinds 1 to 12 are all zero, so such a comment holds
  back the signed tag, as any other line does (decision 75).
- `to_measure` (Q37, OQ9): a rule whose strong cell reads `weak` only because the breaking was
  on and its feature's `audit.mutation.missing` is not empty. The line reads
  `  1 rule to measure: purlin:audit` for one and `  <n> rules to measure: purlin:audit`
  otherwise.
- `no_scope` (OQ10): as today at `signed`; in addition, at `strong` and `signed` with
  `mutation_engine` not `none`, a rule whose strong cell reads `weak` only because its spec
  names no code files (C4.2) counts here and not under `to_measure` or `to_strengthen`.
- A rule waiting only on a proof tagged for another system, whose test was skipped here, is
  `to_test_remote`; a proof, tagged or not, with no test tied to it makes the rule `no_test`
  (Q7, Q20).

## C3. Printed lines

### C3.1 Settled by a decision or a reading

| Id | Line | Printed by | Source |
|---|---|---|---|
| L1 | `This git host cannot run tests remotely. Everything on this machine works.` | setup, where the remote names a git host Purlin cannot use, on a line of its own right after `Gate <gate>. Suites <names>.`, which then names no git host (OQ7); the upgrade, through `prerequisites()`, as today | decision 96 (P1 the words, `scaffold` the placement) |
| L2 | `No git host found.` | setup, where the project has no remote, on a line of its own right after `Gate <gate>. Suites <names>.`, which then names no git host (OQ7); the upgrade keeps `No git remote, so there is no runner to read this workflow. Add one with: git remote add origin <url>` | decision 96 |
| L3 | `purlin: "<answer>" is not a gate; reading it as <gate>.` where `<gate>` is the project's own default | setup (today), the upgrade (new) | Q18 |
| L4 | `This project was set up by an older Purlin and not upgraded, so nothing ran. Run purlin:init --update.` | the run | exists; Q19 moves its proofs |
| L5 | `  1 test comment to correct: purlin:build` / `  <n> test comments to correct: purlin:build` | every ending, in C2's place (OQ3) | Q22 |
| L6 | `→ Run: git show signed/<version>:.purlin/evidence/package/<version>.json` | the export skill's closing row for a package that fails its fingerprint | Q52 |
| L7 | `Nothing left to do.` | the build skill's ending for a finished project at `passed` and at `strong` | decision 76, Q62 |
| L8 | `WARNING: 1 line under ## Rules in <path> is not numbered; a rule is `- RULE-N: <text>`. Run purlin:spec <feature>.` (singular) / `WARNING: <n> lines under ## Rules in <path> are not numbered; a rule is `- RULE-N: <text>`. Run purlin:spec <feature>.` | the status | plural fixed (P2); the closing ` Run purlin:spec <feature>.`, OQ2 |
| L9 | `1 spec file carries tags this release does not read (...)` (singular); the plural stays | the status | plural fixed (P2) |

The words `Git host not read from a remote` leave setup's summary line: where no git host is read
the line names none.

### C3.2 The breaking tool's reasons (lane `mutation` writes them, lane `run` prints them)

Existing, kept word for word:
- `mutmut is not installed: run "pip install mutmut"`
- `stryker is not installed: run "npm install --save-dev @stryker-mutator/core"`
- `dotnet stryker is not installed: run "dotnet tool install -g dotnet-stryker"`

OQ11, in place of today's `dotnet is not installed, so no engine breaks C# code` and
`the engine timed out after <seconds> s, so the breaks it made are partial and measure nothing: raise --arm-timeout to give it longer`:
- .NET missing: `dotnet is not installed: install the .NET SDK, then run "dotnet tool install -g dotnet-stryker"`
- time limit: `the engine timed out after <seconds> s, so the breaks it made measure nothing: run purlin:audit --arm-timeout <seconds> to give it longer`
  (the first `<seconds>` is the limit used; the second is written literally as `<seconds>`).
  `purlin:audit` takes `--arm-timeout <seconds>`, how long the breaking tool
  may run for one feature, 3600 by default, and passes it to the run script, which already
  reads it. Lane `skills-run` adds it to the audit skill's usage block and Step 1; lane `words`
  adds `[--arm-timeout <seconds>]` to the `purlin:audit` row of `references/purlin_commands.md`
  and the usage line to its usage block. **The usage line** (this is its one statement; every
  brief quotes it character for character): the syntax, then exactly two spaces, then the
  purpose, with single spaces everywhere else:

  ```
  purlin:audit --arm-timeout <seconds>  Give the breaking tool longer per feature
  ```

  The audit skill's usage block carries it as it stands, starting in the first column as the
  block's other lines do. `references/purlin_commands.md`'s usage block carries it after the
  two spaces every line of that block starts with. The syntax is longer than the column the
  other lines of both blocks pad to, as `purlin:sign <feature> [RULE-N ...]` is, so it is not
  padded.

OQ12, Python's breaking tool on Windows:
- the run: `mutmut does not run on Windows, so test strength is not measured here and the AI audit alone decides`
- setup and the upgrade, in place of `NO_ENGINE` for a pytest project on Windows:
  `Mutation testing is off: mutmut does not run on Windows, so the AI audit alone judges test strength.`

OQ10:
- no report: `<engine> ran and wrote no report: run purlin:audit again`,
  where `<engine>` is `mutmut`, `stryker` or `dotnet stryker`.

The run prints `purlin: <reason>` once for any answer whose `reason` is not empty, installed or
not (today only an installed engine's reason is printed), and `purlin: <missing>` once for each
distinct `missing` sentence not already printed.

### C3.3 Spec mistakes (P2 writes them; OQ2)

One line each, printed by the status beside the table and so by every run and every audit,
shown as a notice on the dashboard and copied into the evidence package's `warnings`:

| Mistake | Line |
|---|---|
| a `> Scope:` entry that finds no tracked file | `<feature>: > Scope: names <entry>, which finds no file in git. Run purlin:spec <feature>.` |
| two specs with one name | `<path1> and <path2> are both named <feature>; only <path1> is read. Rename one: git mv <path2> <the folder of path2>/<new name>.md` |
| a rule number written twice | `<feature>: <RULE-N> is written twice; the second is read. Run purlin:spec <feature>.` |
| a line under `## Proof` that cannot be read | `<feature>: a line under ## Proof cannot be read: <the line, cut to 60 characters>. Run purlin:spec <feature>.` |
| a first heading naming another feature | `<feature>: the first line names <other>, but the file is <feature>.md, so it is read as <feature>. Run purlin:spec <feature>.` |

- `<path1>` is the spec the reader keeps (the walk-order winner, as today) and `<path2>` the one
  it drops. In the second line `<the folder of path2>` is filled in (for example
  `specs/admin`) and `<new name>` is written literally, so the line reads
  `specs/auth/login.md and specs/admin/login.md are both named login; only specs/auth/login.md is read. Rename one: git mv specs/admin/login.md specs/admin/<new name>.md`.
- A spec whose every scope entry finds nothing prints only the existing line for that case, not
  one line per entry.
- A doubled rule number keeps one entry in the rule order, so every count agrees.
- "Names another feature" means a first line `# Feature: <other>` or `# Anchor: <other>` with
  `<other>` not the file's stem. A first line of neither form is not warned of.

### C3.4 A settings file that cannot be read (P2; OQ1)

`.purlin/config.json cannot be read: <cause>. Fix the file by hand; nothing ran and nothing was saved.`

`<cause>` is, in order of the first that applies: `it is not UTF-8 text`;
`<JSON message> at line <n>` from the JSON reader's own message and line (for example
`Expecting ',' delimiter at line 4`); `it holds a <list | string | number> where an object belongs`;
the operating system's own message for an open that failed.

`purlin:test`'s instructions direct the line to
`→ Fix the settings file by hand, then run: purlin:test` (lane `skills-run`).

### C3.5 The settings tool (lane `settings`; OQ8)

| When | The tool answers |
|---|---|
| a save failed | `The setting was not saved: <cause>.` |
| a write with no value | `A change needs a value; nothing was saved.` |
| a value not accepted for a known setting | `"<value>" is not accepted for <key>; it takes <accepted>. Nothing was saved.` |
| a write of `version` | `version is written by purlin:init from Purlin's own version; nothing was saved.` |
| a read of a key that is absent or null | the JSON `{"<key>": null}`, indented as a found key is (Q70; technical) |

`<accepted>` per key, joined `, ` and ` or `: `gate` takes `passed, strong or signed`;
`mutation_engine` takes `none, auto, mutmut, stryker or stryker_net`; `min_strength` takes
`a whole number from 0 to 100, or null`; `audit_parallel` takes `a whole number from 1 to 16`;
`tests` takes `a list`; `ci` takes `github, azure or none`. An explicit `null` is accepted for
`min_strength` alone. Keys Purlin does not know are written as today. The tool does not write
`version`.

### C3.6 Signing and the audit reader (P2 and lanes `signing`, `review`)

- Unknown rule (OQ15), printed last above the summary by signing, and by the audit reader for
  `--rule`: `<feature> <RULE-N> is not a rule any spec has. Run purlin:status <feature> to see its rules.`
- git failed to write the tag (OQ16): `No tag: git could not write signed/<version>: <git's own message, first line>.`
  Exit 1. The line for a tag that already exists is no longer printed for this case.

### C3.7 The run (lane `run`)

| Id | When | Line |
|---|---|---|
| R1 | a rule some of whose proofs have no test (OQ4) | `<feature> <RULE-N> has no test for <PROOF-N>[, <PROOF-M>...]. Run purlin:build <feature>.` |
| R2 | a rule none of whose proofs has a test | `<feature> <RULE-N> has no test. Run purlin:build <feature>.` (unchanged) |
| R3 | proofs tagged for another system, on a person's machine (OQ20) | one line per system: `1 proof needs <System>; this machine is <System>. Run purlin:test --remote.` / `<n> proofs need <System>; this machine is <System>. Run purlin:test --remote.` A proof tagged for another system with no test tied to it is not counted here (it has R1 or R2 instead). |
| R4 | no test command, tools recognised (OQ5) | `No test command is set in .purlin/config.json, so nothing ran.`, then for each tool in the fixed order `Suggested for <name>: <run>` followed by that tool's needs line where it has one, then `Suggested tests setting: <the entries as one JSON array on one line>` |
| R5 | no test command, nothing recognised | unchanged |
| R6 | the settings file cannot be read | C3.4 |
| R7 | the `audit_parallel` warning (Q10) | printed once, beside the status table, and no longer as the run's first line |

The Python entry's `run` on Windows (OQ6): `py -3 -m pytest` in place of
`python3 -m pytest`, the rest of the command unchanged; every other system keeps `python3`.

### C3.8 The runner (lane `host`)

| When | Line |
|---|---|
| no branch can be read (OQ22) | `No branch could be read from the git host or from git, so the results were not committed.` |
| a run on a ref that is neither a `run/*` branch nor a `signed/*` tag (OQ23) | `This run is on <ref>, which is neither a run branch nor a signed tag: the tests ran and nothing is written.` |
| a signed tag | `Tag run: nothing is written. This run reruns the tests on <ref>.` (unchanged) |

### C3.9 Near misses (lane `reports`; OQ18)

Where the nearest id is a rule with exactly one proof, the fix names that proof and the `why`
reads ``` `RULE-30` is one character from `RULE-3`, which login has; a comment names its one proof, `PROOF-3` ```
(ids and feature filled in). A rule with no proof keeps today's fix and why. A rule with two or
more proofs gives no near miss.

### C3.10 The audit's notes (lane `review`; OQ17)

After the findings in `ai_audit.py --feature <f> --rule <RULE-N>`, with no heading and no blank
line: each note on a line of its own, indented two spaces as the findings are, reading
`  Note: <the note>`. Nothing is printed where the entry has no notes.

## C4. Evidence format 5 (lane `run` writes `references/formats/evidence_format.md`)

`> Format-Version: 5`. The schema string stays `purlin-evidence/2`.

1. A `local` section carries no `hostname`. A `ci` section carries `hostname`, the name the host
   lent the runner, beside `machine` `remote runner, <System>` (Q21).
2. `audit.mutation` is `{"engine", "score", "at", "commit"}` plus an optional `"missing"`: the
   sentence of C1.2, present only when the selected engine measured nothing for the feature
   and `score` is null. Two entries that differ in `missing` alone are different (`merge_audit`).
3. A `ci` section lists, in `proofs`, only the proofs tagged `@env(<this runner's system>)`,
   and in `rules` only the rules those proofs prove (decision 95).
4. A proof tagged `@env` for a system other than the section's reads `not run` in that section
   whatever its tied test did there (decision 95: a test carrying a Mac proof's marker and a
   Windows proof's marker runs on the Mac and proves only the Mac proof).
5. A rule's word in `rules`: `failed` where a tied test of a proof that could run here failed;
   else `no test` where any proof that is not `@manual`, tagged or not, has no test tied to it
   (Q20, Q7); else `not run` where a tied test did not run or a proof is tagged for another
   system; else `passed`. A rule whose proofs are all `@manual` reads `passed`; a rule with no
   proof reads as today.

### C4.1 How the rule's cells read the evidence (lane `core`)

- A section answers only for the proofs it lists: a proof absent from a section's `proofs` is
  neither passed nor failed nor `not run` there (decision 95).
- The passed cell reads `partial` only where two systems that each have a current section
  disagree. A system a proof is tagged for with no current section makes the cell `not run`
  with `missing_env` naming it and the reason `<os>: no run yet`, as `_section_passes` already
  gives (Q7).
- Before the pass check, and after the failure check: where a proof that is not `@manual` has
  no marker tied to a test and no test listed in any current section, the cell reads `no test`
  with the reason `no test for <PROOF-N>[, <PROOF-M>]` (OQ4). Order:
  `failed` > `no test` > `not run` / `partial` > `passed`.

### C4.2 The strong cell (lane `core`)

With `mutation_engine` not `none`, where the feature's `audit.mutation.score` is null and its
`missing` is not empty, the strong cell reads `weak` with the reason `strength not measured:
<missing>` after any findings (OQ9). An engine that cannot run here answers `none` (C1.2), so
the cell reads `strong` on the audit alone with `no mutation score measured`, as today.

OQ10 (decision 94, "nothing measured means not strong"): with
`mutation_engine` not `none` and the gate `strong` or `signed`, a rule of a feature spec that
names no code files (`fingerprint.incomplete_reason` is not None; an anchor is never such a
spec) reads `weak` with the reason
`strength not measured: the spec names no code files: run purlin:spec <feature>`, and counts
under `no_scope` (C2).

## C5. Package format 4 (lane `package` writes `references/formats/package_format.md`)

`> Format-Version: 4`: the table of `left` kinds gains `to_correct` (C2 row 2; OQ3) and
`to_measure` (C2 row 9; OQ9). The two rows, in the table's own form, each where C2 puts its
kind:

```
| `to_correct` | `1 test comment to correct`, `<n> test comments to correct` | `purlin:build` |
| `to_measure` | `1 rule to measure`, `<n> rules to measure` | `purlin:audit` |
```

The sentence above the table reads as `phase3-plan.md` section 12, item 4, gives it. `package.py` copies the payload's `left` as today and needs no code
change for them. The package's `warnings` carry the spec mistakes of C3.3 as they carry every
payload warning.

## C6. Exit codes

This is the table, word for word and in this row order, that lane `words` writes as the
"Exit codes" table of `references/purlin_commands.md` (today lines 135 to 141), replacing
today's rows; no cell word is added or dropped. The lanes that own the commands build to it.
The cells are reference prose that describes what a decision or reading settles; the owner
reads them in the docs pass (`phase3-plan.md` section 12).

| Command | 0 | 1 | 2 |
|---------|---|---|---|
| `scripts/run/purlin_run.py --test`, `--audit` | everything asked happened | a tied test failed or did not run; evidence is missing; a marker names nothing a spec has; no settings file; the settings file cannot be read; a project set up by 0.9.5 and not upgraded; no test command; for `--audit` at `strong` and `signed`, a rule read is weak or could not be audited | a bad command line |
| `scripts/run/purlin_run.py --ci` | the tests tied to the proofs tagged for this runner's system passed | one of those failed or could not run, and nothing else | a bad command line |
| `scripts/review/sign.py` | written and committed, the walk closed, nothing to tag, or the tag already exists | no key; the commit was not made; a named rule no spec has; the tag refused for work or results not committed, no version, or a package not committed; git could not write the tag; the settings file cannot be read | a bad command line |
| `scripts/export/package.py` | written, or the check matched | the check did not match; the project states no version; the package could not be written; the settings file cannot be read | a bad command line |
| `scripts/review/ai_audit.py` | a rule was printed | the rule is not in the project; the settings file cannot be read | a bad command line |
| `scripts/init/scaffold.py` | set up | the settings file cannot be read | a bad command line, not a git repository, or no such project root |
| `scripts/init/update.py` | nothing pending, or applied | the settings file cannot be read | no project |
| `scripts/mcp/purlin/markers.py --near-misses` | always | never | a bad command line |

- Every `the settings file cannot be read` clause is OQ1's; `sign.py`'s
  `git could not write the tag` is OQ16's.
- Where the cells come from: `--ci`'s `0` is decision 95, its `1` keeps today's
  `, and nothing else`; `sign.py`'s `0` is today's cell with `nothing to tag` and
  `the tag already exists` (Q11) added, its `1`
  today's `no key, or the commit was not made` with the cases of Q11, C3.6 and Q65 added;
  `package.py`'s and `ai_audit.py`'s rows are their module docstrings' exit paragraphs with
  Q65 added; `scaffold.py`'s `2` is what scaffold RULE-31 and the argument reader already do,
  and nothing new is built for it; `set up` names what the command did.

## C7. Cross-lane expectations

A lane never edits a file it does not own. Before merging, each lane rebases on `main`, reruns
its own files and `--fast`, fixes its own files where a lane merged earlier changed a result
this file predicts, and reports every other failure with the test, the assertion and the value
seen.

| When this lane merges | What changes for other lanes' tests | Who adjusts |
|---|---|---|
| `core` | a rule with an untested proof reads `no test`, counted `rules to write a test for`; a rule waiting only on another system reads `not run`, counted `rules to test on <System>`; a comment naming nothing adds `test comments to correct` | each later lane in its own files; integration for lanes merged before `core` (none, by the merge order) |
| `run` | `--ci` runs only proofs tagged for its system; a feature with none is not run | lane `scaffold` tags the walk's greeting proof `@env(<this machine's system>)` before this matters (C8) |
| `run` | a local section has no `hostname` | any later lane asserting it adjusts |
| `mutation` | `features[f]['rules']` is gone from the engine's answer | no reader outside `scripts/run/mutation/` |
| `reports` | PROOF-19 no longer asserts the ending | nothing else |
| `scaffold` | the runner file setup writes names no job for the system of the machine running it (C14) | any later lane asserting a setup run's matrix adjusts |
| `drift` | `source_is_repository`, `NOT_A_SPEC_SOURCE` and `not_a_spec_source` exist; an anchor whose `> Source:` names no repository reads `error` in drift (C13) | lane `upstream` imports them |
| `upstream` | `add` refuses a text file or words; `sync` lists an anchor from plain text as `error` and exits 2 (C13) | any later lane whose fixture adds an anchor from plain text adjusts (none is known) |

## C8. Test fixtures other lanes rely on

- `dev/test_init_scaffold.py`'s gate walk: the greeting spec's proof is tagged
  `@env(<this machine's system>)`, computed from the running system, so its `--ci` steps write
  a section before and after decision 95 (lane `scaffold`).
- `dev/test_drift.py` `_rmtree` keeps its name and behaviour: `dev/test_upstream.py` imports it.
- `scripts/mcp/purlin/drift.py` keeps `_looks_like_git(url)` and `_ls_remote(project_root, url)`
  with today's behaviour: `scripts/anchor/upstream.py` imports both. Lane `drift` adds
  `source_is_repository(project_root, source) -> bool`, `NOT_A_SPEC_SOURCE` and
  `not_a_spec_source(name, source) -> str` (C13), which lane `upstream` imports; `drift` merges
  before `upstream`.
- `dev/test_signatures.py` names imported by `dev/test_tag.py`, and `dev/test_upstream.py` names
  imported by `dev/test_upstream_notes.py`, stay (each pair has one owner).
- Stand-in programs: on POSIX a stand-in is a file with no ending and the exec bit set; on
  Windows it is always `<name>.cmd` (`gh.cmd`, `az.cmd`, `dotnet.cmd`, `stryker.cmd`), never an
  `.exe`: no lane builds an `.exe`. Lookup of `gh` and `az` goes through `shutil.which` (lane
  `host`), which on POSIX needs the exec bit and on Windows honours `PATHEXT`, so a `.cmd`
  stand-in and the real `gh.exe` are found the same way. The Windows proofs drafted in
  `phase3-windows-list.md` for scaffold RULE-44 and host RULE-12 say `gh.cmd` on the search
  path, and their notes say to name the stand-in `gh.cmd`.

## C9. The skills start Purlin's scripts through the interpreter lookup

Every line of a skill that starts a Purlin script reads:

```
sh "${CLAUDE_PLUGIN_ROOT}/scripts/purlin_python.sh" "${CLAUDE_PLUGIN_ROOT}/scripts/<path>" <args>
```

The one home that says so is `references/purlin_commands.md`, section "Path resolution" (lane
`words`), one sentence: every Purlin script a skill runs is started through
`scripts/purlin_python.sh`, which finds Python 3 as the plugin's server does, falling back to
`py -3` on Windows. `references/formats/marker_format.md` shows its one example command in the
same form (lane `reports`).

The lookup (lane `settings`) exits 1 with its stderr line when it finds no Python 3, so a skill
that starts a script through it fails loudly (decision 69). The plugin's server start keeps
exit 0 there: the plugin manifest `.claude-plugin/plugin.json` starts the server with the
command `sh` and the arguments `${CLAUDE_PLUGIN_ROOT}/scripts/purlin_python.sh` and
`${CLAUDE_PLUGIN_ROOT}/scripts/mcp/purlin/server.py`, and its `mcpServers.purlin` entry gains,
beside `command` and `args`, `"env": {"PURLIN_PYTHON_SOFT": "1"}`. With `PURLIN_PYTHON_SOFT`
set to `1` the lookup prints the same line and exits 0; with it unset or anything else it exits
1. `command` and `args` do not change, so server PROOF-22 and PROOF-137 hold.

## C10. The one rule on emoji (Q9)

- Lane `instructions` writes `specs/instructions/purlin_output.md`, scope `scripts/**` and
  `templates/**`, with one rule: no file under `scripts/` or `templates/` carries an emoji or a
  pictograph, that is a character with the Unicode property `Extended_Pictographic` or U+FE0F,
  other than `▶`. Its test, `dev/test_purlin_output.py`, reads every tracked file under both
  folders. `→ ▼ ▲ ─ ·` are not pictographs and pass as they are.
- This rule replaces the existing check, run_script RULE-22 and PROOF-22 with its test, which
  covers one script (lane `run` deletes them). It lives in a spec of its own because
  run_script's scope is that one script and the rule's is every file Purlin prints from.
- The clauses of the five other specs go, each by its owner (Q9: "the emoji clauses scattered
  over five other specs go"): states RULE-40 and PROOF-47 with its test (`core`);
  purlin_report RULE-4 "no emoji" and PROOF-4's emoji part (`dashboard`); scaffold RULE-35 and
  PROOF-35 (`scaffold`); update RULE-20's emoji clause and PROOF-20 (`update`); ai_audit
  RULE-14's "and no emoji" and PROOF-29's "with no emoji" (`review`).
- `CLAUDE.md` (the owner's own instructions), `design/readme.md` and
  `references/writing_style.md` keep their emoji lines unchanged: the reading names them as the
  basis of the one promise, not as clauses to remove. The agent's own ban stays (Q58).

## C11. Numbering, splitting, proofs

- **A new id** is one more than the highest the file has held since it was last written whole:
  read `git log -p --follow -- <spec>` back to the commit that replaced the file whole, and take
  the highest `RULE-`/`PROOF-` number seen. Never reuse a deleted number (Q46, Q48 and the
  anchor's RULE-2).
- **Split by claim** (decision 94): a rule is split where its text states two or more claims,
  its proofs fall into groups each showing exactly one of them, and no proof shows two. The
  first claim keeps the rule's id; each other claim takes a new id; every proof keeps its id and
  text and only its `(RULE-N)` changes; markers do not change. A rule whose claims share every
  proof is not split. Each split is listed in the lane's report as `old id -> ids, one line per
  claim`.
- **One case per proof** (decision 71, Q1, Q8): a proof whose test loops over gates, inputs or
  systems with the same expected result becomes one proof per gate, input or system, each with
  a test of its own and a marker above it.
- **Damaged copies** (Q40 for `specs/skills/skill_sign.md`; OQ13 for every other spec under
  `specs/skills/` and for `specs/instructions/purlin_agent.md` and `purlin_version.md`, about
  280 proofs in 12 specs): a proof whose case is a
  deliberately damaged copy of the file the spec covers, reported by the check, leaves the spec
  and its marker line goes; the damaged copy stays as a second assertion inside the test of the
  proof whose sentence the damage removes, through `refusals()`, `frontmatter_refusals()` and
  `next_step_refusals()` of `dev/skill_checks.py`, unchanged. A proof that a bump-script input is
  refused, or that a boundary holds, is not a damaged copy and stays.
- **Instruction rules** (decision 94): a rule of a spec under `specs/skills/` says what the
  instructions tell the agent (`The skill tells the agent to ...`); a rule of `purlin_agent`
  says what the agent definition tells (`The agent definition ...`). Proofs that run the product
  to check the skill quotes it correctly stay, under the reworded rule.
- `dev/test_vocabulary.py`: no lane adds to it.

## C12. One home for each new sentence

`CLAUDE.md` "Skill and reference deduplication": a concept lives in one reference and the others
point at it. Two facts these decisions add are needed in several files; each is stated once, in
the home below, and every other file points at that home in a clause such as
`(references/hard_gates.md, "Where a runner runs")` instead of restating it.

| Fact | Its one home (lane `words`) | Files that point at it, and who writes the pointer |
|---|---|---|
| S1, decisions 95 and 97: a remote runner runs only the tests tied to proofs tagged `@env` for its own system; a person's own machine, Mac or Windows, proves every proof with no `@env` and every proof tagged for its own system, and never one tagged for another; a runner file names a remote machine only for a system some proof is tagged for that the machine running setup is not | `references/hard_gates.md`, section "Where a runner runs, and when a project has one" (line 123), one paragraph | `hard_gates.md` lines 116 to 117 (the false clause "The tests a person ran are the tests a runner runs" goes, nothing restated), line 140 (the tag run's cell, "It runs the marked tests on a clean machine and nothing else") and line 207 (`words`); `references/glossary.md` "remote runner" (`words`); `references/purlin_commands.md` line 110 (`words`); `references/formats/marker_format.md`'s `{files}` row (`reports`); `skills/test/SKILL.md` Step 5 and `skills/audit/SKILL.md` (`skills-run`); `references/spec_quality_guide.md` "The operating system" (`skills-author`); `skills/init/SKILL.md` "What the runner runs" (`scaffold`); the header comments of `templates/purlin.yml` and `templates/purlin.azure-pipelines.yml`, where each says a run "runs the marked tests" (`host`) |
| S2, decision 94 and Q37: test strength is one share per feature; with mutation testing on, a feature whose share could not be measured leaves its rules `weak` with the reason `strength not measured: <reason>` (OQ9); an engine that cannot run on this system counts as none and the AI audit alone decides | `references/hard_gates.md`, one paragraph directly under the gate table (after line 28); the `strong` row of the table (line 27) keeps its words | `references/glossary.md` "test strength" defines the word as the share of one feature's breaks the tests caught, and points (`words`); `references/review_criteria.md` says only what the model is shown about strength, and points (`review`); `references/spec_quality_guide.md` "When a rule is stuck" has the row for reading the cell and what to do, and points (`skills-author`); `skills/audit/SKILL.md` points (`skills-run`) |

A spec's own rule about what its product does is not a copy: specs state behaviour, and the
host, run_script, evidence_writer, states and mutation specs keep their rules on these facts.
A pointer in a file that is not Markdown (a template's `#` comment) names the home as plain
text and says it is in the plugin, since the file is copied into a project that has no
`references/`, as `templates/evidence-readme.md` already does: `references/hard_gates.md in the
Purlin plugin, "Where a runner runs"`.

## C13. An anchor is a spec in Purlin's format (decision 97; lanes `drift`, `upstream`, `skills-author`, `words`)

Anchors made from plain text go everywhere. An anchor's source is a git repository and a path
in it, as `references/formats/anchor_format.md` already names it.

**How a spec in Purlin's format is recognised** (technical call): the file's text, read by the
spec reader every spec goes through (`upstream.parse_rules`, which is `specs._parse_spec`), holds
at least one rule. Nothing else is asked: no heading form, no field.

**How a `> Source:` that names no repository is recognised** (technical call), in one place,
`drift.source_is_repository(project_root, source) -> bool`, which `upstream` imports: it is false
when the value as the spec reader gives it (`info['source']`, the address with any path already
split off by `specs.parse_source`) holds whitespace, which is a description in words, or names a
file that exists, joined to the project root or as written, which is a file on disk. Every other
value is taken as a repository and asked with git, as today; one git cannot read keeps today's
`error` with git's own message. `_looks_like_git` is no longer asked for this, so an Azure DevOps
address is a repository like any other.

**`upstream.py add` refuses** a source that is not a spec in Purlin's format kept in a git
repository, in three cases:

| Case | When it is refused |
|---|---|
| a file on disk (`policy.txt`, or a full path to one) | before any process starts |
| a description in words | before any process starts |
| a file in a repository, at `--path`, that holds no rule | after the fetch; the checkout fetched for it is removed before `add` returns |

`add` returns `{"command": "add", "anchor": "<name>", "source": "<source>", "path": <path or null>, "status": "error", "error": "<the refusal after '<name>: '>"}`.
The command line prints the one line `<name>: <error>` and exits 2, as every refusal of `add`
does (upstream RULE-5 and RULE-6); `--json` prints the object instead. Nothing is written or
changed under `specs/`, `specs/_anchors/` is not created, and the call leaves no file under
`.purlin/runtime/anchors/`. The check of an unsafe source (upstream RULE-6) still comes first.

The refusal (OQ25), as printed:

```
<name>: not added. <what> is not a spec in Purlin's format kept in a git repository. Run purlin:anchor create <name> to write its rules in this project.
```

`<what>` is the source as given for a file on disk, the `--path` as given for a file in a
repository, and `The description given` for words. `upstream.NOT_A_SPEC` holds the part after
`<name>: ` as a `%`-format string with two values (`<what>`, `<name>`). For example:
`refunds: not added. policy.txt is not a spec in Purlin's format kept in a git repository. Run purlin:anchor create refunds to write its rules in this project.`

**An anchor a project already has whose `> Source:` names no repository**: a copy an earlier
Purlin made from plain text, or an anchor a person wrote by hand with words in `> Source:`.

- `drift`: `check_pin` answers `{"status": "error", "remote_sha": null, "not_a_spec": true}`
  before any process is handed the source; `pin_report`'s row carries `"not_a_spec": true` and
  `"error": drift.not_a_spec_source(name, source)`; the engineer view's line is
  `anchor <name>: <error>`. Its `status` stays `error`, so every count of errors holds.
- `upstream.py sync --check`, `sync <name>` and `sync` with no name: `pinned_anchors` covers
  every anchor carrying a `> Source:`; such an anchor's row is `status` `error` with
  `"not_a_spec": true` and the same `error`; it is printed `<name>: <error>`; no process is
  started for it, nothing is written, and the command exits 2, as for any source that cannot be
  read (upstream RULE-9).
- The reason (OQ25), `drift.NOT_A_SPEC_SOURCE`, a `%`-format string with two values (the
  `> Source:` value as written, the anchor's name), filled by `drift.not_a_spec_source(name, source)`:

  ```
  its source, <source>, is not a spec in Purlin's format kept in a git repository, so it cannot be checked. Run purlin:spec <name> to take out its > Source: and > Pinned: lines and keep it as this project's own anchor.
  ```

  Drift prints
  `anchor refunds: its source, policy.txt, is not a spec in Purlin's format kept in a git repository, so it cannot be checked. Run purlin:spec refunds to take out its > Source: and > Pinned: lines and keep it as this project's own anchor.`
  and the anchor check prints the same after `refunds: `.
- The status, the run, the audit and signing read such an anchor's rules as today; nothing else
  warns of it.

**A local anchor** is a spec the project wrote itself under `specs/_anchors/` with no
`> Source:` line (`anchor_format.md`, "Location"): it is never checked and nothing here touches
it. Taking the `> Source:` and `> Pinned:` lines out of an anchor makes it one.

**A sync whose repository file, at the new head, holds no rule** is not decided: it is written
as today and reported (plan section 11).

**What goes** (clean release, deleted outright, no test that it is absent): upstream RULE-7 with
PROOF-7, 24, 28 and 29, and RULE-14 with PROOF-14, their numbers never reused; the Description's
clause on free text; in `scripts/anchor/upstream.py` `FREE_TEXT_NOTE`, `_free_text`,
`is_repository` (its callers use `drift.source_is_repository`), the `no_rules` status and its
printed line, the module docstring's free-text sentence and `add`'s help "or a file of free
text"; their tests in `dev/test_upstream.py`; the free-text paragraph of `skills/anchor/SKILL.md`;
the comment in `scripts/mcp/purlin/drift.py` that calls a Windows path free text; the row for
upstream RULE-7 in `phase3-windows-list.md`. The `> Note:` field is untouched: its "free text"
is a note's own words.

**New rules**, each from the next free id with one proof per case (C11):

- upstream: `add` refuses a source that is not a spec in Purlin's format kept in a git
  repository, prints the refusal, writes nothing and exits 2 (three proofs: a text file in the
  project, a description in words, a file in a repository with no rule); `sync --check`, `sync
  <name>` and `sync` with no name report an anchor whose `> Source:` names no repository as
  `error` with the reason, start no process for it, write nothing and exit 2 (three proofs; the
  third, two repository anchors and one from a text file, takes PROOF-14's case).
- drift: the engineer view reports an anchor whose `> Source:` names no repository as `error`
  with the reason's line, and no process is handed the source (two proofs: a file on disk,
  words).
- skill_anchor: the skill tells the agent that an anchor's source is a spec in Purlin's format
  with at least one rule, kept in a git repository, and that any other source is refused and
  written with `purlin:anchor create` (one proof reading the sentence).

**`references/formats/anchor_format.md`** moves from lane `anchors` to lane `upstream`, which
changes the code it describes: CLAUDE.md "Format reference versioning" puts the format change in
the same commit as the code change. `> Format-Version:` goes from 9 to 10 (what a `> Source:` may
hold narrows, and a source file must hold a rule; a consumer that used plain text must change),
in the `upstream` commit that makes `add` refuse. In "The source: a git URL plus a path", after
its first paragraph, this paragraph, word for word:

```
The file at the path is a spec in this format that holds at least one rule. `purlin:anchor add` refuses any other source, a file on disk, a description in words or a file with no rule, and writes nothing. A copy whose `> Source:` names no repository reads `error` in `purlin:drift` and in `purlin:anchor sync --check`. A local anchor carries no `> Source:` and is never checked.
```

`references/drift_criteria.md` (lane `drift`): the "Anchors behind" table gains the row
`| The source names no repository: words, or a file on disk | `anchor <name>: its source, <source>, is not a spec in Purlin's format kept in a git repository, so it cannot be checked. Run purlin:spec <name> to take out its > Source: and > Pinned: lines and keep it as this project's own anchor.` |`,
under the one Criteria-Version bump, 9 to 10, that Q31 already makes.

## C14. Where a proof is proven, and the machines a runner file names (decision 97)

- **A person's own machine**, Mac or Windows, proves every proof with no `@env` and every proof
  tagged for its own system. A proof tagged for another system reads `not run` there whatever
  its tied test did (C4.4) and is counted by R3. This is built today; nothing changes.
- **A remote machine** runs only the tests tied to proofs tagged for its own system (decision
  95; C4.3; a file of mixed tests runs whole and only the tagged tests count, OQ21).
- **A runner file names a remote machine only for a system some proof is tagged for that the
  machine running setup or the upgrade is not.** Scaffold RULE-13 already writes the file for
  that reason alone; the matrix follows it (C1.12). Scaffold RULE-15 reads "The workflow carries
  one job per operating system the `@env` tags in `specs/` name that the machine running setup
  is not, and no other, and the Purlin release pinned as `v<version>`"; its PROOF-15 becomes a
  project with one proof tagged `@env(windows)` and one tagged `@env(macos)`, set up on a Mac,
  whose matrix reads exactly `os: [windows-latest]` (the test names the running system's case,
  so on Windows it reads `os: [macos-latest]`). Update RULE-15's "carrying the matrix the `@env`
  tags name" reads "carrying one job per operating system the `@env` tags name that the machine
  running the update is not". Host RULE-19 reads "The matrix is one job per operating system it
  is handed, in the order Linux, macOS, Windows, and no other"; its proofs, which hand tags to
  `runners_for`, hold; `scripts/run/workflow.py`'s module docstring says the matrix names the
  systems some proof is tagged for that the machine writing the file is not, and its sentence
  "an untagged proof is satisfied by any operating system, so whichever job runs proves it too"
  goes (decision 95 made it false).
- **The printed words that follow** (chosen here; `phase3-plan.md` section 12, items 6 and 7):
  setup's note under the written runner file,
  `  the matrix is <images>, the systems the @env tags in specs/ name that this machine is not.`,
  in place of `  the matrix is <images>, the systems the @env tags in specs/ name.`; the
  upgrade's question, `Write <path>, one job per operating system your specs name that this machine is not?`,
  in place of `Write <path>, one job per operating system your specs name?`.
- **This repository**: wave W tags the 13 Mac-only proofs `@env(macos)`; setup, run on the
  Mac, then writes a runner file with one Windows job and no Mac job.
