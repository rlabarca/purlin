# The Proof Plugin Contract

A checklist, not a parsed format. It carries no `> Format-Version:` line because nothing reads
it as data: it is what a person follows when they write a proof plugin for a new language, or
audit one of the eight Purlin ships.

The rules themselves live in `specs/_anchors/proof_common.md`, the anchor every per-language
plugin spec declares with `> Requires: proof_common`. This file cites those rules and never
restates them: where the two disagree, the anchor is right and this file is stale. The wire
format a plugin writes is `references/formats/proofs_format.md`.

Four sections:

- **A. Behavioural requirements**: where the rules are, and the two legitimate shapes of the
  merge filter.
- **B. Wiring a new language**: the ordered list of files a new framework has to touch, and
  the per-framework table of what the eight shipped plugins registered.
- **C. Checker and extractor**: why a registered framework with no Pass 1 checker is a hole in
  the quality gate.
- **D. How to prove a plugin**: which test class proves which rule, and the per-plugin spec
  template.

## A. Behavioural requirements

Every requirement is a rule of `specs/_anchors/proof_common.md`, and that is where to read it.
This file keeps no second list: a plugin that fails one of those rules is not a proof plugin,
it is a program that writes JSON files into `specs/`. Section D says which test class proves
which rule.

### The two legitimate merge shapes

RULE-4, RULE-11, RULE-18 and RULE-22 meet in one expression, the filter that decides which
committed entry survives a write. There are exactly two correct shapes of it, and which one a
plugin gets depends on whether its framework reports a skip.

A skip-exempt plugin (shell, sql, phpunit, c) writes the two-clause form:

```python
keep(e) = e["feature"] != feature
          or (os.path.exists(os.path.join(project_root, e["test_file"]))
              and e["test_file"] not in this_run_files)
```

A skip-capable plugin (pytest, jest, vitest, xunit) writes the four-clause form:

```python
keep(e) = e["feature"] != feature
          or (os.path.exists(os.path.join(project_root, e["test_file"]))
              and (e["test_file"] not in this_run_files
                   or ((feature, e["id"], e["test_file"]) in this_run_skipped
                       and (e["id"], e["test_file"], e["test_name"]) not in this_run_wrote)))
```

`this_run_wrote` is what keeps the fourth clause honest: an executed test replaces its own
entry even when a skipped test in the same file carries the same proof id. Two wrong shapes
look close enough to pass a casual read and fail a real project:

- `keep(e) = e["feature"] != feature` alone reaps every entry of the feature on every run, so a
  project whose suite is split across two files keeps only whichever file ran last.
- An existence check resolved from the working directory rather than the project root reaps the
  whole feature whenever the framework starts the run below the root, which the .NET test
  platform always does.

## B. Wiring a new language

A plugin that only writes correct JSON is invisible. These are the places a framework has to be
named before a project can select it, a hook can run it, the quality gate can grade it and the
sweep can regenerate its evidence. Work down the list in order: each step assumes the one above
it landed.

| Step | Path | What it gains |
|------|------|---------------|
| 1 | `scripts/proof/` | The plugin itself, one file for the framework, meeting every rule of `specs/_anchors/proof_common.md`. |
| 2 | `references/supported_frameworks.md` | A row in the Built-in Plugins table (auto-detected) or the Additional Plugins table (manual wiring), with a non-empty **Runner setup** cell, plus a row in the Detection table when it is auto-detected. |
| 3 | `scripts/init/scaffold.py` | A `_DETECTORS` entry matching the reference's Detection cell, a `_WIRING` entry when init writes the framework's config file, and a `_DEST_OVERRIDES` entry when the installed name differs from the plugin's basename. |
| 4 | `scripts/hooks/pre_push_gate.py` | The framework id in `KNOWN_FRAMEWORKS`, so the hook resolves it instead of reporting it as a name Purlin does not know. |
| 5 | `scripts/hooks/pre-push.sh` | A runner arm in the framework `case`, so a push actually re-runs that suite instead of reading stale proof files. |
| 6 | `skills/init/SKILL.md` | Nothing hardcoded: the selection list is built from the reference. A framework wired by hand gains a line in the manual-setup note; one whose runner config init writes gains a row in the Step 4 wiring table. |
| 7 | `skills/test/SKILL.md` | The plugin path in the write-scoped overwrite paragraph, so the skill names the file that emits the project's evidence. |
| 8 | `docs/testing-workflow-guide.md` | A framework subsection under `## Proof Markers` showing the marker in that language. |
| 9 | `references/formats/proofs_format.md` | A framework subsection under `## Proof Markers by Framework`: marker syntax, platform markers, the runner command and the plugin path. |
| 10 | `references/audit_criteria.md` | A language subsection under `## Pass 1: Deterministic Checks`, listing what the checker flags and what it deliberately does not. |
| 11 | `scripts/audit/static_checks.py` | An entry in the `_CHECKERS` extension table and a branch in `_test_bodies`, so Pass 1 grades the language and the cache key covers a test edit. See section C. |
| 12 | `specs/proof/` | A per-plugin spec `proof_plugins_<framework>.md` declaring `> Requires: proof_common` and adding only the framework-specific rules. See section D. |
| 13 | `dev/test_multilang_proof_plugins.py` | One arm per behavioural test class, skipped for its own missing toolchain and for nothing else. |
| 14 | `dev/run_tests.sh` | The test file in the sweep, which is what makes the new evidence regenerable under `proof_common` RULE-14. |
| 15 | `specs/instructions/purlin_references.md` | RULE-3 pins the marker sections `proofs_format.md` documents; RULE-23 pins the non-empty **Runner setup** cell for every listed framework. |
| 16 | `specs/skills/skill_init.md` | RULE-48 pins the dynamically built selection list, RULE-50 the marker rewrite covering every shipped syntax, RULE-64 the runner wiring init writes, RULE-71 the `auto` expansion. |
| 17 | `specs/hooks/pre_push_hook.md` | RULE-5 pins how `test_framework` is read and how `auto` expands, in the reference's detection order. |
| 18 | `specs/instructions/purlin_agent.md` | RULE-4 pins the marker syntax the agent definition documents. |
| 19 | `specs/instructions/purlin_skills.md` | RULE-13 pins that `purlin:init --add-plugin` reads its per-extension patterns from section C of this file rather than a copy of its own. |

Steps 15 to 19 are the spec pins. They are the reason a wiring step cannot be skipped quietly:
each is a committed rule with a proof behind it, so a framework added to the reference and
nowhere else fails a test rather than shipping half wired.

Step 14 is this repository's arrangement and not a consumer's. A consumer project has no
`dev/run_tests.sh`, so nothing but the plugin itself is in a position to record that a run
happened at all: that is why `RULE-19` puts the run marker in the plugin's hands and `RULE-20`
puts the skipped markers in it. A plugin that writes correct proof files and no run marker
leaves every receipt that project issues carrying `evidence.test_run: null`, which says only
that some file on disk holds a `pass`. The marker's merge rule is what lets several plugins in
one project, and several runs of one plugin, add up to one record of the commit they all ran
at. The two silent failures to watch for while wiring are the same shape: `RULE-24` and
`RULE-25` both break after the tests have passed, so the suite goes green and what reaches the
repository is either nothing or a file that reads as complete and is not.

### What the eight shipped plugins registered

| Framework | Plugin file | Test extensions | Pass 1 checker | Cache-key extractor |
|-----------|-------------|-----------------|----------------|---------------------|
| pytest | `scripts/proof/pytest_purlin.py` | `.py` | `check_python` | yes |
| jest | `scripts/proof/jest_purlin.js` | `.js` `.jsx` `.mjs` `.cjs` `.ts` `.tsx` | `check_js` | yes |
| vitest | `scripts/proof/vitest_purlin.ts` | `.js` `.jsx` `.mjs` `.cjs` `.ts` `.tsx` | `check_js` | yes |
| shell | `scripts/proof/shell_purlin.sh` | `.sh` | `check_shell` | none, the documented exception |
| xunit | `scripts/proof/xunit_purlin.cs` | `.cs` | `check_csharp` | yes |
| phpunit | `scripts/proof/phpunit_purlin.php` | `.php` | `check_php` | yes |
| sql | `scripts/proof/sql_purlin.sh` | `.sql` | `check_sql` | yes |
| c | `scripts/proof/c_purlin.h` with `scripts/proof/c_purlin_emit.py` | `.c` `.h` | `check_c` | yes |

The extension column is what `_CHECKERS` in `scripts/audit/static_checks.py` holds, not a
second list: jest and vitest share one checker because they share one language, and the C
header and emitter are one plugin in two files.

## C. Checker and extractor

Every framework in the tables of `references/supported_frameworks.md` has a Pass 1 checker.
That is a requirement, not an observation. A registered framework with no checker is a hole in
the deterministic quality gate: its tests are graded `unmeasurable`, never HOLLOW, so
`assert true` in that language passes a gate that fails it in every other. The one honest
`unmeasurable` is a language no shipped plugin covers, which is a custom plugin's business and
never fails anything.

Every checked extension also has a cache-key extractor in `_TEST_CODE_EXTENSIONS`, with one
exception: shell. Its proofs are keyed on rule text and proof description alone and the cache
entry records `inputs.test_verifiable: false`, which states the limit rather than pretending a
test edit would invalidate the grade. Any other language without an extractor is a grade that
survives an edit to the very test it graded.

So a new language brings three things to `scripts/audit/static_checks.py`, not one:

1. a checker registered in `_CHECKERS` for each of its extensions, reading the same marker the
   plugin reads, so the audited function is the executed one;
2. a branch in `_test_bodies` returning the marked test's source, which is what puts the test
   body in the cache key;
3. a subsection in `references/audit_criteria.md` saying what the checker flags, so a false
   HOLLOW is a documented behaviour rather than a surprise in a blocked merge.

### What a plugin file must contain

`purlin:init --add-plugin` copies a plugin the user names and then checks it against one row
of this table, warning without refusing when the file does not match. The row is a smoke
check on a file nobody has run yet, not the contract of section A:

| Language | Must contain |
|----------|-------------|
| Python (`.py`) | `proofs` and `json` |
| JavaScript (`.js`) | `proofs` and `JSON` |
| TypeScript (`.ts`) | `proofs` and `JSON` |
| C header (`.h`) | `purlin_proof` function |
| PHP (`.php`) | `proofs` and `json_encode` |
| Shell (`.sh`) | `purlin_proof` function |
| C# (`.cs`) | `proofs` and `Proof` |

Every extension here is one a shipped plugin uses, which is why there is no `.java` row: no
plugin is written in Java, and a row for a language nothing ships tells the user a file will
be recognised when it will not.

## D. How to prove a plugin

Each rule of `specs/_anchors/proof_common.md` already has a proof there, and most of those
proofs are parametrised over every shipped plugin. Proving a new plugin is
therefore adding an arm, not writing a suite:

| Behaviour | Where its arm goes |
|-----------|--------------------|
| Spec resolution, fallback, the warning (`RULE-1`, `RULE-3`, `RULE-9`) | `TestFallbackWarningPerPlugin` in `dev/test_multilang_proof_plugins.py` |
| Required fields and platform scoping (`RULE-5`, `RULE-17`) | the field and scoping classes in the same file, one arm per plugin |
| Ordering (`RULE-21`) | the ordinal-order class, seeded with a kept sibling entry so the sort is proved to run after the merge |
| Project root and relative paths (`RULE-22`, `RULE-23`) | `TestProjectRootFoundByWalking` and `TestTestFileIsProjectRelative` |
| The run marker and skip records (`RULE-19`, `RULE-20`) | the run-marker classes, driven in a temp project holding `.purlin/` |
| Atomic writes and imports (`RULE-24`, `RULE-25`) | the temp-file and import classes, which read the plugin source and then run it |

Two things make an arm honest. It is skipped only for its own missing toolchain, so a host
without php still proves the other seven. And it drives the real plugin, through the framework
where the framework can be driven, rather than a reimplementation of the plugin's logic in the
test.

The per-plugin spec is short by design. `specs/proof/proof_plugins_<framework>.md` declares
`> Requires: proof_common` and carries only what the anchor cannot: the marker syntax, the
status mapping, the framework's own skip signal, and how the plugin is invoked. Everything
else is inherited, which is what keeps a change to the proof-file contract a change to one
anchor rather than an edit to eight specs.
