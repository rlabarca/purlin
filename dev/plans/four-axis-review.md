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

The table below is as of HEAD `86d6c1ec`, the verify commit, 146 commits after `3ac3a9fb`. The
rows through `ba78cfe3` were written at that commit; the close-out pass extended every stage and
added the four blocks after Stage 5.

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
| A5 paths and citations | `6c39f987`, after the Stage 3 skill trims had already repointed the format-file citations |

`6c39f987` landed A5 late, beside the lint widening that could enforce it. It adds
`## Path resolution` to `references/purlin_commands.md`, one pointer line to each of the twelve
skills, and the `banned_paths` rows that stop a shipped skill or reference naming this
repository's own `specs/` or `dev/` tree. 27 such citations were repointed or dropped, and
`paths_exist` widened to `skills/**.md` and `agents/**.md` so a plugin-relative path the plugin
root does not carry is reported by file and line.

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
| D1 L2 `skills/` and `agents/` | `4441b1ad`, plus `a30b4003` for the five `skill_init` dashes the lane had to leave behind |
| D1 L3 `references/`, `tools/` and `CLAUDE.md` | `1d99aabc` |
| D1 L4 and L5 `specs/` and the scripts' comment lines | `382863ca` |
| D1 the one-home partition of shipped prose | `6847cfa1` |
| D1 `paths_exist` on a fresh checkout | `f537e58f` |

D3 item 7's empty-live-keys guard was handed to the performance stage and landed there as
`6399f806`.

The widening ran as four commits, each atomic with its own dash sweep, and every dash was
rewritten by hand one line at a time rather than by a regex over the tree. The count fell 618 to
217 (`4441b1ad`), 217 to 134 (`1d99aabc`), 134 to 13 (`382863ca`), and to 8 once `skill_init`'s
last five went in `a30b4003`. The eight that remain are allowlisted program literals: the
`(assumed - <context>)` rule tag, which `scripts/mcp/purlin_server.py` matches with an em dash,
and the anchor header line `specs/mcp/sync_status.md` quotes character for character.
`6847cfa1` closed the other half of the scope question: three shipped files (`CLAUDE.md`,
`references/figma_extraction_criteria.md`, `references/rule_examples.md`) were in no spec's
`> Scope:` and thirty-two were in two, so `one_scope` now holds 44 prose files to 7 owning specs
with one owner each.

Adjacent defects:

- `paths_exist` read `.purlin/report-stamp.js` as a dangling link in any worktree that had not
  run a build. The stamp is gitignored generated state, so the lint was failing on a checkout
  rather than on a broken link. `f537e58f` adds `RUNTIME_PATHS`, carrying the same staleness bar
  as `PATH_ALLOWLIST` so a skip cannot outlive its justification.
- A `git checkout` during `6c39f987`'s mutation check reverted the pointer line in two skills.
  `4441b1ad` restores them and `6c39f987` was amended, so PROOF-18 is green at both commits.

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
| D5 flag consolidation | `952599cb`, `9c5d096d`, `2eddd650` |
| D6 non-skill spec refactors | `a225e2b3` |
| D6 `sync_status` | `beefa1dc`, `5ad5b6c7` |
| D6 dashboard and payload | `9afa0c43`, `2b1b88a6`, `4c1fcc70` |
| D7 concept reduction | `2f47c4b0`, `6eb2a86e`, `20dcad59` |

The retirements of `--list-plugins`, `--mcp`, `--anchor` and `--review` landed inside the D4
commits above. `952599cb` turns the five setting flags into `purlin:init --set <key> <value>`
with one five-row mapping table at Step 2, and keeps the old spellings as aliases until 0.12.0.
`2eddd650` documents `--set` and deprecates `purlin:test --local` on the same window, and drove
the lint's missing-Usage-flag note from 12 to 7.

D6 landed in five commits. `beefa1dc` replaces RULE-6's 460-word restatement of the vhash recipe
with a citation of `references/formats/receipt_format.md` and a two-sided proof: the segment list
parsed out of the format file and the one parsed out of `_compute_vhash` with `ast` must agree,
so a field added to either side alone fails naming the field. `5ad5b6c7` retires seven
`sync_status` rules that could only ever pass or fail with their twin, moving every proof under
the surviving rule. `9afa0c43` moves the two viewport rules to `specs/_anchors/dashboard_visual.md`
and makes seven dashboard rules stop pinning a pixel, a colour or a class. `2b1b88a6` retires two
`purlin_report` restatements and records why three more nominations were not restatements.
`4c1fcc70` reads all fourteen overlapping dashboard and payload pairs and finds every one of them
to be two contracts rather than one: the dashboard proof drives a browser and the payload proof
reads the JSON, so the rules stay and the field shape is stated once on the payload side and
cited from the dashboard.

Adjacent defects: `2e070ffa` removed the em dashes from the four lines the trim lane had
rewritten, ahead of the lint widening that will take the rest. `20dcad59` removed the
`(confirmed)` tag regex, which nothing ever wrote. `9c5d096d` found `purlin:init --mcp`, retired
by D4, still spoken by the `legacy-mcp` migrate directive and by `sync_status` RULE-38; both now
name `purlin:init --update` and the migration id. `2b1b88a6` found PROOF-14 satisfiable by the
wrong card: its second leg looked for `run purlin:audit` anywhere in the summary strip, which the
Design card supplied whatever the Integrity card did.

### Stage 4: terminology (C3a, C3, C4, C5, C6, C7). DONE

| Item | Commits |
|---|---|
| C3a the two-section format everywhere the docs describe it | `5bf66115` |
| C3 the `purlin:` prefix carries no slash | `02749479` |
| C3 the glossary and the canonical vocabulary | `97b4e568`, `82efa5de`, `7f28ce78` |
| C4 contradictions | `bb5517db`, `56ef7b70`, `d489b643`, `11f589f7`, `c87b5583`, `087bdf23`, `f452b407` |
| C5 deduplication and the rename coverage bug | `95c6244d`, `65247203` |
| C6 stale items | `f1e90cd5`, `33e1eba5` |
| C7 stakeholder tools | `7aac0d22`, `6a707b3b` |

`65247203` closed the rename coverage bug: both marker tables in `skills/rename/SKILL.md` covered
three of eight languages, so a rename silently lost Vitest, xUnit, C, PHP and SQL markers.

C3 landed in four commits. `02749479` takes the slash off all 40 sites of `/purlin:<skill>`,
including the three `pre_push_hook` proofs that assert the literal the hook scripts print.
`97b4e568` makes `references/glossary.md` the canonical term list, and its Retired table the
lint's source rather than its documentation: `dev/prose_lint.py` generates eleven `banned_strings`
rows from `GLOSSARY_RETIRED`, and the three rows that already enforced a retirement move into that
tuple so there is one list and not two. `82efa5de` settles the two concepts that still had more
than one name, the drift role (`pm`, `eng`, `qa` as positionals, no `--role` flag) and the CI gate
job (one name in all twenty-two prose lines, with `verify-gate` named once in the Layer 3 row).
`7f28ce78` makes the Quick Reference Purpose cell the one home of every skill one-liner: the
sentence lived in five places and agreed in none, `purlin:anchor` had four variants, and
`agents/purlin.md`, read on every turn, still described `purlin:audit` with one gauge and three
grades three releases after it grew two gauges and eight.

C4 read each contradiction beside the page it contradicts. `bb5517db` keeps the NEVER on
`--no-verify` and drops the claim that the pre-push hook is a safety gate, which
`references/hard_gates.md` and this repository's own `pre_push: off` both deny. `d489b643`
records the legacy-migration receipt refusal in the "What Is NOT a Gate" list, so a reader
meeting the behaviour has a page to check it against. `11f589f7` makes verify Layer 0 of four
rather than the last gate. `c87b5583` unnumbers the Core Loop and puts "there is no fixed order"
above the four moves, with PROOF-2 asserting the two offsets. `087bdf23` qualifies "skills are
optional": true of the user, false of the agent whose own NEVER list forbids writing a spec
outside one. `f452b407` stops the installation guide counting optional fields it then miscounts,
and names all six.

Adjacent defect, found in C4 and fixed there: `56ef7b70` found the audit Pass 2 prompt telling
the grader to answer ONLY six questions, which made it a second and shorter criteria file than
the one Step 1 loads. Deep mocking, assertion farming, the missing negative test, catch-all and
presence-only assertions, time dependence, fragile string parsing and the mutation criterion were
all outside the six, so a project that pinned an `audit_criteria` sha got a grade that never read
most of what it pinned.

C6's stale items: `f1e90cd5` found the quality guide, both authoring skills and the lifecycle
guide routing a new anchor to a `schema/` category, which `sync_status` does not read, so a spec
written there is a file nothing loads. `33e1eba5` found `skills/drift/SKILL.md` printing
`Criteria-Version: 1` two releases after `references/drift_criteria.md` reached 2, and five specs
still opening with the unreviewed-draft comment `purlin:spec-from-code` leaves behind.

### The `skill_init` rule consolidation. DONE

| Item | Commits |
|---|---|
| Byte-identity and detection rules retire | `23eca768` |
| Lifecycle, plugin-emission and selection-list rules collapse | `8168787a` |
| RULE-84's proof gets its test | `b79f9cc1` |

`skill_init` went 77 rules to 66 across the two consolidations, short of the plan's about 30,
because every retirement had to keep its proof body and repoint it rather than delete evidence.
Detection had one rule per heuristic, which froze the heuristic list at the frameworks those rules
named; RULE-12 now reads them from `references/supported_frameworks.md`, which the registry
already builds the selection list from.

Adjacent defects:

- `68977c0d`: the consolidation lane reworded RULE-53 to stand alone, and the landing rebase kept
  the branch's older text, which still read as an extension of the four rules it had absorbed.
  The lane's wording is back.
- `b79f9cc1`: a renumber during landing left the Step 5d audit-criteria test carrying `PROOF-90`
  and `RULE-83`, ids that now belong to the digest rebuild and the plugin backup in a different
  test file. The test takes PROOF-92 under RULE-84, which was the one unproved own rule of the
  spec, and `skill_init` reads 66 of 66.

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
| The two `purlin_prose` single-home proofs take free ids, the contract and docs lanes having already spent PROOF-24 and PROOF-25 | `a62eb304` |
| The `purlin_prose` version-literal and placeholder rules take free ids after the docs lane spent RULE-20, RULE-21, PROOF-28 and PROOF-29 | `80765a59` |
| Two lanes minted PROOF-34, the update lane for the Installed-as column and the trim lane for the legacy migration reference; the column proof takes a free id | `45f28fe3` |
| `skill_init` RULE-53's standalone wording, lost when the landing rebase kept the branch's older text | `68977c0d` |
| The sweep puts this repository's venv first on PATH, so one interpreter carries the shell suites and the pytest half alike | `45ee0a7a` |
| The living record itself, written at `ba78cfe3` | `c939a93e` |

### Stage close: sweep, counts line, receipts. DONE

| Item | Commit |
|---|---|
| The sweep follows the retired phrases and the compact drift JSON, and the tag proof skips | `8343d2cd` |
| The Unreleased counts line, and the version feature's regenerated proofs | `ada8c1a9` |
| The counts proof records its pass against the corrected line | `876d3657` |
| The verification receipts | `86d6c1ec` |

Adjacent defects, all found by the first full sweep after the terminology work:

- The vocabulary lane replaced "read-only and never edits code or tests" with "writes no code and
  no test files" in `skills/audit/SKILL.md` but not in the shell suite that asserts the sentence.
- The same lane rewrote the QA tool's prose without running `bash dev/pack_tools.sh`, so the
  packed `.skill` zip no longer matched its source and the byte-equality proof failed.
- The drift tool now serializes compact JSON, and the external-refs suite matched a key with a
  space after its colon that no longer exists in the output.
- `consumer_ci` PROOF-4 is red by design until the owner tags `v0.10.0`, and a red proof marked
  every sweep as failed, which the receipt issuer reads as no passing run at all. It now skips
  and names the owner action, so RULE-4 stays unproved and only `consumer_ci` goes without a
  receipt.

## Measurements

Before is the plan's Context table at `3ac3a9fb`. Now is measured at `86d6c1ec`, the verify
commit, on this machine, with the receipts freshly issued.

| Measure | Before | Now |
|---|---|---|
| `sync_status` output | 40,600 B | 16,932 B |
| `sync_status` wall time | 0.555 s | 0.296 s |
| `drift` output | 137,083 B | 4,342 B |
| `drift` wall time | 1.04 s | 0.141 s |
| `.purlin/report-data.js` | 2,861,261 B, 1 line | 1,691,339 B, 71 lines |
| Eight largest skills plus `agents/purlin.md` | 211,504 B | 191,497 B |
| All twelve skills plus `agents/purlin.md` | not measured before | 213,509 B |
| Live spec rules | 707 | 696 |
| Dashes in shipped markdown | 782 in 64 files | 8 in 92 files |
| Full sweep | 924 passed, 6 skipped | 1057 passed, 0 failed, 7 skipped across 15 suites |
| Receipts | not measured before | 39 of 42 features, 5 of 5 anchors |
| `python3 dev/prose_lint.py` | no module | exit 0 |

How Now was taken:

- Both tool measures from one process with `_write_report_data` stubbed out, so the digest write
  is not timed and the tracked file is not touched.
- Rule count from `find specs -name '*.md' -print0 | xargs -0 grep -h "^- RULE-" | wc -l`.
- Dash count over tracked `*.md` outside `dev/` and `RELEASE_NOTES.md`, counting occurrences.
- `prose_lint` exits 0 and prints one note, carried into the TODO below.
- The 8 remaining dashes are every one an allowlisted program literal: four in
  `skills/spec/SKILL.md` and two in `references/formats/spec_format.md` for the
  `(assumed - <context>)` rule tag the server matches with an em dash, and two in
  `specs/mcp/sync_status.md`, which quotes the anchor header line the server prints character for
  character. The 92 files are every tracked `*.md` outside `dev/` and `RELEASE_NOTES.md`; the
  before count of 64 files was taken over a narrower set.
- Three features are skipped rather than failing: `consumer_ci`, whose PROOF-4 skips until the
  owner tags `v0.10.0` and pushes `main`, and `figma_web` and `skill_spec`, which had no
  environment witness in the recorded run.

Four of these numbers need reading with care.

The `drift` figures are not like for like. The 137,083 B baseline was taken with 75 changed files
in the tree; the 4,342 B is a clean tree, where there is almost nothing for the tool to report.
The drift lane measured the same dirty tree on both sides: 142,549 B before its work and 75,980 B
after, which is the honest 47 percent cut. The clean-tree figure is here because it is what a
consumer meets on most turns.

`.purlin/report-data.js` is 41 percent smaller and is now 71 lines rather than one, which is the
change that matters more: a one-line file conflicts wholesale on every rebase, and a
one-line-per-key file takes a git delta.

Skill size is the measure furthest from its target. 211,504 B to 191,497 B is a 9.5 percent cut
against the plan's 44 percent. Two things account for it. The init, verify, test and drift trims
were scoped down so they would not collide with the consumer-mechanics lanes editing the same
files, and the flag consolidation added a five-row mapping table to `skills/init/SKILL.md` where
the plan had assumed it would only remove text.

The rule count is nearly flat, 707 to 696, and that hides the work rather than measuring it.
About 130 rules were retired across the branch and about 120 were added for the new behaviour,
so the count barely moved while the share of the specs that is prose restating another rule fell
sharply. Every retirement kept its proof body and repointed it, so no evidence was dropped to
make the number smaller.

## Audits

Both gauges were run for real at the verify commit by an independent auditor (18 parallel graders, every Pass 2 judgment fresh because the audit cache was empty; 885 of 885 proofs graded in both caches).

| Gauge | Score | Counts |
|---|---|---|
| Proof Design | 92 percent (91.8 assessed) | PROVABLE 659, LOOSE 59, UNPROVABLE 0, STRUCTURAL 167 (excluded) |
| Proof Integrity | 63 percent assessed over 667; 43 percent reported | STRONG 422, WEAK 141, HOLLOW 104, EXCLUDED 217, one stale MANUAL stamp (consumer_ci PROOF-3) |

The reported Integrity figure lags the assessed one because the reported denominator counts 1195 executed proof records while a grade is one per feature and proof id; the gauge, not the tests, is what disagrees, and it is worth a rule.

HOLLOW, all 104 from the deterministic Pass 1: logic mirroring 56, tautological assertion 26, no assertions 21, bare except 1. By feature: sync_status 18, purlin_report 15, skill_spec_from_code 15, report_data 10, skill_init 8, proof_common 6, static_checks 5, purlin_prose 4, the rest 3 or fewer. verify_gate PROOF-15 is a likely false positive (its `assert True` is fixture data).

Lowest Design grades, all LOOSE: sync_status PROOF-74 and PROOF-107 (expected value contradicts RULE-39 and RULE-68), skill_init PROOF-70 (contradicts RULE-67), skill_audit PROOF-13 (tautological clause), sync_status PROOF-103 (existence only), skill_spec_from_code PROOF-33 (expected output differs from the named input), security_no_dangerous_patterns PROOF-4 (imprecise FORBIDDEN grep), proof_plugins_pytest PROOF-3 and figma_web PROOF-6 (no expected value), purlin_report PROOF-4 (visual description coupled to the implementation).

Most consequential WEAK: figma_web PROOF-12 and PROOF-5, skill_build PROOF-13 to 16 (grep their own fixtures), proof_common PROOF-4 and PROOF-10 (reimplement the RULE-4 merge in the test), sync_status PROOF-32 and PROOF-45, dashboard_visual PROOF-10, proof_plugins_xunit PROOF-6, skill_verify PROOF-9, proof_plugins_jest PROOF-3, static_checks PROOF-29 to 32 (tier mismatch). 72 proofs are WEAK only under the mutation-on-record cap (the auditor derived mutation evidence from blame and commit bodies, having no author to ask); lifting that cap alone would put assessed Integrity at 74 percent.

Anchor recommendations from the auditor: schema_spec_format RULE-2 ("increasing, never reused" is unobservable as written) and RULE-5; schema_proof_format RULE-1 and RULE-3; dashboard_visual PROOF-3, 4, 5 and 11 inspect stylesheets without rendering.

Two audit-tool defects surfaced: `--prune-cache` prunes only the audit cache, so 66 orphan design-cache entries remain and read as invalidated; and the installed plugin's MCP server resolved a different project root than this checkout, so the auditor ran the repo's own server over stdio with `PURLIN_PROJECT_ROOT` set. Both are in the TODO.

## What still runs after this record

Nothing in the plan's stages. Stage 0 through Stage 5 and the parallel performance stage are all
DONE, the stage close has run, and the receipts are issued. What is left is owner work and the
deferred items, both in the TODO below.

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
- `RELEASE_NOTES.md:11` now reads 1057 passed and 7 skipped across 15 suites, matching
  `.purlin/runtime/last_sweep.json` at `876d3657`. That pair is settled, but the proof that holds
  it is self-referential and has to be handled at the tag.
- The `purlin_version` RULE-9 counts proof compares the Unreleased counts line against the
  previous sweep's record, and the proof's own outcome moves the number by one. A sweep whose
  count is written back into the line therefore reports a figure one different from the line it
  just corrected, and a fresh line can only converge after a local bootstrap of
  `.purlin/runtime/last_sweep.json` to the count a passing run produces, which is what `876d3657`
  did. Fix it properly one of two ways: count the sweep without this test, or compare with a
  tolerance of one.
- `skills/build/SKILL.md:99` still prints `purlin:init --mutation-checks on` in its advisory. It
  is an alias until 0.12.0, so the line works, but it teaches the retired spelling.
- `purlin:test --local` and the five `purlin:init` setting flags are aliases for one release and
  are removed in 0.12.0. `references/purlin_commands.md` states the contract once.
- The `(assumed - <context>)` parsed literal keeps an em dash by design, and the six sites that
  carry it are allowlisted in pairs so the exemption fails the day the separator changes. Any
  future retirement of the separator is an edit to `scripts/mcp/purlin_server.py`, to
  `references/formats/spec_format.md`, to `skill_spec` RULE-11 and to two end-to-end fixtures, in
  one commit.
- `python3 dev/prose_lint.py` exits 0 and prints one note: six `## Usage` flags are absent from
  `references/purlin_commands.md`, namely `purlin:anchor --check-only`, `purlin:anchor --source`,
  `purlin:init --audit-llm`, `purlin:init --ci`, `purlin:init --force` and
  `purlin:init --platform-id`. It is a count to drive down, not an offender.
- Integrity's reported denominator counts executed proof records (1195), not graded (feature, proof id) pairs (667): 43 percent reported against 63 percent assessed. Give the gauge one denominator, with a rule.
- `--prune-cache` prunes only the audit cache; 66 orphan design-cache entries read as invalidated. Prune both.
- The 104 HOLLOW proofs are the Integrity ceiling; the biggest single lever is the 56 logic-mirroring ones, and the `logic_mirroring` detector still flags before-and-after invariance tests (noted in the previous plan too).

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
- Two lanes that both add rules to one spec collide on ids, because each reads the maximum in its
  own checkout. Landing renumbers the later lane. Gaps are legal, so a free id above the range
  main is using is the cheap fix, and `a62eb304`, `80765a59` and `45f28fe3` are three instances
  of it. PROOF-34 was minted twice, once by the update lane and once by the trim lane.
- My list-aware rebase resolver keeps the branch's text where both sides edit the same rule id.
  That is right for a generated file and wrong for a reworded rule: a lane's rewording of an
  existing rule is silently dropped at landing. Re-read every reworded rule after landing.
  `purlin_prose` RULE-14 and `skill_init` RULE-53 were both restored this way, in `62ea1edf` and
  `68977c0d`.
- The `purlin_version` counts proof is self-referential: it compares the Unreleased counts line
  against the previous sweep's record, so its own pass or fail moves the number it is compared
  against. Converging a fresh line needs a local bootstrap of `.purlin/runtime/last_sweep.json`
  to the count a passing run produces. Recorded in the TODO with the two real fixes.
- The pre-commit delegator now carries a missing-shim guard, landed in `c101b77a`, so a lane
  whose checkout has no `.purlin/hooks/` commits cleanly instead of failing every commit.
