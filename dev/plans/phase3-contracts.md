# Phase 3 contracts: what lanes produce and consume, word for word

Written by the planning agent on 2026-09-29 for decisions 94, 95 and 96. Every agent builds to
this file and none chooses. `phase3-plan.md` says who owns what; each brief under
`phase3-lanes/` repeats the parts its lane needs.

Words marked **PENDING OQ<n>** are the recommended option of owner question `<n>` in
`phase3-plan.md` section 8. Before the fan-out the orchestrator replaces each such line with the
option the owner chose, in this file and in every brief that repeats it, and deletes the
`PENDING` mark. Where the owner chose the option that removes the thing, the orchestrator writes
`REMOVED BY OQ<n>` in its place, and every lane leaves that item as it stands. A lane that still
finds a `PENDING` mark when it starts leaves that item as it stands and reports it.

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
    no-report sentence (C3.2). **PENDING OQ10** (recommended option 1; option 2 keeps it too).
    With OQ10's option 3, `missing` stays `''` here.
  - A feature whose spec names no code files is not handed to the engine, as today, and has no
    `missing`: lane `core` reads that case from the spec itself (C4.2, **PENDING OQ10**).
  - The engine cannot run on this operating system (`runs_here` is false, C1.3): `engine` is
    `none`, `available` is false, `reason` is the not-on-this-system sentence (C3.2,
    **PENDING OQ12**; with OQ12's removal option `reason` is `''`), and every `missing` is `''`:
    it counts as no engine.
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

### C1.9 The settings file that cannot be read (P2, **PENDING OQ1**)

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

### C1.10 The unknown rule (P2, **PENDING OQ15**)

`scripts/review/sign.py` `NOT_A_RULE` holds C3.6's line as a `%`-format string, and P2 adds
beside it `def not_a_rule(feature, rule) -> str`, which returns that line filled in whatever
the owner's option (three values for options 1 and 2, two for option 3). Every print of the
line, P2's own and each lane's, calls `sign.not_a_rule(feature, rule)` and never formats
`sign.NOT_A_RULE` itself. Lane `signing` prints it last, above the summary; lane `review`
imports `not_a_rule` from `scripts/review/sign.py` and prints `sign.not_a_rule(feature, rule)`
from `ai_audit.py --rule`.

### C1.11 Setup's line for an engine that cannot run here (P2, **PENDING OQ12**)

`scripts/init/scaffold.py`: `NO_ENGINE_HERE = 'Mutation testing is off: mutmut does not run on Windows, so the AI audit alone judges test strength.'`
(OQ12's first option; its second option's words are in C3.2; with its removal option P2 does not
add the constant and lanes `scaffold` and `update` print no mutation line for such a project).
Lane `scaffold` prints it from setup and lane `update` from the upgrade, each where
`mutation.runs_here(engine)` is false, in place of `NO_ENGINE`.

## C2. Kinds of `Left to do`

`scripts/mcp/purlin/summary.py` `KINDS`, final order (lane `core` owns it):

| # | Kind | One / many | Command | Carried by |
|---|---|---|---|---|
| 1 | `no_proof` | as today | `purlin:spec` | a rule |
| 2 | `to_correct` (**PENDING OQ3**: its place, what it counts) | `test comment to correct` / `test comments to correct` | `purlin:build` | the project |
| 3 | `to_fix` | as today | `purlin:build` | a rule |
| 4 | `no_test` | as today | `purlin:build` | a rule |
| 5 | `to_test` | as today | `purlin:test` | a rule |
| 6 | `to_test_remote` | as today | `purlin:test --remote` | a rule |
| 7 | `to_test_by_hand` | as today | `purlin:sign` | a rule |
| 8 | `to_audit` | as today | `purlin:audit` | a rule |
| 9 | `to_measure` (**PENDING OQ9**: whether it exists, and its place just before `to_strengthen`) | `rule to measure` / `rules to measure` | `purlin:audit` | a rule |
| 10 | `to_strengthen` | as today | `purlin:build` | a rule |
| 11 | `no_scope` (when it counts: **PENDING OQ10**) | as today | `purlin:spec` | a rule |
| 12 | `to_sign` | as today | `purlin:sign` | a rule |
| 13 | `to_tag` | as today | `purlin:sign` | the project |

- `to_correct` (Q22, **PENDING OQ3**): its count is the number of lines
  `markers.marker_problems` returns over the test files the settings' suites name, at every
  gate: a comment naming something no spec has (`NAMES_NOTHING`) and a comment naming a rule
  that has proofs (`RULE_HAS_PROOFS`), since both fail the run. With OQ3's second option only
  the `NAMES_NOTHING` lines are counted. No rule carries it. The terminal line reads
  `  1 test comment to correct: purlin:build` for one and
  `  <n> test comments to correct: purlin:build` for any other count. The payload item's
  `text` follows the same rule as every kind (`summary._words`): `"1 test comment to correct"`
  for one, `"<n> test comments to correct"` otherwise, so the item is
  `{"kind": "to_correct", "count": 1, "text": "1 test comment to correct", "command": "purlin:build"}`
  for one and `{"kind": "to_correct", "count": 3, "text": "3 test comments to correct", "command": "purlin:build"}`
  for three. `to_tag` appears only when kinds 1 to 12 are all zero, so such a comment holds
  back the signed tag, as any other line does (decision 75). With OQ3's removal option there
  is no `to_correct`.
- `to_measure` (Q37, OQ9): a rule whose strong cell reads `weak` only because the breaking was
  on and its feature's `audit.mutation.missing` is not empty. With OQ9's second option there is
  no `to_measure` and such a rule counts under `to_strengthen`; with the third, C4.2's weak
  cell is not built.
- `no_scope` (**PENDING OQ10**, option 1): as today at `signed`; in addition, at `strong` and
  `signed` with `mutation_engine` not `none`, a rule whose strong cell reads `weak` only because
  its spec names no code files (C4.2) counts here and not under `to_measure` or
  `to_strengthen`. With OQ10's options 2 and 3, `no_scope` counts as today.
- A rule waiting only on a proof tagged for another system, whose test was skipped here, is
  `to_test_remote`; a proof, tagged or not, with no test tied to it makes the rule `no_test`
  (Q7, Q20).

## C3. Printed lines

### C3.1 Settled by a decision or a reading

| Id | Line | Printed by | Source |
|---|---|---|---|
| L1 | `This git host cannot run tests remotely. Everything on this machine works.` | setup, where the remote names a git host Purlin cannot use; the upgrade, through `prerequisites()`, as today; placement in setup **PENDING OQ7**, the same placement as L2: the summary line drops its `Git host ...` part in that case too, and L1 stands where the owner's answer puts L2 (recommended: `Gate <gate>. Suites <names>.` then L1 on a line of its own). With OQ7's option 2 L1 closes the summary line; with its option 4, which removes L2 alone, L1 stays a line of its own after the summary line | decision 96 (P1 the words, `scaffold` the placement) |
| L2 | `No git host found.` | setup, where the project has no remote; placement **PENDING OQ7** (recommended: a line of its own right after `Gate <gate>. Suites <names>.`, which drops its `Git host ...` part in that case; the upgrade keeps `No git remote, so there is no runner to read this workflow. Add one with: git remote add origin <url>`) | decision 96 |

Under every option of OQ7 the words `Git host not read from a remote` leave setup's summary line:
where no git host is read the line names none (with option 4 and no remote, setup prints nothing
about the host).
| L3 | `purlin: "<answer>" is not a gate; reading it as <gate>.` where `<gate>` is the project's own default | setup (today), the upgrade (new) | Q18 |
| L4 | `This project was set up by an older Purlin and not upgraded, so nothing ran. Run purlin:init --update.` | the run | exists; Q19 moves its proofs |
| L5 | `  1 test comment to correct: purlin:build` / `  <n> test comments to correct: purlin:build` | every ending, in C2's place (**PENDING OQ3**) | Q22 |
| L6 | `→ Run: git show signed/<version>:.purlin/evidence/package/<version>.json` | the export skill's closing row for a package that fails its fingerprint | Q52 |
| L7 | `Nothing left to do.` | the build skill's ending for a finished project at `passed` and at `strong` | decision 76, Q62 |
| L8 | `WARNING: 1 line under ## Rules in <path> is not numbered; a rule is `- RULE-N: <text>`. Run purlin:spec <feature>.` (singular) / `WARNING: <n> lines under ## Rules in <path> are not numbered; a rule is `- RULE-N: <text>`. Run purlin:spec <feature>.`; the closing ` Run purlin:spec <feature>.` is **PENDING OQ2** (options 1 and 2 add it; option 3 and 4 leave today's line with the plural fixed) | the status | plural fixed (P2); the command, decision 94's headline, through OQ2 |
| L9 | `1 spec file carries tags this release does not read (...)` (singular); the plural stays | the status | plural fixed (P2) |

### C3.2 The breaking tool's reasons (lane `mutation` writes them, lane `run` prints them)

Existing, kept word for word:
- `mutmut is not installed: run "pip install mutmut"`
- `stryker is not installed: run "npm install --save-dev @stryker-mutator/core"`
- `dotnet stryker is not installed: run "dotnet tool install -g dotnet-stryker"`

**PENDING OQ11** (recommended option; today's words are
`dotnet is not installed, so no engine breaks C# code` and
`the engine timed out after <seconds> s, so the breaks it made are partial and measure nothing: raise --arm-timeout to give it longer`):
- .NET missing: `dotnet is not installed: install the .NET SDK, then run "dotnet tool install -g dotnet-stryker"`
- time limit: `the engine timed out after <seconds> s, so the breaks it made measure nothing: run purlin:audit --arm-timeout <seconds> to give it longer`
  (the first `<seconds>` is the limit used; the second is written literally as `<seconds>`).
  With this option `purlin:audit` takes `--arm-timeout <seconds>`, how long the breaking tool
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
  padded. These words are shown to the owner in OQ11's first option.
- With OQ11's second option the time-limit sentence ends `measure nothing: run purlin:audit again`
  and no flag is added; with its third, both reasons keep today's words and no flag is added.

**PENDING OQ12** (recommended option), Python's breaking tool on Windows:
- the run: `mutmut does not run on Windows, so test strength is not measured here and the AI audit alone decides`
- setup and the upgrade, in place of `NO_ENGINE` for a pytest project on Windows:
  `Mutation testing is off: mutmut does not run on Windows, so the AI audit alone judges test strength.`
- With OQ12's second option: `mutmut does not run on Windows` and
  `Mutation testing is off: mutmut does not run on Windows.`; with its removal option the run
  prints nothing for it and setup and the upgrade print no mutation line for such a project.

**PENDING OQ10** (options 1 and 2):
- no report: `<engine> ran and wrote no report: run purlin:audit again`,
  where `<engine>` is `mutmut`, `stryker` or `dotnet stryker`.

The run prints `purlin: <reason>` once for any answer whose `reason` is not empty, installed or
not (today only an installed engine's reason is printed), and `purlin: <missing>` once for each
distinct `missing` sentence not already printed.

### C3.3 Spec mistakes (P2 writes them; **PENDING OQ2**)

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

### C3.4 A settings file that cannot be read (P2; **PENDING OQ1**)

`.purlin/config.json cannot be read: <cause>. Fix the file by hand; nothing ran and nothing was saved.`

`<cause>` is, in order of the first that applies: `it is not UTF-8 text`;
`<JSON message> at line <n>` from the JSON reader's own message and line (for example
`Expecting ',' delimiter at line 4`); `it holds a <list | string | number> where an object belongs`;
the operating system's own message for an open that failed. All four causes are shown to the
owner in OQ1's first option; with its second option the line is
`.purlin/config.json cannot be read at line <n>. Fix it, then run the command again.` where the
JSON reader names a line, and `.purlin/config.json cannot be read. Fix it, then run the command again.`
otherwise.

### C3.5 The settings tool (lane `settings`; **PENDING OQ8**)

| When | The tool answers |
|---|---|
| a save failed | `The setting was not saved: <cause>.` |
| a write with no value | `A change needs a value; nothing was saved.` |
| a value not accepted for a known setting | `"<value>" is not accepted for <key>; it takes <accepted>. Nothing was saved.` |
| a write of `version` | `version is written by purlin:init from Purlin's own version; nothing was saved.` |
| a read of a key that is absent or null | the JSON `{"<key>": null}`, indented as a found key is (Q70; technical) |

`<accepted>` per key (the six phrases are shown to the owner in OQ8's first option, and are
**PENDING OQ8** with the rest of this table), joined `, ` and ` or `: `gate` takes `passed, strong or signed`;
`mutation_engine` takes `none, auto, mutmut, stryker or stryker_net`; `min_strength` takes
`a whole number from 0 to 100, or null`; `audit_parallel` takes `a whole number from 1 to 16`;
`tests` takes `a list`; `ci` takes `github, azure or none`. An explicit `null` is accepted for
`min_strength` alone. Keys Purlin does not know are written as today.

### C3.6 Signing and the audit reader (P2 and lanes `signing`, `review`)

- Unknown rule (**PENDING OQ15**), printed last above the summary by signing, and by the audit
  reader for `--rule`: `<feature> <RULE-N> is not a rule any spec has. Run purlin:status <feature> to see its rules.`
  With OQ15's third option the line is today's, `<feature> <RULE-N> is not a rule any spec has.`,
  still printed last and by the audit reader.
- git failed to write the tag (**PENDING OQ16**): `No tag: git could not write signed/<version>: <git's own message, first line>.`
  Exit 1. With OQ16's second option: `git could not write the tag signed/<version>.` then git's
  own message on the next line, exit 1; with its third, signing prints git's own message as git
  gave it and exits 1. In every option the line for a tag that already exists is no longer
  printed for this case.

### C3.7 The run (lane `run`)

| Id | When | Line |
|---|---|---|
| R1 | a rule some of whose proofs have no test, **PENDING OQ4** | `<feature> <RULE-N> has no test for <PROOF-N>[, <PROOF-M>...]. Run purlin:build <feature>.` |
| R2 | a rule none of whose proofs has a test | `<feature> <RULE-N> has no test. Run purlin:build <feature>.` (unchanged) |
| R3 | proofs tagged for another system, on a person's machine, **PENDING OQ20** | one line per system: `1 proof needs <System>; this machine is <System>. Run purlin:test --remote.` / `<n> proofs need <System>; this machine is <System>. Run purlin:test --remote.` A proof tagged for another system with no test tied to it is not counted here (it has R1 or R2 instead). |
| R4 | no test command, tools recognised, **PENDING OQ5** | `No test command is set in .purlin/config.json, so nothing ran.`, then for each tool in the fixed order `Suggested for <name>: <run>` followed by that tool's needs line where it has one, then `Suggested tests setting: <the entries as one JSON array on one line>` |
| R5 | no test command, nothing recognised | unchanged |
| R6 | the settings file cannot be read | C3.4 |
| R7 | the `audit_parallel` warning (Q10) | printed once, beside the status table, and no longer as the run's first line |

The Python entry's `run` on Windows, **PENDING OQ6**: `py -3 -m pytest` in place of
`python3 -m pytest`, the rest of the command unchanged; every other system keeps `python3`.

### C3.8 The runner (lane `host`)

| When | Line |
|---|---|
| no branch can be read, **PENDING OQ22** | `No branch could be read from the git host or from git, so the results were not committed.` |
| a run on a ref that is neither a `run/*` branch nor a `signed/*` tag, **PENDING OQ23** | `This run is on <ref>, which is neither a run branch nor a signed tag: the tests ran and nothing is written.` |
| a signed tag | `Tag run: nothing is written. This run reruns the tests on <ref>.` (unchanged) |

### C3.9 Near misses (lane `reports`; **PENDING OQ18**)

Where the nearest id is a rule with exactly one proof, the fix names that proof and the `why`
reads ``` `RULE-30` is one character from `RULE-3`, which login has; a comment names its one proof, `PROOF-3` ```
(ids and feature filled in). A rule with no proof keeps today's fix and why. A rule with two or
more proofs gives no near miss.

### C3.10 The audit's notes (lane `review`; **PENDING OQ17**)

After the findings in `ai_audit.py --feature <f> --rule <RULE-N>`: a blank line, the heading
`What the audit noted`, then each note indented two spaces, as the findings are. No heading
and no blank line where the entry has no notes.

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
  with the reason `no test for <PROOF-N>[, <PROOF-M>]` (**PENDING OQ4**). Order:
  `failed` > `no test` > `not run` / `partial` > `passed`.

### C4.2 The strong cell (lane `core`)

With `mutation_engine` not `none`, where the feature's `audit.mutation.score` is null and its
`missing` is not empty, the strong cell reads `weak` with the reason `strength not measured:
<missing>` after any findings (the prefix `strength not measured: ` is shown to the owner in
OQ9's first and second options). An engine that cannot run here answers `none` (C1.2), so the
cell reads `strong` on the audit alone with `no mutation score measured`, as today.
**PENDING OQ9**: with OQ9's third option this weak cell is not built.

**PENDING OQ10** (option 1; decision 94, "nothing measured means not strong"): with
`mutation_engine` not `none` and the gate `strong` or `signed`, a rule of a feature spec that
names no code files (`fingerprint.incomplete_reason` is not None; an anchor is never such a
spec) reads `weak` with the reason
`strength not measured: the spec names no code files: run purlin:spec <feature>`, and counts
under `no_scope` (C2). With OQ10's option 2 the reason is the same and the rule counts under
`to_measure`; with its option 3 or 4 such a rule reads as today.

## C5. Package format 4 (lane `package` writes `references/formats/package_format.md`)

`> Format-Version: 4`: the table of `left` kinds gains `to_correct` (C2 row 2, unless OQ3
removes it) and `to_measure` (C2 row 9, if OQ9 keeps it). If both are removed, nothing in the
format changes and there is no bump. The two rows, in the table's own form, each where C2 puts
its kind:

```
| `to_correct` | `1 test comment to correct`, `<n> test comments to correct` | `purlin:build` |
| `to_measure` | `1 rule to measure`, `<n> rules to measure` | `purlin:audit` |
```

The first row is **PENDING OQ3**, the second **PENDING OQ9**. Where `to_correct` stands, the
sentence above the table reads as `phase3-plan.md` section 12, item 4, gives it. `package.py` copies the payload's `left` as today and needs no code
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

- Every `the settings file cannot be read` clause is **PENDING OQ1**; with OQ1's option 3 it is
  left out, and `update.py`'s `1` reads `never` as today.
- `sign.py`'s `git could not write the tag` is **PENDING OQ16**: with every option of OQ16 the
  exit is 1, so the clause stands whatever the words of the printed line.
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

## C8. Test fixtures other lanes rely on

- `dev/test_init_scaffold.py`'s gate walk: the greeting spec's proof is tagged
  `@env(<this machine's system>)`, computed from the running system, so its `--ci` steps write
  a section before and after decision 95 (lane `scaffold`).
- `dev/test_drift.py` `_rmtree` keeps its name and behaviour: `dev/test_upstream.py` imports it.
- `scripts/mcp/purlin/drift.py` keeps `_looks_like_git(url)` and `_ls_remote(project_root, url)`
  with today's behaviour: `scripts/anchor/upstream.py` imports both.
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
- **Damaged copies** (Q40 for `specs/skills/skill_sign.md`, approved; for every other spec under
  `specs/skills/` and for `specs/instructions/purlin_agent.md` and `purlin_version.md`
  **PENDING OQ13**, and with OQ13's second or third option those specs keep these proofs as
  they stand): a proof whose case is a
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
| S1, decision 95: a remote runner runs only the tests tied to proofs tagged `@env` for its own system; a proof with no `@env` is proven by a run on a person's machine | `references/hard_gates.md`, section "Where a runner runs, and when a project has one" (line 123), one paragraph | `hard_gates.md` lines 116 to 117 (the false clause "The tests a person ran are the tests a runner runs" goes, nothing restated), line 140 (the tag run's cell, "It runs the marked tests on a clean machine and nothing else") and line 207 (`words`); `references/glossary.md` "remote runner" (`words`); `references/purlin_commands.md` line 110 (`words`); `references/formats/marker_format.md`'s `{files}` row (`reports`); `skills/test/SKILL.md` Step 5 and `skills/audit/SKILL.md` (`skills-run`); `references/spec_quality_guide.md` "The operating system" (`skills-author`); `skills/init/SKILL.md` "What the runner runs" (`scaffold`); the header comments of `templates/purlin.yml` and `templates/purlin.azure-pipelines.yml`, where each says a run "runs the marked tests" (`host`) |
| S2, decision 94 and Q37: test strength is one share per feature; with mutation testing on, a feature whose share could not be measured leaves its rules `weak` with the reason `strength not measured: <reason>` (**PENDING OQ9**); an engine that cannot run on this system counts as none and the AI audit alone decides | `references/hard_gates.md`, one paragraph directly under the gate table (after line 28); the `strong` row of the table (line 27) keeps its words | `references/glossary.md` "test strength" defines the word as the share of one feature's breaks the tests caught, and points (`words`); `references/review_criteria.md` says only what the model is shown about strength, and points (`review`); `references/spec_quality_guide.md` "When a rule is stuck" has the row for reading the cell and what to do, and points (`skills-author`); `skills/audit/SKILL.md` points (`skills-run`) |

A spec's own rule about what its product does is not a copy: specs state behaviour, and the
host, run_script, evidence_writer, states and mutation specs keep their rules on these facts.
A pointer in a file that is not Markdown (a template's `#` comment) names the home as plain
text and says it is in the plugin, since the file is copied into a project that has no
`references/`, as `templates/evidence-readme.md` already does: `references/hard_gates.md in the
Purlin plugin, "Where a runner runs"`.
