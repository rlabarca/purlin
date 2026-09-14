# The Proof Plugin Contract

A checklist, not a parsed format. It carries no `> Format-Version:` line because nothing reads it
as data: it is what a person follows when they write a proof plugin for a new framework, or read
one of the six Purlin ships.

The wire format a plugin writes is `references/formats/proofs_format.md`. Where the two disagree,
that file is right and this one is stale.

Three sections:

- **A. What a plugin must do**: the behaviour every plugin has, and the two legitimate shapes of
  the merge filter.
- **B. Wiring a new framework**: the ordered list of places a framework has to be named before a
  project can select it and a run can execute it.
- **C. How to prove a plugin**: which test proves which behaviour.

## A. What a plugin must do

1. **Read its framework's marker and nothing else.** The marker syntax per framework is in
   `references/formats/proofs_format.md`. A plugin reads one marker name, compared exactly: a
   trait or a decorator spelled in another casing is not a marker.
2. **Find the project root by walking up.** The nearest ancestor of the working directory, that
   directory included, holding `specs/` or `.purlin/`; the working directory itself when no
   ancestor holds either. A framework that starts its run below the root is the normal case, not
   the exception.
3. **Record `test_file` relative to that root, with `/` separators** on every operating system.
   Resolve whatever the framework hands over against the working directory first, so an absolute
   path and a relative one naming the same file record the same value. A file outside the root is
   measured from the nearest project root above the file itself, and left absolute when there is
   none; never rewritten with `../` segments.
4. **Write to `.purlin/runtime/proofs/<feature>.<tier>.json`**, one file per feature and tier,
   creating the directory when it does not exist.
5. **Emit all seven fields** on every entry: `feature`, `id`, `rule`, `test_file`, `test_name`,
   `status`, `tier`. No eighth. `status` is `"pass"` or `"fail"` and nothing else.
6. **Write nothing when no marker was collected.** A run of an unmarked suite leaves the proof
   files exactly as it found them.
7. **Merge write-scoped**, by the filter below, and sort the merged entries by
   `(id, test_file, test_name)` under plain ordinal comparison after the merge, so two runs of
   the same tests in any collection order write byte-identical files.
8. **Write atomically**: the whole file to `<path>.<pid>.tmp` beside the target, then one
   filesystem operation replacing the target. The temp name carries the writing process's own id,
   so two plugins writing one file in the same run never collide.
9. **Emit no entry for a test the framework did not execute**, and keep the entry that test
   already had. `"fail"` means it ran and its assertion failed.
10. **Fail loudly when markers were seen and nothing was written.** Print one line naming the
    features whose evidence went missing and exit non-zero. This is the one failure a test
    framework cannot report on its own: the suite goes green and what a reader sees is an earlier
    run's file.
11. **Refuse a retired marker keyword by name.** `platforms=`, `:on(...)`, `on(...)` and
    `PURLIN_PROOF_PLATFORMS` all named an operating system in the test. That claim now lives on
    the spec's proof line as `@env(windows)`, `@env(macos)` or `@env(linux)`. A plugin that meets
    one prints a line naming the replacement and fails the run, rather than writing an entry that
    reads as proved on a host that cannot prove it.
12. **Depend on the language's own standard library and the test framework, and nothing else.**
    A plugin that needs a package installed is a plugin that does not run in the project it was
    copied into.

### The two legitimate merge shapes

Requirements 7 and 9 meet in one expression, the filter that decides which existing entry
survives a write. There are exactly two correct shapes of it, and which one a plugin gets depends
on whether its framework reports a skip.

A skip-exempt plugin (shell, sql) writes the two-clause form:

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

`this_run_wrote` is what keeps the fourth clause honest: an executed test replaces its own entry
even when a skipped test in the same file carries the same proof id. Two wrong shapes look close
enough to pass a casual read and fail a real project:

- `keep(e) = e["feature"] != feature` alone reaps every entry of the feature on every run, so a
  project whose suite is split across two files keeps only whichever file ran last.
- An existence check resolved from the working directory rather than the project root reaps the
  whole feature whenever the framework starts the run below the root, which vstest always does.

## B. Wiring a new framework

A plugin that only writes correct JSON is invisible. These are the places a framework has to be
named before a project can select it, a run can execute it and a rename can rewrite its markers.
Work down the list in order: each step assumes the one above it landed.

| Step | Path | What it gains |
|------|------|---------------|
| 1 | `scripts/proof/` | The plugin itself, one file for the framework, meeting every requirement of section A. |
| 2 | `references/supported_frameworks.md` | A row in the Built-in Plugins table with a non-empty **Runner setup** cell, a row in the Detection table when it is auto-detected, and a row in the "Where each framework runs" table naming its arm. |
| 3 | `scripts/mcp/purlin/frameworks.py` | The framework id in `KNOWN_FRAMEWORKS` and a `_DETECTORS` entry matching the reference's Detection cell, so `auto` expands to it and a named value resolves instead of being reported as unknown. |
| 4 | `scripts/run/purlin_run.py` | A runner arm in `run_framework`, so a run actually executes that suite instead of reading an earlier run's proof files, and a `_MARKER_PATTERNS` entry reading the same marker the plugin reads, so a marked test that produced no entry is reported. |
| 5 | `scripts/init/scaffold.py` | A `_WIRING` entry when `purlin:init` writes the framework's config file, and a `_DEST_OVERRIDES` entry when the installed name differs from the plugin's basename. |
| 6 | `skills/init/SKILL.md` | Nothing hardcoded: the selection list is built from the reference. A framework wired by hand gains a line in the manual-setup note; one whose runner config init writes gains a row in the wiring table. |
| 7 | `skills/test/SKILL.md` | The plugin path in the write-scoped overwrite paragraph, so the skill names the file that emits the project's evidence. |
| 8 | `docs/testing-workflow-guide.md` | A framework subsection under `## Proof Markers` showing the marker in that language. |
| 9 | `references/formats/proofs_format.md` | A framework subsection under `## Proof Markers by Framework` (marker syntax, the runner command, the plugin path) and a row in the feature-name token table, which is what `purlin:rename` rewrites. |
| 10 | `scripts/review/static_checks.py` | An entry in the checker table for each of the framework's test extensions, reading the same marker the plugin reads, so the free checks grade the language instead of leaving `assert true` in it ungraded. |

### What the six shipped plugins registered

| Framework | Plugin file | Test extensions | Free-check reader |
|-----------|-------------|-----------------|-------------------|
| pytest | `scripts/proof/pytest_purlin.py` | `.py` | yes |
| jest | `scripts/proof/jest_purlin.js` | `.js` `.jsx` `.mjs` `.cjs` `.ts` `.tsx` | yes, shared with vitest |
| vitest | `scripts/proof/vitest_purlin.ts` | `.js` `.jsx` `.mjs` `.cjs` `.ts` `.tsx` | yes, shared with jest |
| xunit | `scripts/proof/xunit_purlin.cs` | `.cs` | yes |
| sql | `scripts/proof/sql_purlin.sh` | `.sql` | yes |
| shell | `scripts/proof/shell_purlin.sh` | `.sh` | yes |

Jest and vitest share one reader because they share one language and one marker.

### What a plugin file must contain

`purlin:init --add-plugin` copies a plugin the user names and then checks it against one row of
this table, warning without refusing when the file does not match. The row is a smoke check on a
file nobody has run yet, not the contract of section A:

| Language | Must contain |
|----------|-------------|
| Python (`.py`) | `proofs` and `json` |
| JavaScript (`.js`) | `proofs` and `JSON` |
| TypeScript (`.ts`) | `proofs` and `JSON` |
| Shell (`.sh`) | `purlin_proof` function |
| C# (`.cs`) | `proofs` and `Proof` |

Every extension here is one a shipped plugin uses, which is why there is no `.java` row: no
plugin is written in Java, and a row for a language nothing ships tells the user a file will be
recognised when it will not.

## C. How to prove a plugin

Proving a new plugin is adding an arm, not writing a suite. Every behaviour in section A already
has a test parametrised over the shipped plugins, in this repository's own behavioural suite for
the proof plugins:

| Behaviour | Where its arm goes |
|-----------|--------------------|
| The proof file's location, name and seven fields (A.4, A.5) | `TestTheRuntimeProofFile`, one arm per plugin |
| Write nothing without a marker (A.6) | `test_no_markers_no_proof_files` |
| The merge filter and orphan reaping (A.7) | `TestWriteScopedMergeKey` |
| Ordering (A.7) | the ordinal-order class, seeded with a kept sibling entry so the sort is proved to run after the merge |
| The project root and relative paths (A.2, A.3) | `TestProjectRootFoundByWalking` and `TestTestFileIsProjectRelative` |
| A skipped test keeps its entry (A.9) | `TestSkippedTestKeepsItsEntry` |
| Markers seen and nothing written (A.10) | `TestSeenMarkersAndNoEntryFails`, plus the run script's own two loud-failure checks |
| A retired keyword refused (A.11) | `TestRetiredKeywordRefused` |
| Atomic writes and no third-party import (A.8, A.12) | the temp-file and import classes, which read the plugin source and then run it |

Two things make an arm honest. It is skipped only for its own missing toolchain, so a host
without `dotnet` still proves the other five. And it drives the real plugin, through the
framework where the framework can be driven, rather than a reimplementation of the plugin's logic
in the test.
