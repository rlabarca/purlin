<!-- Checked-in working plan. This copy is authoritative: the original lived in a
     per-user ~/.claude/plans/ directory that does not travel between machines.
     Update this file as phases complete, in the same commit as the work. -->

# Two gauges everywhere, honest roll-ups, and remote verification

## Status: Phases 0-5 COMPLETE and committed. Phases 6-7 superseded; see platform-generic-remote-verification.md

Baseline at handoff: **578 passed, 21 skipped, 6 suites, 41/41 VERIFIED**, working tree clean
(except `.claude/settings.json` and `.claude/settings.json.bak`, which must stay uncommitted).
Head of the work is `9a748f5a`.

### Branch and merge-back (read this first)

**All work lives on branch `two-gauges-remote-verification`.** Stay on it. Do not commit to `main`
and do not merge or rebase onto `main` without being asked.

`origin/main` is 38 commits behind this branch: every phase of this plan, plus the v0.10.0
follow-up work that preceded it, is unpushed on `main` locally on the originating machine. On a
fresh clone `main` therefore looks ancient; that is expected, and the branch is the truth.

The merge back to `main` happens **when the whole plan is done and the user says so** — not per
phase. Until then, keep committing to the branch in the same rhythm the log already shows: a
`feat(...)`/`fix(...)` commit carrying the work, then a separate `verify:` commit carrying the
re-issued receipts.

---

## Context

v0.10.0 split proof quality into two independent gauges:

- **Proof Design** (PROVABLE / LOOSE / UNPROVABLE, STRUCTURAL excluded): is the proof
  *description* falsifiable? Measurable before any code or test exists.
- **Proof Integrity** (STRONG / WEAK / HOLLOW / MANUAL, EXCLUDED excluded): does the *test*
  honestly demonstrate the rule?

The split reached the dashboard's summary strip and stopped. Phases 0-2 carried it the rest of
the way through both reporting surfaces. Phases 3-7 extend it to runner-gated proofs, remote
execution, and the docs and diagrams.

### Decisions taken (binding)

| Question | Decision |
|---|---|
| Roll-up over partial data | Gauge states its denominator; amber below full coverage; rows never blank |
| Where remote execution lives | `purlin:test`, **not** `verify`. `verify` stays read-only and inherits it by delegation |
| Remote trigger | The skill detects proofs that cannot execute on this host and offers setup then |
| Gating | Required check plus auto-merge only when the project declares remote verification required; mode visible in `purlin:status` and the dashboard |
| Runner-gated proofs | Warn, never block |
| Tier 3a | Prerequisite, lands before any CI commit-back |

---

## DONE — Phase 0: renames (`03fe26f5`)

- `purlin:unit-test` → `purlin:test`. Skill dir, frontmatter, `skill_unit_test` spec → `skill_test`
  (with proof and receipt files, via `git mv`), and 29 files of references. No alias: breaking,
  with an upgrade note in RELEASE_NOTES.
- `purlin:verify --audit` → `purlin:verify --recheck`. The old flag collided with the
  `purlin:audit` skill; `docs/anchors-guide.md` carried an inline parenthetical explaining they
  were different things, now deleted.
- Historical RELEASE_NOTES entries deliberately left alone. They record what shipped.

## DONE — Phase 1: per-feature Design, honest roll-ups (`b954dd0f`, `0ef43e4f`)

- `_read_audit_cache_by_feature` parameterized by cache name (the two caches are shape-identical);
  `_build_feature_design` mirrors `_build_feature_audit`.
- `audit` and `design` are now always objects carrying `state` ∈ measured / excluded / unmeasured
  and their own `coverage`. Never null, so no cell is blank.
- Both summaries carry `coverage {measured, total, complete}`. Integrity's population is executed
  proofs; Design's is declared proof descriptions.
- Dashboard: sixth column (Design before Integrity), one `gaugeCell` helper, one `gaugeCard`
  builder, colspans 4 and 6, `min-width` 830px.
- New rules: `report_data` RULE-25/26/27/28, `purlin_report` RULE-4 amended + RULE-35/36,
  `dashboard_visual` RULE-10 generalized.
- Adjacent fix: `purlin:rename` never touched the quality caches, so the Phase 0 rename orphaned
  six graded descriptions (`skill_rename` RULE-4).
- `dev/test_report_data.py` and `dev/test_purlin_report.py` added to the sweep.

## DONE — Phase 2: `purlin:status` reports and recommends (`b0e7e67f`, `b5c956d0`, `a762a9a1`)

- Summary table gains Design and Integrity columns; summary line carries each gauge's coverage
  and its own age; `skills/status/SKILL.md` prints the server's line rather than a substitute and
  gained a Gauge Recommendations step.
- Gauge-driven directives: Design findings → `purlin:spec`, Integrity WEAK/HOLLOW →
  `purlin:build`, unmeasured → `purlin:audit`, Design first.
- New rules: `sync_status` RULE-18/39 amended, RULE-25 rewritten, RULE-43/44/45;
  `purlin_report` RULE-15 amended + RULE-37; `skill_status` RULE-6/7/8.

### Four defects found and fixed during Phase 2, all specced

1. **One `/audit 78d ago` label for two independent caches.** The header read the Integrity
   cache's age as the project's; a repo graded for Design an hour earlier showed 78 days stale.
   Now one label per gauge, and `design_summary` gained the staleness flag it never had.
2. **Blanket refresh directive.** A stale gauge now names the narrowest command:
   `purlin:audit --design`, `--integrity`, or bare when both are stale. Design grading is free;
   Integrity grading costs LLM calls.
3. **`excluded` claimed from a subset.** `skill_audit` read `excluded` off 2 assessments while 18
   executed proofs were never looked at. It now requires full assessment coverage; a partially
   assessed feature reads `not audited`.
4. **The two vocabularies mixed.** A Design cell read `excluded`, but Design's unscorable level is
   STRUCTURAL. Design now reads `structural`.

Presentation, per review: whole words rather than `excl`, and each state coloured by meaning
(teal = correct terminal state, amber = needs an audit run). Gray is retired from the gauge
columns.

---

## DONE — Phase 3: Tier 3a, the merge key gains test_file (`3efadf32`)

Merge key `(feature, tier)` → `(feature, tier, test_file)` across all eight plugins plus this
repo's four stale `.purlin/plugins/` copies. An entry survives only if it belongs to another
feature, or its test file was not in this run AND still exists.

- `proofs_format.md` went to **Format-Version 4**, not 3: 3 was already spent on the xUnit
  plugin in `db08fe1c`. The section is renamed Write-Scoped Overwrite, so `purlin_references`
  RULE-2 and its grep moved with it.
- New `proof_common` RULE-11 (orphan reaping: a deleted or renamed test file is reaped) and
  RULE-12 (the bound: a marker removed from a file that is not re-run stays until that file
  runs again). RULE-4 rewritten, RULE-10 narrowed to "the same test file".
  `schema_proof_format` RULE-5 rewritten with a new PROOF-8.
- **The bug was live here.** `dev/run_tests.sh` excluded 26 of 45 dev test files and its header
  said why. Running three of them deleted 1064 lines of other files' proofs, which is why
  `proof_common` PROOF-10/11/12 were specced but absent from every committed proof file. Four
  suites joined the sweep: 484/8/5 → 548/21/6, every proof file gaining, none losing.
- Adjacent: the shell harness recorded a different `test_file` for `bash dev/x.sh` than for
  `bash /abs/dev/x.sh`. The old feature-wide purge collapsed that; the new key accumulated it as
  two entries for one proof with conflicting statuses. `BASH_SOURCE` is now absolutized at call
  time and relativized at write time (`proof_plugins_shell` RULE-5, which already promised it).
- Adjacent: PROOF-12 hand-wrote a 1-of-2 proof file, proving sync_status reads what is on disk
  rather than that anything was purged. Two tests marked PROOF-10/RULE-10 against a spec that
  assigns PROOF-10 to RULE-4, one of them writing its two runs to different files. All repointed
  and rewritten.

## DONE — Phase 3.5: gauge toplines are coverage-weighted (`0638da97`)

Not in the original plan; requested mid-session. The dashboard headlined Proof Integrity at 100%
while 39 of 40 feature rows read `not audited`.

    reported = passing / (gradeable + unmeasured)

Design 91% → 85%, Integrity 100% → 2%. At full coverage it equals the assessed score exactly, so
the gauge does not change meaning as coverage fills in. The assessed score is kept and reported
beside the denominator, because thin coverage needs a wider audit while bad proofs need better
tests. The amber-on-incomplete override is gone: it now promotes a genuinely red gauge.

`sync_status` RULE-46 is the new rule; RULE-31/39 and `report_data` RULE-27 name both figures.
The pinned formulas in `audit_criteria.md` / `audit/SKILL.md` / `sync_status.md` are untouched —
they are what `assessed` means. Adjacent: the coverage sub-label was dim 10px grey and now
carries its own colour band; the summary strip tiled seven cards into four columns below 1500px,
leaving a card-sized hole (`purlin_report` RULE-38, PROOF-40).

## DONE — Phase 4: runner-gated proofs (`01c04dc4`)

- `windows` named as the one **runner-gated** tier (`_RUNNER_GATED_TIERS`). A proof declaring it
  with no result there reports `AWAITING RUNNER`, distinct from `NO PROOF`. Warn, never block:
  out of the coverage denominator, receipt still issued with an `awaiting_runner` list
  (`skill_verify` RULE-9). Verified: deleting the windows proof file yields AWAITING RUNNER for
  PROOF-53/54 at an unchanged 35/35 PASSING, where before it yielded a silent VERIFIED.
- Provenance from `git log -1` on the tier file plus the commit's `Purlin-Runner:` trailer.
  Zero new fields, asserted by PROOF-80.
- The three "cannot run here" conventions unified under `proof_common` RULE-13: `status` records
  execution, never availability. Phase 3's merge key is what makes emitting nothing safe.
  `test_e2e_cross_model_audit.sh` no longer writes `fail` when gemini is absent;
  `test_e2e_figma_web.py` gates on `PURLIN_E2E_FIGMA` (gating on `claude` on PATH still errored,
  because the missing piece is the Figma MCP server). PROOF-17 scans for the pattern.
- **Adjacent, and the reason the two surfaces disagreed:** four places computed "which rules
  count" independently, one under a comment reading "must match _report_feature's counting
  logic". The table said 1/2 PARTIAL while the detail said 1/1 PASSING. Extracted to
  `_active_rule_entries`.
- Adjacent: `report_data` RULE-19 had no declared PROOF line despite a test emitting PROOF-19
  for it — a `schema_spec_format` RULE-4 violation sync_status cannot see, because coverage
  counts executed proofs rather than declared ones. It was the only one in the project.
- `@windows` documented in the `spec_quality_guide` tier table, `spec_format.md`,
  `testing-workflow-guide.md` and Pass D's implausible-tier criterion.

### Not done in Phase 4, deliberately

`purlin:test` has **no remote path yet** — that is Phase 5. The AWAITING RUNNER directive says
"run these on a host for that tier and commit the proof file it writes" rather than promising
setup assistance that does not exist. Update it when Phase 5 lands.

A receipt issuer now lives at `dev/issue_receipts.py`, driving the server's own
`_build_coverage_rules` / `_collect_relevant_proofs` / `_compute_vhash` / `_awaiting_runner`. It
is committed, so the Execution note about rewriting it from scratch is obsolete.

## DONE — Phase 5: remote execution inside `purlin:test` (`7c80c286`, receipts `9a748f5a`)

Phase 4 made an unproved `@windows` tier visible as `AWAITING RUNNER` but nothing could close the
gap, so its directive deliberately promised no setup. Phase 5 made the promise true and the
directive now names `purlin:test`.

- **`skills/test/SKILL.md`**: Step 1.5 classifies tiers before the first test runs; Step 2b is the
  remote path (push, dispatch, await, pull) bounded at 3 rounds; Step 3 reports remotely-proved
  separately, sourcing the runner from the commit trailer; setup offered on discovery, never at
  init. New rules `skill_test` RULE-7/8/9/10/11. Added `purlin:test --local` (not in the original
  plan) so a developer on a repo with a runner can still run locally; documented in
  `purlin_commands.md` rather than deferred to Phase 7.
- **Verify's read-only contract held.** `skill_test` PROOF-8 asserts `skills/verify/SKILL.md`
  contains no `git push`, `gh workflow run` or `git pull`. Build and verify inherit by delegation.
- **`scripts/ci/verify_gate.py`** with new spec `specs/ci/verify_gate.md` (8 rules, 8 proofs) and
  `dev/test_verify_gate.py`. Reads a new read-only `read_report_payload` in the server, never the
  rendered table: PROOF-1 fails on any box-drawing glyph in the source. Exit codes 0/1/2 matching
  `dev/bump_version.sh`. PROOF-5 snapshots the whole tree plus `git status` across all three modes
  to prove the gate writes nothing. `.github/workflows/verify-gate.yml` runs it, following
  `version-check.yml` as the model.
- **The declaration/enforcement split is stated, not implied**, in all eight places the mode is
  reported: the config field description, the `sync_status` line (`sync_status` RULE-49), the
  dashboard tooltip (`purlin_report` RULE-40), the gate output, the gate source header,
  `hard_gates.md`, `README.md`, and `references/remote_verification.md`.
- **`hard_gates.md` still says exactly 1 gate.** CI gating is a non-`## Gate N` section framed as
  project policy layered on the framework's single gate, so `purlin_references` PROOF-6's
  `^## Gate \d+` count is unchanged.
- New config field `remote_verification` (`required` | `optional` | `off`), default `off`, plumbed
  through `templates/config.json`, `.purlin/config.json` (this repo declares `optional`),
  `skill_init` RULE-9/11, `drift_criteria.md`, `docs/installation-guide.md`, and
  `dev/test_init_e2e.sh` (whose `init_project` helper now reads `templates/config.json` as its base
  instead of hand-building the dict, so the required-fields proof stops asserting against its own
  literal).
- New reference `references/remote_verification.md` (`purlin_references` RULE-18/19, Scope and
  Description updated to eleven files) carrying the loop, the workflow template, the trailer, both
  loop-guard halves, the trust split, and the gauges-do-not-travel recommendation.

### Six adjacent defects found and fixed, each with a rule and a proof

1. **`windows-proofs.yml` wrote no `Purlin-Runner:` trailer.** Phase 4 shipped the reader with no
   writer, which is why this repo's own status line read `runner not recorded`
   (`verify_gate` RULE-7/8, checked across every commit-back workflow, with the assertion on
   `-m "Purlin-Runner:` rather than the bare string so a comment cannot satisfy it).
2. **Five stale `purlin:unit-test` references in `skills/build/SKILL.md`.** Phase 0 missed build's
   core iteration loop, pointing the agent at a skill that does not exist. `skill_build` RULE-14
   now also states the delegation the rename was protecting.
3. **Three stale `purlin:verify --audit` references in `docs/regulated-environments.md`**,
   including the Layer 3 deploy-gate name (`skill_verify` RULE-10, which scans `skills/`,
   `references/`, `docs/` and the root, exempting `RELEASE_NOTES.md`).
4. **`drift_criteria.md`'s config ownership table never listed `digest`** (`purlin_references`
   RULE-20, now checked against `templates/config.json`'s keys).
5. **`dev/issue_receipts.py` resolved receipt paths against cwd**, so it only worked when run from
   the repo root. Now takes `root` and `quiet`, which is also how `dev/test_verify_gate.py`
   receipts its temp projects through the real issuer.
6. **The `off` branch of the mode line keyed on declared rather than awaiting proofs**, telling a
   fully proved project its proofs "will stay AWAITING RUNNER". Caught by PROOF-81 while writing
   it; RULE-49 now says the branch keys on awaiting and why.

### Style note carried forward

The user's global rule forbids em-dashes. New prose in specs, references, skills and comments
avoids them. Sample output blocks and the server's own output lines keep them, because they
reproduce or extend the separator every other line the server already prints. The user was told
and has not asked for the program output to change.

## Phase 5 — Remote execution inside `purlin:test` (SUPERSEDED by the DONE section above; kept for the reasoning)

`CLAUDE.md` requires `build` and `verify` to delegate test execution to the test skill, so remote
execution belongs there and both callers inherit it with **no change to verify's read-only
contract** (`skills/verify/SKILL.md:137` "NEVER modify code or test files", `:195` "Verify does
NOT fix tests. Build fixes.").

### `skills/test/SKILL.md`

- **New Step 1.5 — classify tiers**: locally-runnable vs runner-gated; report what cannot run here.
- **Step 2 gains a remote path**: push the current branch, dispatch the workflow, await it, pull
  the proof commits it pushed back. Existing Step 4 already commits proof files.
- **Step 3 reporting** distinguishes locally-proved from remotely-proved, from the commit trailer.
- **Bound the loop at 3 rounds**, matching `skills/audit/SKILL.md:403` and
  `skills/verify/SKILL.md:176`.
- **Setup assistance triggered by discovery, not init.** When runner-gated proofs exist and no
  remote is configured, offer to set it up from a new `references/remote_verification.md` holding
  the workflow template. `init` is untouched.

### The loop, which already exists and is already documented

```
purlin:test  ->  push branch  ->  CI runs runner-gated tiers  ->  proofs come back
   red  ->  report + "-> Run: purlin:build <feature>"
purlin:build  ->  fixes, commits
purlin:test  ->  ...  ->  green
purlin:verify  ->  reads the returned proofs, issues receipts   (never edits a file)
```

### Mode, and the trust split

- New config field `"remote_verification": "required" | "optional" | "off"`, surfaced in
  `purlin:status` and the dashboard header.
- **State the split explicitly.** `docs/regulated-environments.md:71-79` requires policy to live
  outside the repo, "not by config files the agent can edit", and `config.local.json` is
  gitignored. The field *declares* the mode; enforcement is GitHub branch protection.
- Deterministic `scripts/ci/verify_gate.py --check` consuming the **structured** payload
  `_build_report_data` produces. Do not parse the Unicode table the way
  `scripts/hooks/pre-push.sh:70-111` does, which hard-couples it to `_build_summary_table`'s
  glyphs and **fails open** (`:68`).
- Exit codes aligned with `dev/bump_version.sh` (`0` ok / `1` gate failure / `2` bad invocation),
  with a rule and a proof, following `.github/workflows/version-check.yml` — the one proven
  spec-governed CI gate in the repo.
- New feature spec `specs/ci/verify_gate.md`. Legitimate: real code, not a test container. No
  spec's `> Scope:` currently covers `.github/**`.
- `references/hard_gates.md` says Purlin has exactly one hard gate, enforced "in the skill logic,
  not a hook". Amend it and `README.md:173-179` to place CI gating as project policy layered on
  the framework's single gate.
- The gauges cannot travel: `.purlin/cache/` is gitignored, so both are per-machine
  (`docs/collaboration-guide.md:102`, whose claim that gauge results are never shared becomes
  wrong). Recommend: CI recomputes Design deterministically, publishes Integrity only where
  `audit_llm` is set.

## Phases 6 and 7: SUPERSEDED

The remaining phases of this plan were re-planned on 2026-09-11 with a generic platform model
replacing the `windows`-only tier, per-platform reporting, `purlin:init --update`, the pre-push
defects, the trust and GxP fixes, and the docs work. The continuation is
`dev/plans/platform-generic-remote-verification.md`, which is now the authoritative working plan
for branch `two-gauges-remote-verification`. Its "TODO before pushing main" section is the
list that gates the eventual push of `main`.

---

## Also outstanding, from the 0.10.0 plan

**The authoritative list is now "TODO before pushing main" in
`dev/plans/platform-generic-remote-verification.md`**, finalized at the end of Phase 11. It is the
list that gates the eventual `--ff-only` merge and push of `main`, it carries everything below
plus everything execution deferred through Phases 6 to 11, and it is where a new context starts.
Read it there rather than here; these three are kept because they predate that plan.

- **Tier 2a: run a real `purlin:audit`.** Proof Integrity is measured over a handful of executed
  proofs across 2 features and is months stale. The dashboard says so honestly in amber rather
  than claiming a green 100%, but the number is still near-meaningless. This also exercises the
  audit pipeline end to end for the first time. Carried forward as the first open item of the
  TODO list.
- **38 LOOSE Design findings across 12 features**, worth triaging via `purlin:spec`. Carried
  forward in that plan's Backlog table.
- `~/.claude/plans/purlin-0.10.0-followups.md` still holds Tier 2 and Tier 3. Do not delete it
  until those are done.

## Execution notes

- **Trap: never run a subset of test suites.** Much reduced by Phase 3 but not gone: the merge
  key is per test *file*, so running a subset of the tests *inside* one file still replaces that
  file's entries for the features it touches and drops the proofs you skipped. Run whole files,
  finish with `bash dev/run_tests.sh`, and check `git diff --stat specs/` before committing.
- **Trap: never `git checkout -- specs/` to undo proof churn.** It reverts spec `.md` edits with
  it. Use `git checkout -- 'specs/**/*.proofs-*.json'`.
- pytest is not installed system-wide:
  `python3 -m venv /tmp/purlin-venv && /tmp/purlin-venv/bin/pip install -q pytest playwright`,
  then `export PATH=/tmp/purlin-venv/bin:$PATH`. Do not try to download Chromium;
  `dev/browser_launch.py` falls back to installed Chrome.
- **Do not restore `.claude/settings.json`.** `"enabledPlugins": {}` is correct here, and
  `.claude/settings.json.bak` stays uncommitted.
- Three suites cannot run on this machine and their proofs are committed from elsewhere:
  `test_e2e_figma_web.py` (Figma MCP), `test_windows_native.py` (Windows CI),
  `test_e2e_cross_model_audit.sh` (gemini CLI). Do not "fix" their proofs by running something else.
- The receipt issuer is committed at `dev/issue_receipts.py` and now takes a project root:
  `python3 dev/issue_receipts.py` for this repo, `main(root, quiet=True)` from a test.
- **Receipts reference committed state.** Commit specs and proofs FIRST, then run the issuer, then
  commit the receipts as a separate `verify:` commit. The combined vhash is
  `sha256(sorted individual vhashes joined by comma)[:8]` over every `specs/**/*.receipt.json`.
- Re-running the issuer rewrites `commit` and `timestamp` on every receipt, including features
  that did not change. That is what the existing `verify:` commits in the log already do; it is
  churn, not a defect.
- **`grep` in this environment is aliased to `ugrep --ignore-files`, and `--include` globs behave
  differently from GNU grep** — a repo-wide `grep -rn "x" --include="*.md" .` silently missed
  `skills/build/SKILL.md`, which is how five stale references almost went unnoticed a second time.
  Use `command grep` for any repo-wide search you intend to trust.
- Every rule change ships with its proof in the same commit; dev tests locking in old behaviour
  get updated, not deleted around (`CLAUDE.md`).
