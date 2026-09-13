<!-- Checked-in working plan. This copy is authoritative: the original lived in a
     per-user ~/.claude/plans/ directory that does not travel between machines.
     Update this file as phases complete, in the same commit as the work. -->

# Four-axis review (2026-09-12): consumer install, terminology, elegance, performance

The living record for the four-axis review of the framework. Written as the phases land, per the
convention in `dev/plans/README.md`.

## Context

Four Opus explore sweeps and four Opus design passes measured this repository on four axes:
terminology and intent consistency across docs, skills, agents, references, specs and tools;
elegance, meaning overwrought implementations and concepts; performance, meaning tokens injected
into context, wall-clock time and file sizes; and the marketplace consumer's experience, verified
against two real consumer projects on this machine, both stuck on 0.9.5. The review measured this
because the repository develops itself with itself, so every prompt it ships is also a prompt it
pays for on every turn, and because nine consumer paths were broken after a plugin update. The
owner decided on 2026-09-12 to continue on `two-gauges-remote-verification`, to retire
`## What it does` entirely, to drop `model:` from both shipped agents, and to let an `sh` wrapper
resolve the interpreter. The standing constraints held throughout: every rule change ships with a
PROVABLE proof and a mutation check in the same commit, no new skills, no em or en dashes, specs
refactored rather than patched, and `main` never merged or pushed by an agent.

## Reconciled design decisions

Where the four designs disagreed, this is the resolution that executors followed.

| Topic | Decision |
|---|---|
| Lint owner | One spec: `purlin_docs` renamed to `purlin_prose`, module `dev/prose_lint.py`, proofs in `dev/test_purlin_prose.py`. Terminology work adds rows to its tables. |
| Rule retirement | Delete, leave the number vacant, never renumber. Gaps are legal. |
| Digest version field | `schema_version`, integer, top-level. Consumer migration id `digest-schema-old`. |
| Dashboard | Copy always, with a `dashboard-stale` migration. Stale-root-copy detection dropped. |
| Hook plugin-root resolution | Generated shims in `.purlin/hooks/` own resolution; the duplicated block leaves both hook scripts. |
| `role` parameter and `manifest.json` | Both deleted as dead. Drift keeps a positional role in prose only, tokens `pm`, `eng`, `qa`. |
| vhash formula | Already in `references/formats/receipt_format.md`. No move, no version bump. |
| Format-Version bumps | `spec_format` 9 to 10; `anchor_format` 5 to 6; `proofs_format` 6 to 7; `supported_frameworks` 6 to 7. `receipt_format` stays 4. |
| `references/` paths in skills | No prefixing of 115 paths. One pointer line per SKILL.md to the path-resolution anchor, and a `paths_exist` lint. |
| `--update` | Stays inside `purlin:init`. No new skill. |
| Kept against findings | Box-drawing table; `_split_proof_tags` duplication; `PURLIN_DEV_RELOAD`; single-element tables; the `_load_payload` pair; `design_cache.json` format; `is_deferred` and `is_assumed` on own rules. |
| Deferred | Proof-plugin common module; STRUCTURAL plus EXCLUDED merge; UNTESTED into PARTIAL; hiding the vhash; `config.local.json`; init's three questions; the `> Stack:` merge. Recorded below. |
| Owner-only prerequisite | Tag `v0.10.0` and push `main`. A rule lands red until the owner tags. |

## Stages

The table below is as of HEAD `ba78cfe3`, 105 commits after `3ac3a9fb`. More lands after this
record is written; the close-out pass extends the table.

### Stage 0: quick wins (P1, P2, P8). DONE

| Item | Commits |
|---|---|
| P1 anchor dump collapse | `ec990106` |
| P2 drift batch diff and compact JSON | `722408c3`, `592c2b44` |
| P8 dead code | `acd77987`, `7af4edca`, `9481f74a`, `b423b3bb` |

Adjacent defect, fixed here: three plugin proofs shelled out to a bare `python3 -m pytest`, so on
a machine whose PATH `python3` is not the interpreter running the suite they failed for a reason
that had nothing to do with the plugin. Here the venv has pytest and the PATH `python3` does not,
so four proofs failed on every run. `e9bf2cf6` moves them to `sys.executable`. Harness fix, so no
rule and no spec edit.

### Stage 1: consumer mechanics (A1, A2, A3, A7, A5 partial). DONE

| Item | Commits |
|---|---|
| A1 hooks and dashboard survive a plugin update | `d45b50b0`, `ba7fc2be`, `9582d81c`, `0027b7bb`, `b554f23d` |
| A2 `--update` repairs everything | `071f40e6`, `c101b77a`, `202d7ca4`, `8765bfcc`, `d2a413bd`, `ec156355`, `6b4bd135` |
| A3 interpreter resolver | `ac485ca9`, `5db41736`, `67f07cd9` |
| A7 detection precision and `spec_dir` retirement | `b135f325`, `93343e13`, `b244eb86` |
| A5 paths and citations | folded into the Stage 3 skill trims, which cite the format files rather than this repository's specs |

Adjacent defects:

- The delegator written into the git hooks slot used to `exec` the shim blind, so any checkout
  without `.purlin/hooks/` (an older branch, a pre-init commit, a worktree sharing the hooks
  directory) failed the hook and blocked every commit made there. `c101b77a` gives it a guard
  that names the missing path, says what to run, and exits 0.
- The per-file hooks-stale summary is joined as `<path> is <reason>`, and the shim reason began
  with a verb, so the advisory read `is differs from`. `b3a9fe61` makes the reason a predicate.

### Stage 2: lints, boilerplate, correctness (D1, D2, D3). DONE

| Item | Commits |
|---|---|
| D1 L0 vacant rule numbers | `3d9e98e5` |
| D1 L1 the lint module at today's scope | `f7bbdbe3` |
| D2 boilerplate collapse | `f23115f2`, `735582e0`, `e0412a57` |
| D3 eight correctness fixes | `a5464d3d`, `d4edb087`, `9313d0b7`, `f2520041`, `6acc6b9f`, `2ac32c1c`, `dd128299`, `846fa509` |

D1 L2 through L5, the widening of the lint to `skills/`, `agents/`, `references/`, `specs/` and
`scripts/` with the dash sweep, has not landed. D3 item 7's empty-live-keys guard was handed to
the performance stage and landed there as `6399f806`.

### Stage 3: trim and refactor (D4, D5, D6, D7). DONE

| Item | Commits |
|---|---|
| D4 spec-from-code | `08be5ba6`, `408d6982`, `4ce5b081`, `2e070ffa` |
| D4 audit | `783c5a3e`, `180cc815` |
| D4 init | `3a8871bb` |
| D4 spec | `af8b3d69` |
| D4 verify | `a86312e0` |
| D4 build | `203f4e61` |
| D4 test | `fc905894` |
| D4 drift | `12255e20` |
| D4 agent | `4d43687c`, `a0ea6676`, `0e75c418` |
| D6 non-skill spec refactors | `a225e2b3` |
| D7 concept reduction | `2f47c4b0`, `6eb2a86e`, `20dcad59` |

D5's flag consolidation, the `--set` form and the alias window, has not landed; the retirements
of `--list-plugins`, `--mcp`, `--anchor` and `--review` landed inside the D4 commits above. D6's
`sync_status`, `purlin_report` and `report_data` consolidations have not landed.

Adjacent defects: `2e070ffa` removed the em dashes from the four lines the trim lane had
rewritten, ahead of the lint widening that will take the rest. `20dcad59` removed the
`(confirmed)` tag regex, which nothing ever wrote.

### Stage 4: terminology (C3a, C5, C6, C4, C7). Partial

| Item | Commits |
|---|---|
| C3a the two-section format everywhere the docs describe it | `5bf66115` |
| C5 deduplication and the rename coverage bug | `95c6244d`, `65247203` |
| C7 stakeholder tools | `7aac0d22`, `6a707b3b` |

C3's glossary and the rest of the canonical vocabulary, C4's contradictions pass and C6's stale
items have not landed. `65247203` closed the rename coverage bug: both marker tables in
`skills/rename/SKILL.md` covered three of eight languages, so a rename silently lost Vitest,
xUnit, C, PHP and SQL markers.

### Stage 5: consumer docs, CI, root (A4, A6, A8). DONE

| Item | Commits |
|---|---|
| A4 docs stop lying | `dc3d0186`, `3ac252f5`, `d7c1bf04`, `c3926dab`, `b1b42c75`, `ba78cfe3` |
| A6 CI for consumers | `30212a2c`, `7494f7e5`, `9aa70de6`, `fd9556c4` |
| A8 project root | `9c00cc10`, `90666da2` |

`9aa70de6` lands `consumer_ci` RULE-4 red on purpose: the documented clone ref is a tag that does
not exist until the owner tags `v0.10.0`.

### Parallel: performance (P3, P4, P5, P6, P7, P9). DONE

| Item | Commits |
|---|---|
| P3 pytest tier markers | `7988cd6e`, `1604c76f`, `5c3eaf86` |
| P4 sync_status time | `3bbbc69f`, `d0ce993c`, `d051c2a7`, `e8568dda` |
| P5 drift rule_details | `2393b1fd`, `f3d298f3`, `78e0cf62` |
| P6 digest hygiene | `21912890`, `48ce15ad`, `3c92c489`, `842a4564`, `9c1e517a` |
| P7 digest de-dup | `62ce8ca0`, `78e7a6e4`, `92735c6d` |
| P9 static_checks | `604791b6`, `34004b04`, `f160f7df`, `6399f806` |

Adjacent defects:

- P5 turned up nondeterminism in `rule_details`. The changed-behavior specs were walked as a set,
  so the order of the block was a fresh accident of string hashing in every process and two
  identical calls returned different bytes. `2393b1fd` sorts the walk by spec name and proves it
  under `PYTHONHASHSEED` 0 and 1. The same commit found `total_rules` counting a feature's own
  rules while `proved_rules` counted own plus inherited: `proof_plugins_sql` reported 2 rules with
  41 proved.
- P4 regressed the spec tree. `_spec_index` replaced a recursive glob with one `os.walk` and
  indexed `files` alone, but a directory named `<feature>.md` lands in `dirs`, so the index
  stopped holding it. `_scan_specs` opens every spec path with no guard, and that open is how a
  broken spec tree is heard, so `generate_digest` scanned zero features and returned None instead
  of raising, and the pre-commit hook took its silent branch. Found by `git bisect run`, fixed in
  `a1e62064` by indexing `files + dirs`.

### Integration fixes across lanes. DONE

| Fix | Commit |
|---|---|
| The `_spec_index` files-only regression from P4 | `a1e62064` |
| `purlin_prose` RULE-14 restored to name the model-field absence the structure lint enforces, after the skill-trim lane reworded it | `62ea1edf` |
| This repository carries its own hook shims, as `purlin:init` now writes them | `24468eca` |
| `purlin:init --update` refreshed this repository's hook shims | `d3e0a8dd` |
| A proof id collided with one main had already handed out; renumbered into a free range | `6d315cea` |
| The update rules take free ids after a rebase | `c68626a1` |
| The rebase's duplicated rule lines go | `dce9fa18` |

## Measurements

Before is the plan's Context table at `3ac3a9fb`. Now is measured at `ba78cfe3` on this machine.

| Measure | Before | Now |
|---|---|---|
| `sync_status` output | 40,600 B | 33,747 B |
| `sync_status` wall time | 0.555 s | 0.361 s |
| `drift` output | 137,083 B | 102,633 B |
| `drift` wall time | 1.04 s | 0.656 s |
| `.purlin/report-data.js` | 2,861,261 B | 1,623,582 B |
| Eight largest skills plus `agents/purlin.md` | 211,504 B | 189,652 B |
| All twelve skills plus `agents/purlin.md` | not measured before | 210,903 B |
| Spec rules | 707 | 701 |
| Dashes outside the enforced scope | 782 in 64 files | 629 in 50 files |
| `python3 dev/prose_lint.py` | no module | exit 0 |

How Now was taken:

- Both tool measures from one process with `_write_report_data` stubbed out, so the digest write
  is not timed and the tracked file is not touched.
- Rule count from `find specs -name '*.md' -print0 | xargs -0 grep -h "^- RULE-" | wc -l`.
- Dash count over tracked `*.md` outside `dev/` and `RELEASE_NOTES.md`, counting occurrences.
  Counting matching lines instead gives 588 in the same 50 files.
- `prose_lint` exits 0 but prints one note: twelve `## Usage` flags are absent from
  `references/purlin_commands.md`. D5 owns that.

The byte and time targets in the plan assumed the whole program had landed. Skill size is the
measure furthest from its target, because D4 moved rules and pointers ahead of the prose cuts the
lint widening will finish.

## What still runs after this record

- The lint widening: `dev/prose_lint.py` from today's enforced scope out to `skills/`, `agents/`,
  `references/`, `specs/` and `scripts/` comment lines, each widening atomic with its dash sweep.
- The glossary and the canonical vocabulary pass: `references/glossary.md`, the retired-terms
  table the lint reads, the anchor-spec and role vocabulary, `purlin:<skill>` with no slash.
- The init rule consolidation: `skill_init` from 75 rules to about 30.
- The flag consolidation: `purlin:init --set <key> <value>`, the alias window, `test --local`
  deprecated, and the twelve Usage flags added to `references/purlin_commands.md`.
- The `sync_status` and dashboard spec consolidations: `sync_status` 66 rules to about 52,
  `purlin_report` and `report_data` to about 40 together, the two viewport rules moved to
  `specs/_anchors/dashboard_visual.md`.
- The stale-items pass and the contradictions pass.
- The stage close: the full `dev/run_tests.sh` sweep, the `RELEASE_NOTES.md` count line, the
  receipts re-issued by `purlin:verify`, and both audits, Proof Design and Proof Integrity.

## TODO before pushing main

- tag v0.10.0 and push main; consumer_ci PROOF-4 is red until then; flip the fixture's `two-gauges-remote-verification` pin in the same commit
- Deferred concept merges. The decisions table defers each; it records a reason only for the
  first.

  | Deferred | Reason |
  |---|---|
  | Proof-plugin common module | Three blockers: `proof_common` RULE-16 and RULE-25 forbid non-stdlib imports; there is no missing-copy detector, so a project whose copy of the module is absent fails silently; jest's CJS cannot import a `.mjs` module. Unblock in that order: write the missing-copy detector, then rewrite RULE-16 and RULE-25 with PROOF-20 and PROOF-31, then land the module for the Python plugins only. |
  | STRUCTURAL and EXCLUDED merged into one status | Two names the review counted as one idea. No further reason recorded. |
  | UNTESTED folded into PARTIAL | UNTESTED is PARTIAL with 0 of N proved. No further reason recorded. |
  | The vhash hidden from the user | A concept a consumer does not need to meet. No further reason recorded. |
  | `config.local.json` | A second config file a consumer meets. No further reason recorded. |
  | Init's three questions | No further reason recorded. |
  | The `> Stack:` merge | No further reason recorded. |

- `dev/test_proof_plugins.sh`, `dev/test_init_e2e.sh` and `dev/test_e2e_build_changeset.sh` still
  shell out to a bare `python3 -m pytest`. `e9bf2cf6` fixed the Python callers with
  `sys.executable`; these shell suites have no equivalent and fail on a host whose PATH `python3`
  lacks pytest. They pass here only because `dev/run_tests.sh` is run with the venv's `bin` on
  PATH.
- `RELEASE_NOTES.md:11` claims 1001 passed and 7 skipped across 15 suites.
  `.purlin/runtime/last_sweep.json` records 924 at a lane commit. `purlin_version` RULE-9 checks
  one against the other, so the line needs a full `dev/run_tests.sh` sweep at the final commit
  before the tag.

## Execution notes

- Lanes must branch from the branch tip, not from an older commit. When a lane's base lane was
  itself rebased, rebase the lane with `--onto` from its true fork point: a plain `git rebase`
  replays commits the base already carries and conflicts on every one of them.
- The pre-commit delegator is installed in the git hooks directory, which worktrees share through
  the common git dir. Until the guard in `c101b77a` landed, the delegator `exec`ed the shim blind
  and every commit in a lane whose checkout lacked `.purlin/hooks/` failed.
- `.purlin/report-data.js` and the regenerated `specs/**/*.proofs-*.json` conflict on every
  rebase, because both are generated and both are tracked. Resolve by taking the branch's copy
  and letting the next hook run regenerate.
- A fresh worktree lacks the gitignored `.purlin/report-stamp.js`, so `prose_lint`'s path check
  fails on it until the file is copied in from the main tree.
- Rule ids and proof ids collide across parallel lanes, because each lane reads the maximum in its
  own checkout. They are renumbered at landing; gaps are legal, so taking a free id above the
  range main is using is the cheap fix.
- `dev/run_tests.sh` needs `/opt/homebrew/opt/dotnet@8/bin` on PATH for the xUnit projects, which
  target net8.0 while this host's default `dotnet` is 10.x, and it needs the venv's `bin` so the
  hooks' `python3` has pytest. Run
  `export PATH=$PWD/.venv/bin:/opt/homebrew/opt/dotnet@8/bin:$PATH` first.
- A `git bisect run` driven from a worktree leaked `GIT_DIR` into the temp-project tests, which
  then wrote into the main checkout's `.git/config`. The config had to be restored by hand. Unset
  `GIT_DIR` and `GIT_WORK_TREE` in the bisect script, or bisect in a clone.
