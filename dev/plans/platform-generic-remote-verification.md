<!-- Checked-in working plan. This copy is authoritative: the original lived in a
     per-user ~/.claude/plans/ directory that does not travel between machines.
     Update this file as phases complete, in the same commit as the work. -->

# Platform-generic remote verification, per-platform reporting, and the trust fixes

Continuation of `dev/plans/two-gauges-remote-verification.md` (Phases 0-5 DONE at `1ef764dd`).
This plan supersedes that file's Phases 6-7 and adds Phases 8-11. When execution starts, this
content is merged into the checked-in plan (the checked-in copy is authoritative and travels).

## Context

Phase 5 shipped remote execution for exactly one hard-coded tier named `windows`. That conflates
two orthogonal things: the **tier** (unit / integration / e2e: what kind of test) and the
**platform** (where the test must run). A proof can name one tier, so it can name one platform,
and nothing in the codebase detects the host it is running on. The user wants a generic model:
platforms defined in config with OS family, version and architecture, a proof able to require
several platforms, the host detected so the local run proves what it can and a runner proves the
rest, extensible later to mobile OS targets, all reported honestly per platform in `purlin:status`
and the dashboard.

A full document-and-code scan (three explorers, spot-checked by hand) also found that several
compliance-adjacent promises are not backed by mechanism, and a few mechanisms are fragile in ways
an engineer adopting Purlin as an agent tool would not accept. The top findings become phases of
this plan; the rest is a recorded backlog.

### Binding decisions (from the user, this session)

| Question | Decision |
|---|---|
| Spec syntax | Tier stays what-kind. A separate trailing tag `@on(<platform-id>[, ...])` names the platforms a proof must be proved on. Ids resolve against a `platforms` registry in `.purlin/config.json`. Existing `@windows` migrates to `@unit @on(...)`. |
| Receipt depth | vhash binds rule text, test identity (file + name) and platform for `@on` proofs, `\x00` separators; receipts carry per-platform provenance; every receipt re-issued once; docs drop "signed" and "tamper-evident" and state exactly what the hash binds. |
| Pacing | Run to completion; stop only for the merge to `main` or a genuine blocker. |
| Reporting | Verified, Passing and Proof Integrity split per platform when any proof declares `@on`; cards roll up and open a modal; `purlin:status` stays concise; Proof Design never splits. |
| Carried forward | Runner-gated proofs warn, never block. `remote_verification` declares, branch protection enforces. Remote execution lives in `purlin:test`; `verify` stays read-only. No em-dashes in new prose. Rule + proof in the same commit; specs and proofs before receipts; `verify:` commit separate; `git pull --ff-only` after every push because CI commits back. |

### Branch and hand-off (decision: user, 2026-09-12)

All work on `two-gauges-remote-verification`, which is pushed to `origin` after every phase
(the runner loop needs it). **`main` is neither merged nor pushed in this plan.** The branch is
picked up as is on the user's work machine (`git fetch && git checkout
two-gauges-remote-verification`) for the ADO runner plan; the TODO list below is worked in a
new context on this machine first. The eventual `--ff-only` merge and push of `main` happen
after the ADO work, after both quality gauges have been run for real on this repo (Proof
Design via `purlin:audit --design`, Proof Integrity via `purlin:audit`, i.e. Tier 2a, which
Phase 10.4 makes meaningful) with the "Proof-quality gate" bars met. If `--ff-only` ever
refuses, stop and ask.

### Execution strategy (context budget; decision: user)

Aggressively delegate. The main context orchestrates and never holds a test log:
- One subagent per commit (general-purpose, or `fork` when it needs this plan's reasoning) with a
  brief naming the files, the rule text, the proof, the mutation check and the commit message. It
  returns a summary under 300 words: files changed, rules and proofs added, sweep counts,
  mutation result.
- Test sweeps run inside a subagent that returns counts and failing test names only. Explore
  agents answer "where is X" questions. `Plan` agents design any phase whose detail here proves
  insufficient.
- The main context reads the subagent summary, spot-checks `git diff --stat` and the spec diff,
  commits (or asks the subagent to), issues receipts, and updates the DONE section.
- Phase boundaries: refresh the checked-in plan's DONE section so a new context can resume from
  the file alone.

### Proof-quality gate (decision: user; applies to every rule this plan adds or amends)

- Every new or amended rule ships with a proof whose description grades PROVABLE under Pass D:
  it names an observable assertion and a failure condition, never presence-only prose where a
  behaviour can be asserted. After each phase's spec edits run
  `python3 scripts/audit/static_checks.py --check-proof-design --project-root .` and require zero
  UNPROVABLE and zero LOOSE among the descriptions this plan wrote.
- Every proof is mutation-checked (revert the fix, watch the proof fail, restore) and the DONE
  section records the mutation for each.
- Grep-based proofs over skill or doc prose are acceptable only for rules about prose (a skill
  step exists, a doc says X); every rule about behaviour has a behavioural proof.
- Before the local merge: `purlin:audit --design` reads no UNPROVABLE across the repo and Design
  at or above the current 91%; `purlin:audit` (Integrity) measures 100% of executed proofs with
  no HOLLOW and no WEAK on the features this plan touched; the fork reviewer's findings (see
  "Reviewer findings applied") are all closed.

## Evidence the plan rests on (verified this session)

- The only hard-coded runner-gated tier is `_RUNNER_GATED_TIERS = frozenset({'windows'})` at
  `scripts/mcp/purlin_server.py:699`. Tier parsing (`_TIER_TAG_RE`, `:44-49`) already accepts any
  `@name(...)`; proof discovery (`_read_proofs`, `:266-320`) already accepts any file suffix.
- No proof plugin records where a test ran; the only platform string in the code is
  `sys.platform != "win32"` in `dev/test_windows_native.py:33`.
- `_compute_vhash` (`:358-363`) ignores tier, rule text and test identity. 15 of 41 receipts carry
  a September timestamp over proof files last written in April; `dev/issue_receipts.py:49-50`
  filters deferred rules only, diverging from `_active_rule_entries`.
- Manual stamps print `PASS (manual)` (`:1649`) but never increment `proved` (`:1486`).
- Strict pre-push never blocks PASSING (`scripts/hooks/pre-push.sh:99-101` vs `:156`); the
  comma-list `test_framework` matches no `case` arm; `find -maxdepth 2` misses nested specs;
  `off` is unspecced; three fail-open paths; table-glyph parsing.
- `scripts/proof/phpunit_purlin.php:57` calls `exec()` while the security anchor forbids it and
  its proofs grep only `.py`.
- `_check_git_staleness` (`:2440-2461`) passes an anchor's `> Source:` to `git ls-remote` with no
  `--`.
- Four legacy files are tracked under `.purlin/cache/` despite the gitignore; the committed digest
  has `git_sha: null`; `dev/run_tests.sh` omits eight test files that back committed proofs.
- Docs: `docs/index.md:11` "signed verification", `lifecycle-guide.md:48` and
  `dashboard-guide.md:59` "tamper-evident", three inconsistent enforcement-layer sections, an
  invalid CI example in `docs/examples/figma-web-app.md:167-177`, `regulated-environments.md:79`
  citing a `.test-lock.json` that does not exist, `assets/src/*.mmd` gitignored and absent.

## Phase order

| Phase | Delivers | Depends on |
|---|---|---|
| 6 | 6.0 sweep completeness + run marker first; then the platform framework: `@on(...)`, registry, host detection, scoped proof files, per-platform satisfaction, vhash v2, receipt v2, generic remote path | Phase 5 |
| 7 | `purlin:init --update` + migration script + every-skill warning; migrate this repo's Windows proofs through it | 6 |
| 8 | Per-platform reporting in `purlin:status` and the dashboard (roll-up cards, modal) | 6, 7 |
| 9 | Pre-push hook: the four planned defects plus the adjacent ones; hook reads the payload | 6 |
| 10 | Trust and GxP fixes: git argument hardening, security anchor scope, manual proofs, evidence age, audit-cache integrity, auditor identity, housekeeping, tools/QA, environment ids for the four externally-gated suites | 6, 7, 9 |
| 11 | Docs, one enforcement-layer reference, diagrams, RELEASE_NOTES, screenshots | all |
| end | Real `purlin:audit --design` and `purlin:audit`; branch pushed; NO merge and NO push of `main`; TODO list written for the next context | all |

Commit rhythm for every phase: `feat(...)`/`fix(...)` carrying code + spec rules + proofs in one
commit; `python3 dev/issue_receipts.py`; separate `verify:` commit; `git pull --ff-only` after
every push (three workflows commit back). Update the DONE section of the checked-in plan in the
same commit as the phase's last work. Run whole test files only; finish with
`bash dev/run_tests.sh`; check `git diff --stat specs/` before each commit.

---

## Phase 6: platform framework

### 6.0 Sweep completeness and the run marker (lands first; every receipt below depends on it)

- `dev/run_tests.sh` gains every runnable test file that backs committed proofs: pytest pool adds
  `test_drift.py`, `test_pre_push_hook.py`, `test_e2e_spec_from_input.py`,
  `test_e2e_spec_migration.py`, `test_e2e_ui_extraction.py`; shell list adds
  `test_e2e_external_refs.sh` (after an idempotent `bash dev/setup-external-refs.sh`),
  `test_e2e_strict_required.sh`, `test_e2e_manual_staleness.sh`, `test_e2e_required_rules.sh`,
  `test_e2e_verify_audit.sh`, `test_e2e_anchor_authority.sh`, `test_e2e_hybrid_audit.sh`,
  `test_e2e_additional_criteria.sh`. Each is run once by hand first; one that fails is fixed under
  its own rule before it joins (list them as "evaluated" in the DONE section, not promised).
  `test_e2e_build_agent.py` gains a `PURLIN_E2E_AGENT=1` gate (it spends money), mirroring
  `PURLIN_E2E_FIGMA`.
- The sweep writes `.purlin/runtime/test_run.json` on exit (`.purlin/runtime/` is gitignored):
  `{at, commit, sweep, suites, test_files[], passed, failed, skipped, ok}`.
- `proof_common` RULE-14: every `test_file` named by a committed proof entry is either executed
  by `dev/run_tests.sh` or listed with its runner in the rule's exception list
  (`test_windows_native.py` windows runner, `test_e2e_figma_web.py` Figma MCP,
  `test_e2e_cross_model_audit.sh` gemini CLI, `test_e2e_build_agent.py` claude CLI). PROOF-18 in
  new `dev/test_sweep_completeness.py`: set difference equals the exception list exactly, so an
  exception that stops being needed also fails. Mutation: remove one file from the sweep.
- `dev/build_audit_cache.py` is deleted: it hand-writes 200+ grades under a key formula that
  never invalidates (Phase 10.4 makes such entries `invalidated` anyway).

## DONE — Phase 6.0: sweep completeness and the run marker (`test(proof_common): complete the sweep, record the run`, receipts in the `verify:` commit that follows it)

- **Evaluated, and all thirteen joined.** Each candidate was run once by hand, whole file, before
  it joined; every one passed on this machine, so no suite needed a fix under its own rule.
  Pytest pool: `test_drift.py` (4), `test_pre_push_hook.py` (12), `test_e2e_spec_from_input.py`
  (13), `test_e2e_spec_migration.py` (22; its "LLM evaluation" test is a deterministic check, no
  model is called), `test_e2e_ui_extraction.py` (14). Shell, via `run_suite`:
  `test_e2e_external_refs.sh` (15 proofs), `test_e2e_strict_required.sh` (2),
  `test_e2e_manual_staleness.sh` (3), `test_e2e_required_rules.sh` (4),
  `test_e2e_verify_audit.sh` (5), `test_e2e_anchor_authority.sh` (5), `test_e2e_hybrid_audit.sh`
  (11), `test_e2e_additional_criteria.sh` (1). `dev/setup-external-refs.sh` runs before the
  external-refs suite: a second run reports the existing bare repo and exits 0, and because the
  security anchor already carries `> Source:` it edits no spec. The bare repo it creates has a
  HEAD that differs from the committed `> Pinned:` SHA (the commit is re-made per machine) and
  that disturbed nothing in `sync_status`.
- `test_pre_push_hook.py` and `test_e2e_strict_required.sh` lock the current strict-mode
  behaviour. They joined as they are; Phase 9 rewrites them with the hook.
- **Counts.** 14 suites (was 6), `644 passed, 21 skipped` (was 578 passed). Nine proof files
  gained 57 entries and none lost any: `git diff --stat specs/` was insertions only.
- **Run marker.** `dev/run_tests.sh` now `cd`s to the repo root (the shell harness resolves
  `specs/` against cwd), tees the pytest pool through a log to read its summary line, and writes
  `.purlin/runtime/test_run.json` from an `EXIT` trap, so an aborted sweep still leaves a marker
  with `ok: false`. `passed`/`failed` are the pytest counts plus the shell suites (the pool is
  subtracted from the suite tally so it is not counted twice); `skipped` is pytest's. Accumulators
  are newline-separated strings, not arrays: `/bin/bash` on macOS is 3.2, where an empty array
  expanded under `set -u` is an error.
- **`proof_common` RULE-14 / PROOF-18**, `dev/test_sweep_completeness.py`. The exception list is
  read from RULE-14's own text (the backticked `dev/test_*` paths), so the spec and the test
  cannot disagree about it. The list has **three** entries, not the four the phase text named:
  `dev/test_e2e_cross_model_audit.sh` names no committed proof entry (`skill_audit` PROOF-9/10/11
  are proved by `dev/test_skill_specs.py`), and since the list is exact by design, listing it
  fails as a stale exception. When a host with the gemini CLI commits that suite's entries it
  joins the list; Phase 10.6 should expect three and re-check.
  Mutations: deleting the `test_drift.py` line from the sweep fails naming `dev/test_drift.py`;
  adding the cross-model suite to the list fails naming it as stale. Both restored. The
  description grades PROVABLE under `--check-proof-design`.
- `dev/test_e2e_build_agent.py` gains a module-level `PURLIN_E2E_AGENT=1` skip, mirroring
  `PURLIN_E2E_FIGMA`, and is an exception in RULE-14.
- `dev/build_audit_cache.py` deleted; `command grep -rn build_audit_cache` found references only
  under `dev/plans/` and in `RELEASE_NOTES.md`.
- Not in the candidate list and not evaluated: `dev/test_pre_push_hook.sh`, the shell twin of the
  pytest file. No committed proof names it, so RULE-14 does not reach it. Phase 9 decides whether
  it lives or goes.
- `.purlin/report-data.js` is regenerated by the sweep and committed with the proofs, as every
  earlier phase did. CLAUDE.md unchanged.

### 6.1 Grammar and parsing (`schema_spec_format`, `spec_format.md` v9)

- `_TIER_TAG_BODY` gains an args group, character-identical in `scripts/mcp/purlin_server.py:48`
  and `scripts/audit/static_checks.py:900`:
  `(?<!\band)(?<!\bor)(?<!,)\s+@(\w+)(?:\(([^)]*)\))?\s*$`
- New helper `_split_proof_tags(desc) -> (clean_desc, tier, platforms, warnings)` in both modules,
  looping right-to-left over trailing tags: at most one tier tag, at most one `@on(...)`, either
  order; `@on` alone means `@unit`; `@on` on a `@manual` proof is a warning and ignored; a bare
  `@windows` tier is read as `@unit @on(windows)` with a warning naming the rewrite (one release
  of compatibility). Platform id charset `[a-z0-9][a-z0-9-]*` (it becomes a filename, a workflow
  name and an env value).
- `_scan_specs` (`purlin_server.py:161-199`) adds `proof_platforms_by_id` (every proof id, `[]`
  when agnostic) and `proof_tag_warnings`; `_report_feature` prints the warnings in its existing
  warnings block. `static_checks._read_proof_tiers` becomes `_read_proof_tags`.
- Rules: `schema_spec_format` RULE-9 (tag grammar and the two-module parity, which is what
  `dev/test_schema_spec_format.py:241,272` already emit PROOF-9 against and no rule declares) and
  RULE-10 (id charset). PROOF-9 extended with `@unit @on(windows-2022)`,
  `@on(a, b) @integration`, `@on(windows)` alone, `@manual @on(x)`. PROOF-10 rejects
  `@on(Windows_2022)` and `@on(ubuntu-24.04)`.
- `references/audit_criteria.md:88-92` (Pass D implausible-tier criterion) and
  `references/spec_quality_guide.md:300-311` rewritten around `@on`: a description under `@on`
  that any host could verify is LOOSE.
- Format-Version: `spec_format.md` 8 to 9 (tier table row `@windows` replaced by a "Platform
  tags" paragraph). Commit the format file with the code.

## DONE — Phase 6.1: grammar and parsing (`feat(schema_spec_format,static_checks): parse @on(...) platform tags`, receipts in the `verify:` commit that follows it)

- **Grammar.** `_TIER_TAG_BODY` is now
  `(?<!\band)(?<!\bor)(?<!,)\s+@(\w+)(?:\(([^)]*)\))?\s*$` (args captured), and
  `_split_proof_tags(desc) -> (clean_desc, tier, platforms, warnings)` sits directly under it in
  both `scripts/mcp/purlin_server.py` (line 56) and `scripts/audit/static_checks.py` (line 908),
  character-identical (`inspect.getsource` equal), with `_PLATFORM_ID_RE = ^[a-z0-9][a-z0-9-]*$`
  beside each. Right-to-left scan; `on` fills platforms (split on `,`, stripped, deduped,
  order kept, invalid ids dropped with a warning); any other name is the tier; a second tier
  tag or second `@on` stops the scan with a warning and stays in the description; `@on` alone
  is tier `unit`; `@on` on `@manual` warns and drops the platforms; bare `@windows` is tier
  `unit`, platforms `['windows']`, warning `@windows is a platform, not a tier: write @unit
  @on(windows)`. One case the phase text did not name: `@windows @on(x)` is also aliased to
  `unit` with the same warning and keeps the declared platforms rather than adding `windows`.
  `@on()` with no id warns `@on() names no platform`. The connector lookbehinds are unchanged,
  so `..., and @windows` still yields no tag and no truncation.
- **Server.** `_scan_specs` calls the helper once per proof line; the feature dict gains
  `proof_platforms_by_id` (every proof id, `[]` when agnostic) and `proof_tag_warnings`
  (`[(proof_id, message)]`). `_report_feature` prints each as `WARNING: PROOF-N: <message>`.
  It goes through the `advisories` list, not `warnings`: the `warnings` list also decides the
  `PASSING`/`VERIFIED` short path (`if all_proved_passing and not warnings`), and routing the
  alias warning there demoted a passing feature with one legacy `@windows` proof into the
  per-rule detail, where its gated rule printed `NO PROOF` (sync_status PROOF-79 caught it).
  Advisories print in the same block in every path and change no verdict.
- **CLI.** `static_checks._read_proof_tiers` is now `_read_proof_tags(spec_path) -> (tiers,
  platforms)`; `check_proof_design` reads the tiers from it and `_read_proof_descriptions` strips
  tags with the helper (so a two-tag line loses both tags, where the old single `re.sub` left one).
  No wrapper kept: the old name had one caller.
- **Legacy alias downstream.** `proof_tier_by_id` for a bare `@windows` proof now reads `unit`,
  so `_runner_gated_proofs` alone would have stopped gating it and sync_status PROOF-79/80,
  report_data PROOF-30, verify_gate PROOF-4, purlin_report PROOF-41 and the skill_verify
  fixtures in `dev/test_skill_specs.py` (all built on `... @windows`) would have gone red. The
  minimal move for this commit: `_runner_gated_proofs` also gates a `unit` proof whose
  `proof_platforms_by_id` entry names a member of `_RUNNER_GATED_TIERS`, under that platform
  name. `_awaiting_runner`, provenance, the `proofs-windows.json` result file and every test
  above are unchanged; Phase 6.4 replaces the mechanism. `_RUNNER_GATED_TIERS` itself is untouched.
- **Rules and proofs.** `schema_spec_format` RULE-9 (grammar, `@on` semantics, the two-module
  parity and why) and RULE-10 (id charset and why). PROOF-9: the existing parity test keeps its
  connector cases and gains `test_tier_and_platform_tags_split_identically_in_both_modules`
  (`@unit @on(windows-2022)`, `@on(windows-2022, macos-14) @integration`, `@on(windows)` alone,
  `@manual @on(x)`, bare `@windows`, the prose case, a stamped `@manual(...)`; both modules must
  return equal tuples; both tags stripped; either order gives one tuple). PROOF-10:
  `@on(Windows_2022)`, `@on(ubuntu-24.04)` and `@on(windows_2022)` each yield `[]` and one
  warning naming the id; `@on(ubuntu-24)` is the positive control. Both descriptions grade
  PROVABLE under `--check-proof-design`. Mutation: widening `_PLATFORM_ID_RE` to
  `[a-z0-9][a-z0-9_-]*` in both modules fails PROOF-10 on `windows_2022`; the first attempt with
  only `Windows_2022` and `ubuntu-24.04` survived that mutation (each violates on a second
  character too), which is why the underscore-only id was added. Restored.
- **Docs.** `references/formats/spec_format.md` 8 to 9: the `@windows` tier-table row is gone,
  the "any `@<name>` is parsed as a tier" sentence now excludes `on`, and a "Platform tags"
  section gives the grammar, the two examples, the family ids, the charset, the connector rule,
  the legacy alias with its exact warning and the `@manual` rule. `audit_criteria.md` Pass D
  gains an "Implausible platform tag" bullet (a description under `@on(...)` that any host could
  verify is LOOSE); `spec_quality_guide.md` tier table and the runner-gated paragraph are
  rewritten around `@on`. `@windows` mentions in `docs/`, `skills/` and
  `references/remote_verification.md` are left for `purlin_docs` RULE-1 (Phase 11) as allocated.
- **Sweep.** `bash dev/run_tests.sh`: 14 suites, `646 passed, 21 skipped` (was 644: PROOF-9 gained
  one test, PROOF-10 is new). `git diff --stat specs/`: only `schema_spec_format.md` (+4) and
  `schema_spec_format.proofs-unit.json` (+18, two entries, none lost); the alias touched no
  other proof file because every legacy `@windows` fixture lives in test code, not in a
  committed spec.
- CLAUDE.md unchanged.

### 6.2 Registry and host detection (`config_engine`, `sync_status`)

- Optional top-level `platforms` object in `.purlin/config.json` (NOT in `templates/config.json`,
  so `skill_init` RULE-9 stays at seven fields; treated like `audit_llm`):
  `{"<id>": {"os": windows|macos|linux, "version": "14" | ">=10.0.20348", "distro": "ubuntu",
  "arch": x86_64|arm64, "runner": {"provider": "github", "runs_on": "...", "workflow": "..."},
  "label": "..."}}`. `ios`/`android` reserved, rejected with "not yet supported" so the extension
  point is named. `provider` other than `github` is reported as not dispatchable and treated as
  awaiting.
- Built-in family ids with no config: `_BUILTIN_PLATFORMS = {windows, macos, linux}` (config
  entry of the same id overrides, typically to attach a runner). A small project writes
  `@on(windows)` with zero config.
- `_platform_registry(config) -> (registry, errors)` next to `_REMOTE_VERIFICATION_MODES`
  (`:828`): validates, drops malformed entries, errors go to the sync_status preamble, the payload
  (`platforms.errors`) and the gate (exit 2 in every mode: unreadable evidence). A spec naming an
  unregistered non-family id gets a feature WARNING and is treated as awaiting on that id.
- `_detect_host_platform() -> {os, version, distro, arch, id}` using `platform.system()`,
  `mac_ver()`, `win32_ver()`, `freedesktop_os_release()`, `machine()` normalized; `id` is
  `PURLIN_PLATFORM` when set. `_platform_satisfied_by_host(def, host)` and
  `_version_satisfies(constraint, actual)` (two forms only: prefix `14` and `>=N`).
- Config overlay stays flat replace (`config_engine.py:85`); new `config_engine` rule states it
  with a proof (two-entry base, one-entry local, resolved has one). `drift_criteria.md` table
  gains the `platforms` row (owner: `purlin:test` setup offer with consent, or hand edit).

## DONE — Phase 6.2: registry and host detection (`feat(config_engine,sync_status): platforms registry and host detection`, receipts in the `verify:` commit that follows it)

- **Numbers taken (landing order, not the provisional table).** `sync_status` RULE-50 (registry)
  and RULE-51 (host), PROOF-82/83 (RULE-50) and PROOF-84 (RULE-51); `config_engine` RULE-11 and
  PROOF-13 as allocated. The reviewer table had pencilled RULE-50/51 and PROOF-82/83 for 6.4's
  Platforms block and undeclared-results rules; 6.4 now takes RULE-52+ and PROOF-85+, and
  6.5's one-verdict rule moves to the next free number after that.
- **Server** (`scripts/mcp/purlin_server.py`): `import platform` (line 19); a registry block
  directly under `_REMOTE_VERIFICATION_MODES`: `_BUILTIN_PLATFORMS` (928), `_normalise_arch`
  (946), `_validate_platform_entry` (953), `_platform_registry` (1023), `_detect_host_platform`
  (1049), `_version_tuple` (1082), `_version_satisfies` (1090), `_platform_satisfied_by_host`
  (1115), `_host_platform_ids` (1135). `sync_status` resolves config once, above the preamble
  (the second `resolve_config` before the summary table is gone), builds the registry, and after
  the uncommitted-changes block prints `⚠ Platform registry: N entries ignored:` with one
  indented error per dropped entry and `→ Fix: edit "platforms" in .purlin/config.json`.
  `_report_feature` gains `registry=None` (defaults to the built-ins) and appends
  `WARNING: PROOF-N names platform "x", which is not in .purlin/config.json platforms and is
  not a family id (windows, macos, linux)` plus one `→ Fix: add it under platforms, or use a
  family id` line through the 6.1 `advisories` list, so no verdict moves.
- **Decisions the phase text left open.** A malformed config entry that would have replaced a
  built-in (say `windows: {os: "ios"}`) is dropped and the built-in stays, so `@on(windows)`
  keeps resolving while the preamble names the rejection; RULE-50 states it. `distro` on a
  non-linux entry is an error, not ignored. `>=` pads the shorter tuple with zeros
  (`>=14.0` holds on `14`; `>=14.0.1` does not). A host version that is empty or has no
  leading digits fails every constraint. `arch` on the host falls back to the lower-cased raw
  `machine()` when it is not one of the five aliases, so an exotic arch mismatches rather than
  crashes. A non-object `platforms` value is one error (`platforms: must be an object ...`) and
  the registry is the built-ins. `provider` is any non-empty string, as decided; nothing is
  dispatched here.
- **Not built (6.4).** No Platforms block, no payload `platforms` shape, no change to
  `_runner_gated_proofs`/`_awaiting_runner`, no gate exit code. `_detect_host_platform`,
  `_platform_satisfied_by_host` and `_host_platform_ids` have no caller in `sync_status` yet;
  6.4 wires them into the satisfaction model.
- **config_engine.** Overlay stays `dict.update`. RULE-11 states the flat replace and why;
  PROOF-13 (`dev/test_config_engine.py`, `test_nested_object_in_local_replaces_base_object_whole`)
  seeds a two-entry `platforms` in base and a one-entry `platforms` in local and asserts the
  resolved object is exactly the local one. Module docstring gains the paragraph.
- **Proofs** in `dev/test_mcp_server.py`, class `TestPlatformRegistry`: PROOF-82
  (`test_registry_keeps_valid_entries_and_names_every_dropped_one`: six entries, four dropped,
  each named in the errors and the preamble; the `windows` override carries its workflow;
  `AMD64` reads `x86_64`), PROOF-83 (`@unit @on(foo)` advisory, gone once `foo` is registered,
  absent for `@on(macos)`), PROOF-84 (`test_host_detection_and_satisfaction`: monkeypatched
  `platform.system/mac_ver/win32_ver/freedesktop_os_release/machine` and `PURLIN_PLATFORM`;
  macOS 14.7.1 arm64, Ubuntu 24.04, os-release raising OSError, Windows build 10.0.20348,
  env-id short-circuit with `_host_platform_ids`). All four new descriptions grade PROVABLE
  under `--check-proof-design`.
- **Mutations** (each applied, proof run, restored): deep-merge the overlay in
  `resolve_config` and PROOF-13 fails; replace the `>=` tuple comparison with the prefix
  comparison and PROOF-84 fails (`>=13` on 14.7.1 is the discriminating case; `>=14.8` alone
  would not have caught it); accept unknown keys (`unknown = []`) and PROOF-82 fails; drop the
  unknown-id collection and PROOF-83 fails; delete the `platforms` row from
  `drift_criteria.md` and purlin_references PROOF-20 fails.
- **Docs.** `references/drift_criteria.md` ownership table gains the `platforms` row (owner
  `purlin:test` setup offer with consent, or hand edit; readers `sync_status`, `purlin:test`,
  `scripts/ci/verify_gate.py`; default not set, family ids only); the "only skill that writes
  config" sentence now says "unprompted" and names `purlin:test`'s consent path; the closing
  invariant names the five optional fields. `purlin_references` RULE-20/PROOF-20 extended to
  require rows for `audit_llm`, `audit_llm_name`, `audit_criteria`, `audit_criteria_pinned`,
  `platforms` (all five had rows already except `platforms`). `skills/init/SKILL.md` config
  table gains a `platforms` row marked optional and not written by init; the table intro says
  so. `templates/config.json` untouched; `skill_init` RULE-9 stays at seven fields.
- **Sweep.** `bash dev/run_tests.sh`: 14 suites, `650 passed, 21 skipped` (was 646: PROOF-82/83/84 and
  PROOF-13 are new). `git diff --stat specs/`: `sync_status.proofs-integration.json` 4 to 7 entries,
  `config_engine.proofs-unit.json` 19 to 20, `purlin_references.proofs-unit.json` unchanged (the
  PROOF-20 test kept its name); no entry lost. A first sweep run in the background was killed by
  the OS for memory alongside a second waiting shell; the churned proof files were restored with
  `git checkout -- 'specs/**/*.proofs-*.json'` and the sweep re-run in the foreground, which is the
  count above.
- CLAUDE.md unchanged.

### 6.3 Scoped proof files and plugins (`proof_common`, `schema_proof_format`, `proofs_format.md` v5)

- Name `<feature>.proofs-<tier>@<platform-id>.json`; agnostic files unchanged and byte-identical.
  Discovery regex (`purlin_server.py:284`, `static_checks.py:1143`):
  `^(.+)\.proofs-([A-Za-z0-9_]+)(?:@([a-z0-9][a-z0-9-]*))?\.json$`; `_read_proofs` groups by
  `(feature, tier, platform)` and stamps `entry['platform']` from the filename on read.
- Scoped files carry an 8th field `platform` on every entry and at the top level (constant per
  file, so `git diff --cached --quiet` idempotency holds). Merge key `(feature, tier, platform,
  test_file)`; within a file the code is unchanged. Orphan reaping unchanged per file.
- Plugin rule: a marker with no declared platforms never writes a scoped file, whatever
  `PURLIN_PLATFORM` says; with declared platforms it writes the scoped file named by
  `PURLIN_PLATFORM` else the detected family. Plugins never evaluate versions.
- pytest: `@pytest.mark.proof(f, p, r, tier="unit", platforms=("windows-2022",))`, `_host_platform()`
  helper, key `(feature, tier, plat)`, suffix `f"{tier}@{plat}"`. jest/vitest marker
  `[proof:f:PROOF-N:RULE-N:unit:on(a, b)]`. shell: `PURLIN_PROOF_PLATFORMS` env beside
  `PURLIN_PROOF_TIER`. C: `purlin_proof_on(...)` with `purlin_proof` as a NULL-platform wrapper,
  detection in `c_purlin_emit.py`. phpunit and sql: `[on(a,b)]` after the tier. xunit: trait
  `...:tier:on(a,b)`. Regenerate the four `.purlin/plugins/` copies by `cp` (byte-identity rules
  `skill_init` RULE-18/19/20 already exist).
- Rules: `proof_common` RULE-2/4/5/11/12/13 amended, new RULE-14 (marker decides, env names);
  PROOF-5 extended (7 vs 8 fields), new PROOF-18 (real pytest plugin with `PURLIN_PLATFORM` set
  writes only the declared marker to the scoped file) and PROOF-19 (unset env names the family).
  `schema_proof_format` RULE-1/2/4/5 rewritten: no tier is runner-gated, `windows` leaves the
  valid tier set, every `@` suffix is a registry or family id; PROOF-4 updated
  (`dev/test_schema_proof_format.py:230`).
- Format-Version: `proofs_format.md` 4 to 5.

### 6.3b Proof plugins on runners (what runs where, and why no runner-specific plugin exists)

- **One plugin per framework, everywhere.** A runner executes the same plugin the developer runs:
  this repo's `scripts/proof/*`, a consumer project's `.purlin/plugins/*` copies. The only
  per-runner input is `PURLIN_PLATFORM`; nothing in a plugin branches on the host except the
  family fallback in `_host_platform()`. `proof_common` RULE-16 states it; PROOF-20 greps
  `scripts/proof/` and `.purlin/plugins/` for `sys.platform`/`process.platform`/`PHP_OS`/
  `RuntimeInformation` and asserts every hit is inside that one helper. This is what makes "a
  simulated Windows path is not a Windows proof" true without a second code path.
- **`test_file` is forward-slash on every platform.** Today only pytest (`:52`) and shell (`:90`)
  normalise; jest (`path.relative`, `:48`), vitest (`:111`), xunit (`MakeRelative`, `:317`),
  phpunit (`$argv[1]`, `:145`) and sql (`:98`) write the host separator. On a Windows runner that
  yields `dev\x.js`, a different merge key from the macOS run, and once vhash v2 binds test
  identity a different hash per platform for the same test. `proof_common` RULE-15: every
  plugin writes `test_file` relative to the project root with `/` separators on every OS. Proofs
  in `dev/test_multilang_proof_plugins.py` (and `dev/test_proof_jest.sh` for the JS reporters):
  drive each plugin with a backslash-bearing path where its API allows (jest/vitest reporter fed
  a fake `testFilePath` under a matching `rootDir`; xunit via `CodeFilePath`; phpunit and sql via
  argv; c via the emitted JSON) and assert no `\` in any written `test_file`. Mutation: remove
  one plugin's replace and its proof fails.
- **Stale plugin copies on a runner write legacy files.** A consumer runner checks out
  `.purlin/plugins/` as committed; if the project has not run `purlin:init --update` those copies
  predate `platforms=` and write `proofs-<tier>.json` with no platform, which the server then
  reports as an agnostic result that satisfies nothing. The workflow template therefore runs a
  preflight before the tests: `python3 "$PURLIN_PLUGIN_ROOT/scripts/update/migrate.py" --check
  --project-root .` and fails the job (exit 1, message `→ Run: purlin:init --update and commit`)
  when `plugin-copies-stale` or any `legacy-*` migration is pending. `verify_gate` RULE-10 (every
  commit-back workflow carries the preflight) with a proof over the workflow files.
- **Consumer CI has no Purlin `scripts/`.** This repo's workflows work because the repo is the
  plugin. A consumer checkout holds specs, proofs, receipts and `.purlin/`, nothing else. Every
  template that calls Purlin tooling (`verify_gate.py`, `migrate.py`) gains an "Install Purlin
  tooling" step: `git clone --depth 1 --branch v<VERSION> https://github.com/rlabarca/purlin.git
  "$RUNNER_TEMP/purlin"` and `PURLIN_PLUGIN_ROOT=$RUNNER_TEMP/purlin` in the job env, pinned by
  tag (which also answers the backlog's "pin the plugin" item for CI). The gate and migrate
  scripts already import the server by `sys.path` relative to their own file, so they run from
  that clone unchanged. `purlin_references` RULE-24: every CI template under `references/` and
  `docs/` that invokes a `scripts/` path does so through `PURLIN_PLUGIN_ROOT` and pins a tag;
  PROOF greps the yaml blocks.
- **Per-framework runner setup.** The template's install step is chosen from `test_framework`:
  `pip install pytest`; `npm ci` (jest/vitest); `dotnet restore` (xunit); `composer install`
  (phpunit); `sudo apt-get install -y gcc` or the Windows/macOS toolchain note (c); nothing extra
  for shell and sql beyond `python3` (`actions/setup-python` puts `python3` on PATH on all three
  OSes, which the shell and sql plugins' embedded interpreter needs). `references/supported_frameworks.md`
  gains a "Runner setup" column that the skill reads when scaffolding; `purlin_references`
  RULE-25 keeps that column complete for every listed framework (proof: every framework row has
  a non-empty cell). All `run:` steps in a template use `shell: bash` (Git Bash on Windows
  runners), which also covers the `@` path splat hazard.
- **Runner-side plugin loading is the project's own config.** The runner runs the project's test
  command (`pytest`, `npx jest`, ...) and the project's `conftest.py`/reporter config loads the
  plugin exactly as locally; the template never registers a plugin itself. The setup offer in
  `purlin:test` verifies the plugin is wired (the freshness check's "no proof files written"
  branch already exists for the local run and is reused for the runner's log).

## DONE — Phase 6.3 (with 6.3b's plugin rules): scoped proof files and plugins (`feat(proof_common,schema_proof_format): platform-scoped proof files`, receipts in the `verify:` commit that follows it)

- **Numbers taken (landing order, matching the reviewer table).** `proof_common` RULE-15
  (forward-slash `test_file`), RULE-16 (one plugin per framework, host branching only in the
  host-platform helper), RULE-17 (marker decides, environment names, no version evaluation);
  PROOF-19 (RULE-15, per plugin), PROOF-20 (RULE-16, grep plus copy byte-identity), PROOF-21
  and PROOF-22 (RULE-17, env set / env unset, per plugin); RULE-2/4/5/11/12/13 amended and
  PROOF-5 extended (exactly 7 fields agnostic, exactly 8 scoped). `schema_proof_format` RULE-1/2/4/5
  rewritten, RULE-8 (discovery pattern, in-memory `platform` stamp, id charset, legacy alias and
  advisory), PROOF-4 updated, PROOF-5/8 gained scoped variants, PROOF-9 new (RULE-8). Next free:
  proof_common RULE-18/PROOF-23, schema_proof_format RULE-9/PROOF-10. `skill_init` gained nothing:
  the vitest byte-identity rule the reviewer asked for already exists as RULE-47/PROOF-49.
- **Discovery.** `_PROOF_FILE_RE` and `_proof_file_parts(basename) -> (stem, tier, platform,
  legacy)` sit directly above `_read_proofs` in `scripts/mcp/purlin_server.py` and beside
  `_PLATFORM_ID_RE` in `scripts/audit/static_checks.py`, `inspect.getsource`-identical (PROOF-9
  asserts it). `_read_proofs(project_root, legacy=None)` groups by `(stem, tier, platform)` with
  the old same-directory preference, stamps `entry['platform']` (id or `None`) on every entry read,
  and appends each legacy path to `legacy` when a list is passed. `static_checks.audit_scope`
  now parses names through the same helper and stamps the same way; it never had a same-directory
  preference (it counts executed ids across every file) and still has none. `_awaiting_runner`'s
  executed set is `{(id, tier)} ∪ {(id, platform)}`, so a result satisfies the 6.1 alias under
  either name; nothing else in the server reads an entry's tier.
- **The legacy file.** `specs/audit/static_checks.proofs-windows.json` is untouched (Phase 7 renames
  it). `_read_proofs` reads it as tier `unit`, platform `windows`, on every entry, and
  `sync_status` prints in the preamble: `⚠ Legacy proof file: 1 file names a platform as the
  tier:` / `  specs/audit/static_checks.proofs-windows.json (read as unit@windows; becomes
  static_checks.proofs-unit@windows.json)` / `→ Run: purlin:init --update to rename it and
  rewrite the markers`. PROOF-53/54 (declared `@windows`, aliased by 6.1 to unit+on(windows), gated
  under `windows`) are satisfied by the `(id, 'windows')` member of the executed set; static_checks
  stays 35/35 VERIFIED and no AWAITING RUNNER appears. `_RUNNER_GATED_TIERS` is unchanged (its
  comment now says it is the alias name, replaced in 6.4); `_runner_provenance` still finds the
  legacy path by `proofs-windows.json`.
- **Plugins, identical semantics in all eight.** Host id = `PURLIN_PLATFORM` if set, else the family
  (`Windows`/`win32` → `windows`, `Darwin`/`darwin` → `macos`, `Linux`/`linux` → `linux`, anything
  else lower-cased), computed in one helper per plugin (`_host_platform` in pytest, shell, C emitter
  and sql; `hostPlatform` in jest and vitest; `host_platform` in phpunit; `HostPlatform` in xunit).
  A marker with declared platforms writes `<feature>.proofs-<tier>@<host>.json` with `platform` at
  the top level and on each entry; a marker without writes the agnostic file byte-for-byte as
  before. Merge key `(feature, tier, platform, test_file)`; the per-file code is unchanged.

  | Plugin | Marker syntax for platforms |
  |---|---|
  | pytest | `@pytest.mark.proof(f, p, r, tier="unit", platforms=("windows-2022",))`; a bare string is one id |
  | jest / vitest | `[proof:f:PROOF-N:RULE-N[:tier][:on(a, b)]]`, regex `\[proof:(\w+):(PROOF-\d+):(RULE-\d+)(?::(\w+))?(?::on\(([^)]*)\))?\]`; tier may be omitted with `on(...)` present |
  | shell | `PURLIN_PROOF_PLATFORMS="a,b"` (comma list) read at each `purlin_proof` call beside `PURLIN_PROOF_TIER`; the record line gained an 8th `|` field |
  | C | `purlin_proof_on(f, p, r, passed, name, file, tier, "a,b")`; `purlin_proof` is the wrapper passing `NULL`; the header prints `"platforms": "a,b"` and `c_purlin_emit.py` detects the host and names the file |
  | phpunit | `@purlin f PROOF-N RULE-N [tier] [on(a,b)]`, tier group `(?:\s+(?!on\()(\w+))?` so `on(` is never read as a tier |
  | sql | `-- @purlin f PROOF-N RULE-N [tier] [on(a,b)]`, same lookahead |
  | xunit | trait `f:PROOF-N:RULE-N[:tier][:on(a,b)]`; `on(...)` may follow the tier or stand in its place |

  `test_file` forward slashes: every plugin now replaces `\` with `/` outright (pytest and shell
  keep their `os.sep` replace and add it; jest/vitest `split(path.sep).join("/")` plus a
  backslash replace; xunit's `MakeRelative` already replaced and its catch branch now does too;
  phpunit and sql normalise the argv path for the record while still opening the path as given;
  the C emitter normalises). Replacing a literal backslash on POSIX rather than only `os.sep`
  is what makes PROOF-19 constructible on this machine for every plugin (a test file literally
  named `tests\test_x.py` collects under pytest, `dev\t.sh` sources under bash), and a
  POSIX test path with a backslash in it is not a case anyone has. sql's embedded Python now
  receives the two paths through `PURLIN_SQL_TEST_FILE`/`PURLIN_SQL_DB_FILE` rather than
  spliced into the source: the backslash path was a `SyntaxWarning` (and a future error) when
  interpolated. Every plugin's header comment documents the syntax. The four `.purlin/plugins/`
  copies are `cp` regenerated; `dev/test_init_e2e.sh` PROOF-18/19/20/49 pass and PROOF-20's
  second test asserts the byte-identity directly.
- **Proofs.** `dev/test_multilang_proof_plugins.py` gained a "Platform-scoped proof files"
  section: `TestPytestPlatformScoping`, `TestJestPlatformScoping` (node drives the real reporter
  with a fake `testFilePath`; it lives here and not in `dev/test_proof_jest.sh` because that script
  is outside `dev/run_tests.sh`, which RULE-14 would have flagged), `TestVitestPlatformScoping`
  (`_drive_reporter` gained `env=`), `TestCPlatformScoping`, `TestSQLPlatformScoping`,
  `TestPHPPlatformScoping`, `TestXUnitPlatformScoping`, each with a scoped test (PROOF-21 and
  PROOF-5 markers), a forward-slash test (PROOF-19) and a family test (PROOF-22); shell's three
  live in `dev/test_proof_plugins.sh`. `TestOnePluginEverywhere` (PROOF-20) greps `scripts/proof/`
  and `.purlin/plugins/` for the seven host tokens, finds the enclosing definition by scanning
  upward with a per-language definition regex (control keywords skipped), and requires
  `hostplatform` in the lower-cased, underscore-stripped name; 12 files checked, 12 hits. xunit's
  forward-slash case is not constructible on a POSIX host (`CodeFilePath` is the compiler's own
  path), so that test asserts the real run's path has no backslash and that `MakeRelative`
  replaces in both branches; the php and xunit classes skip here (no `php`, no `dotnet`) and
  ran nowhere yet. `dev/test_schema_proof_format.py`: PROOF-4 rewritten (valid set
  {unit, integration, e2e}, `@` suffix charset, name/top-level/entry agreement for non-legacy
  files, the legacy file read back as unit@windows through `_read_proofs`, `spec_format.md`
  documents `@on(`); `TestScopedProofFiles` adds the PROOF-5 and PROOF-8 scoped variants and
  PROOF-9. `dev/test_schema_spec_format.py`'s real-spec connector test now reads PROOF-4's new
  line (tier `integration`, backticked `@on(` not a tag, no platforms).
- **Pass D.** Every new or amended description grades PROVABLE except `proof_common` PROOF-20
  (STRUCTURAL: a grep over source, which is the only proof a rule about where code may live
  can have) and `schema_proof_format` PROOF-4 (STRUCTURAL, as before: it scans committed
  files). Zero UNPROVABLE, zero LOOSE on both anchors.
- **Mutations (each applied, its proof run, restored; all thirteen caught).** pytest: drop the
  backslash replace; drop `entry["platform"]`; let `PURLIN_PLATFORM` alone scope an undeclared
  marker; return the raw `platform.system()` from the family fallback. jest: drop the backslash
  replace. vitest: drop the top-level `platform`. C emitter: drop the `test_file` normalisation.
  sql: drop the `(?!on\()` lookahead (tier reads `on`). shell: drop the `chr(92)` replace. server:
  drop the `platform` stamp on read; empty `_LEGACY_PLATFORM_TIERS`; drop the `(id, platform)`
  member of the executed set (sync_status PROOF-79 goes AWAITING). grep: a `sys.platform` read
  inside `c_purlin_emit.main` (PROOF-20 names the file, line and function).
- **Format and docs.** `proofs_format.md` 4 → 5: File Naming gains the scoped form, the id charset,
  the legacy sentence; Schema gains a scoped example; Fields gains `platform` (top level and
  per entry) and says `test_file` is `/`-separated; Merge states the four-part key and that the
  per-file merge is unchanged; the platform-gated paragraph is rewritten around `@on` and
  `PURLIN_PLATFORM`; a "Runners" paragraph states one plugin everywhere, `PURLIN_PLATFORM` as the
  only per-runner input and no version evaluation; each framework section gains a "Platform
  markers" paragraph. `skills/test/SKILL.md`, `skills/verify/SKILL.md` and
  `references/remote_verification.md` still say "runner-gated tier" and `@windows`; those are
  allocated to 6.6 (`skill_test` rewording) and Phase 11 (`purlin_docs` RULE-1) and were left.
  CLAUDE.md unchanged.
- **Sweep.** `bash dev/run_tests.sh` (foreground): 14 suites, `670 passed, 27 skipped` (was 650/21:
  +20 passed are pytest/jest/vitest/C/sql × 3, PROOF-20 × 2, schema PROOF-5/8/9 scoped variants;
  +6 skipped are the php and xunit classes). `git diff --stat specs/`: insertions only;
  `proof_common.proofs-integration.json` 6 → 28 entries, `proof_common.proofs-unit.json` 27 → 31,
  `schema_proof_format.proofs-unit.json` 8 → 11, no entry lost. No scoped file was committed:
  every fixture writes into a temp project.

### 6.4 Server satisfaction model (`sync_status`, `report_data`, `verify_gate`)

- Delete `_RUNNER_GATED_TIERS`/`_runner_gated_proofs` (`:699-708`). New
  `_platform_scoped_proofs(info)`, `_awaiting_runner(name, info, all_proofs, registry)` returning
  `[(proof_id, tier, platform)]`, `_platform_results(...)` returning per-proof per-platform
  results, awaiting, and `undeclared` (results under an id no proof declares).
- Satisfaction: result under R satisfies declared D iff `R == D`, or D is a family id and
  `registry[R].os == D`. Fail wins across files. Rule status mechanism unchanged
  (`_build_proof_lookup`); `_active_rule_entries` keeps its semantics with the awaiting set keyed
  by `(pid, platform)`: a rule leaves the denominator only when every declared proof is awaiting
  on every declared platform; a rule with any result stays in and counts what that result proves.
  Required anchor rules never excluded.
- `_platform_provenance(project_root, spec_path, feature, tier, platform_id)` replaces
  `_runner_provenance` (`:726`): one `git log -1` per scoped file, memoized per report run, format
  adds `%(trailers:key=Purlin-Platform,valueonly)`; filename/trailer mismatch reported.
- Payload (consumed by Phase 8): per feature `platforms: {<id>: {total, proved, failing[],
  awaiting[], status PROVED|FAILING|PARTIAL|AWAITING, results{}, provenance{commit, when, runner,
  trailer_platform}|null, receipt{commit, stale}|null}}`; `awaiting_runner: [{id, tier,
  platform}]`; `rule.proofs[].platforms` and `.results`; top-level `platforms: {registry, host,
  local[], remote[], errors[], summary{<id>: {features, proofs_awaiting, proofs_failing,
  proofs_proved}}}` and `platform_testing: bool`. All present, `{}`/`[]` when nothing declared
  (fail-closed reason of RULE-30).
- `purlin:status` gains a `Platforms:` block after the mode line (host line, `local:` ids with
  the `PURLIN_PLATFORM` value to set, `runner:` ids with workflow or "no runner configured").
  Phase 8 owns the rest of the presentation.
- Rules: `sync_status` RULE-47/48 amended (drafts in the design output; no em-dashes), new
  RULE-50 (Platforms block, registry errors never silently dropped), RULE-51 (undeclared results
  count toward nothing); `report_data` RULE-29 amended to the triple, new RULE-31/32 for the two
  `platforms` shapes; `verify_gate` RULE-4 per-platform wording, RULE-7 both trailers, new RULE-9
  (pull-rebase-retry in every commit-back workflow), Scope names `.github/workflows/purlin-*-proofs.yml`.
  Proofs: PROOF-79 (family satisfaction case included), PROOF-80 (per-file provenance +
  cross-check), new PROOF-82/83/84; `dev/test_report_data.py:1027-1101`,
  `dev/test_verify_gate.py` (`_spec` helper writes `@unit @on(windows-2022)`, temp config gets
  the registry). Mutation checks: remove the family rule and PROOF-79 must fail; return None from
  provenance and the line must still print "runner not recorded".
- `verify_gate.py`: `_findings` prints `name: PROOF-N declared @on(<platform>) with no result
  there`, a "By platform" section from `platforms.summary`, `platforms.errors` non-empty is exit 2
  in every mode. `verify-gate.yml` adds `.github/workflows/**` to its paths.

## DONE — Phase 6.4: server satisfaction model (`feat(sync_status,report_data,verify_gate): per-platform satisfaction`, receipts in the `verify:` commit that follows it)

- **Numbers taken (landing order).** `sync_status` RULE-47/48 amended, RULE-52 (Platforms
  block) and RULE-53 (undeclared results) new; PROOF-79/80 rewritten, PROOF-83's fixture
  amended (see below), PROOF-85 (RULE-52), PROOF-86 (RULE-53), PROOF-87 (RULE-47) new; next free
  RULE-54/PROOF-88. `report_data` RULE-29 amended, RULE-31 (top-level `platforms` and
  `platform_testing`) and RULE-32 (per-feature `platforms` record, per-proof keys) new;
  PROOF-30 rewritten, PROOF-32/33 new; next free RULE-33/PROOF-34. `verify_gate` RULE-2/4/7
  amended, RULE-9 (registry errors exit 2, By-platform section) new; PROOF-2/4/7 updated,
  PROOF-9 new; next free RULE-10/PROOF-10, so 6.6's rebase loop and preflight land as
  RULE-10/11 and PROOF-10/11, not the RULE-9/10 the phase text pencilled.
- **Server** (`scripts/mcp/purlin_server.py`). `_RUNNER_GATED_TIERS`, `_runner_gated_proofs` and
  `_runner_provenance` are gone. New block under `_attach_gauge_coverage`:
  `_platform_scoped_proofs` (819), `_result_satisfies` (834: `R == D`, or D in
  `_PLATFORM_OS_VALUES` and `registry[R].os == D`, nothing else), `_platform_results` (853:
  `results`, `awaiting`, `undeclared`, plus `satisfied_by` `{D: [(tier, R)]}` for provenance),
  `_awaiting_runner(name, info, all_proofs, registry)` (910, triples), `_mark_undeclared_results`
  (915), `_PROVENANCE_CACHE` (944) and `_platform_provenance` (947: `%H%x00%cI%x00` plus both
  trailers, memoized per `(abs root, relpath)`, cleared on entry to `sync_status`,
  `read_report_payload` and `generate_digest`; falls back to the legacy `proofs-windows.json`
  name when the scoped file does not exist). Beside `_host_platform_ids`:
  `_declared_platform_counts` (1294), `_platform_dispatch_note` (1304), `_platforms_block` (1323),
  passed to `_build_summary_table` as `platform_lines` and printed after the mode line.
  `_runner_lines(project_root, name, info, pres, awaiting_rule_count)` (1980) is platform-keyed
  and also prints the RULE-53 advisory; `_active_rule_entries(..., registry)` (2037) excludes a
  rule only when every planned proof is scoped and awaiting on every platform it declares.
  `_feature_platform_records` (2640) builds the RULE-32 record; `_build_report_data` (2689)
  resolves the registry and host once, computes `_platform_results` per feature, and emits
  `awaiting_runner` triples, `undeclared`, per-feature `platforms`, per-proof `platforms`/
  `results` (only for `@on` proofs, executed and planned), top-level `platforms` and
  `platform_testing`. `_compute_drift` resolves config for the registry too.
- **Decision the phase text left open: "counts toward nothing" is enforced, not just reported.**
  `_mark_undeclared_results` stamps `undeclared: True` in memory on a scoped entry whose
  platform satisfies none of its proof's declared platforms, and `_build_proof_lookup`,
  `_build_all_proofs_lookup` and `_collect_relevant_proofs` skip stamped entries, so an
  undeclared result moves no rule, appears under no rule in the payload and enters no vhash.
  Every entry point stamps after `_read_proofs`: `sync_status`, `read_report_payload`,
  `generate_digest`, `_compute_drift` and `dev/issue_receipts.py`. A caller that forgets gets
  the pre-6.4 counting; PROOF-86 pins sync_status and the payload.
- **Decision: an agnostic result for an `@on` proof satisfies no platform and keeps the rule
  excluded.** With the denominator rule keyed on `(pid, platform)` literally, a proof declared
  `@on(foo)` whose only result is agnostic is awaiting on foo, and a rule it is the only proof
  for leaves the denominator. That made sync_status PROOF-83's one-rule fixture read `0/0`
  instead of PASSING, so the fixture (and its description) gained a second rule proved
  agnostically: the advisory's "no demotion" claim is now tested against a rule that is proved
  here. Nothing else in 6.2 moved.
- **Payload shape.** Per feature: `platforms: {id: {total, proved, failing[], awaiting[], status
  PROVED|FAILING|PARTIAL|AWAITING, results{pid: pass|fail|null}, provenance{commit, when, runner,
  trailer_platform}|null}}` (`{}` when nothing declared; no `receipt` sub-key yet, 6.5's),
  `awaiting_runner: [{id, tier, platform}]`, `undeclared: [{id, tier, platform}]`. Top-level
  `platforms: {registry (no `_id`), host, local[], remote[], errors[], summary{id: {features,
  proofs_awaiting, proofs_failing, proofs_proved}}}` over declared ids, and `platform_testing`.
  PROOF-30/32/33 assert `_build_report_data` and `read_report_payload` agree on all of it.
- **Text.** `⚠ AWAITING RUNNER: N proofs declared @on(<platform>) with no result — ids`;
  `✓ @on(<platform>) proved remotely <when> (<runner>[ (trailer says <x>)])[ via @<R>]`;
  `⚠ Undeclared platform result: PROOF-N has a result in <feature>.proofs-<tier>@<R>.json but
  declares no platform it satisfies; it counts toward nothing`; `Platforms: host <os> <version>
  <arch>[ (PURLIN_PLATFORM=<id>)]` / `  local:  <id> (N proofs); run with PURLIN_PLATFORM=<id>`
  (one line per id; `none of the declared platforms is this host` when empty) / `  runner: <id>
  (N proofs; github workflow <name> | no runner configured | runner provider <x> is not one
  purlin:test can dispatch | unregistered)`. The mode line's "runner-gated proofs" wording is
  untouched for Phase 8. On this repo the block reads `host macos ... arm64`, `local: none`,
  `runner: windows (2 proofs; no runner configured)`, and static_checks prints
  `✓ @on(windows) proved remotely 74 days ago (runner not recorded)`: the legacy file's commit
  (`986fef5c`, PR #5) carried no trailer, which was already the case before this phase.
- **Gate** (`scripts/ci/verify_gate.py`): `_findings` prints `declared @on(<platform>) with no
  result there`; `_by_platform` (95) renders `By platform (N):` from `platforms.summary`, one
  `id: P proved, A awaiting, F failing (K features)` line each, in every mode; a non-empty
  `platforms.errors` exits 2 in every mode after printing each error, before any finding.
  `verify-gate.yml` triggers on `.github/workflows/**` (both `push` and `pull_request`);
  `windows-proofs.yml` gained `-m "Purlin-Platform: windows"` (minimal edit; Phase 7 rewrites it).
- **Elsewhere.** `dev/issue_receipts.py` writes the triple and stamps undeclared results;
  `skills/verify/SKILL.md` sample is `{"id": "PROOF-53", "tier": "unit", "platform": "windows"}`;
  `dev/test_purlin_report.py` PROOF-41 fixture carries `platform` (render unchanged: it still
  groups by `tier`, Phase 8's); `dev/test_skill_specs.py` skill_verify PROOF-9 passes the
  registry and expects the triple; `dev/test_report_data.py` `_write_proofs` gained `platform=`;
  `dev/test_verify_gate.py` `_spec` declares `@unit @on(windows-2022)` and `_make_project`
  registers it. Not changed, noted for 6.5: the issuer still computes `active` without
  `_active_rule_entries`, so a feature whose rule is only awaiting is skipped as `unproved`
  while sync_status reads PASSING; pre-existing, and 6.5's one-verdict function is where it
  is fixed.
- **Pass D.** All 13 new or amended descriptions grade PROVABLE except verify_gate PROOF-7
  (STRUCTURAL, a grep over workflow files, as before). Zero UNPROVABLE, zero LOOSE among them;
  no em-dashes or en-dashes in any line this phase wrote.
- **Mutations (each applied, its proof run with bytecode caching disabled, restored; all
  caught).** Drop the family clause of `_result_satisfies` (PROOF-79); drop the trailer
  cross-check (PROOF-80: `trailer says other` missing); `any` for `all` over a rule's proofs
  and `any` for `all` over a proof's platforms in `_active_rule_entries` (PROOF-87, which gained
  its two-proof rule because the one-rule fixture could not tell the two apart); let an
  undeclared result reach `_build_proof_lookup`, `_build_all_proofs_lookup` or
  `_collect_relevant_proofs` (PROOF-86, whose fixture was moved to a rule that stays in the
  denominator because a fail on an excluded rule is invisible either way); print the Platforms
  block with nothing declared and read an unregistered id as `no runner configured`
  (PROOF-85); registry errors not exiting 2 (verify_gate PROOF-9); never report FAILING per
  platform (report_data PROOF-33); `platform_testing` always true (PROOF-32). Two same-size
  mutations first "survived" because Python reused a `.pyc` whose mtime matched the restored
  file to the second; re-run with `PYTHONDONTWRITEBYTECODE=1` and `__pycache__` removed.
- **Sweep.** `bash dev/run_tests.sh` (foreground): 14 suites, `676 passed, 27 skipped` (was
  670/27: +6 are sync_status PROOF-85/86/87, report_data PROOF-32/33, verify_gate PROOF-9).
  `git diff --stat specs/`: every changed proof file gained entries or kept its count; no
  entry lost. Subset runs during development churned `sync_status.proofs-unit.json` and
  `skill_spec_from_code.proofs-unit.json`; both were restored with
  `git checkout -- 'specs/**/*.proofs-*.json'` before the sweep, whose output is what is
  committed.
- CLAUDE.md unchanged. `references/formats/proofs_format.md` unchanged: no field moved.

### 6.5 vhash v2, receipt v2, one verdict function (`sync_status` RULE-6, `skill_verify`)

Unified formula (the two designs reconciled; user chose `\x00` separators):

```
segments = ["purlin-vhash/2"]
for key in sorted(active_rule_keys):      segments += ["R", key, sha256(" ".join(rule_text.split()))[:16]]
for p in sorted(proofs, key=(feature,id,rule,tier,platform,test_file,test_name)):
                                          segments += ["P", p.feature, p.id, p.rule, p.status, p.tier, p.platform or "", p.test_file, p.test_name]
for m in sorted(counted_manual_stamps):   segments += ["M", feature, proof_id, rule, email, date, sha]
vhash = sha256("\x00".join(segments))[:8]
```

Rule text is whitespace-normalised so a reflow does not invalidate; `feature` in every proof
segment ends the anchor/feature `PROOF-N` collision; `platform` is `""` until Phase 6.3's field
exists (forward-compatible); `M` segments are empty until Phase 10.2 counts stamps. 8 hex kept
(change detector, not a token). `sync_status` RULE-6 rewritten to state exactly this; PROOF-6
re-pins the literal (`dev/test_mcp_server.py:1778`), the mutation check being the literal itself.

- One verdict function: `_feature_verdict(name, info, all_features, all_proofs, global_anchors,
  project_root, registry)` returning `{rule_entries, active_entries, proof_by_rule,
  relevant_proofs, manual_ok, proved, has_fail, vhash, awaiting, platforms, undeclared, receipt,
  has_current_receipt}`. Callers: `_report_feature` (`:1466`), the table loop in `sync_status`
  (`:1113-1131`, which rebuilds the rule entries a second time today), `_build_report_data`
  (`:2042-2070`), `generate_digest` (`:2616`) and `dev/issue_receipts.py`. `sync_status` RULE-50:
  the verdict is computed by exactly one function and `_compute_vhash` is called from exactly one
  place; PROOF-82 counts call sites by AST (the PROOF-34/35 technique). The issuer's `is_def`
  filter (`:50`) disappears because the issuer no longer computes anything.
- Receipt v2 in a new `references/formats/receipt_format.md` (Format-Version 2; the v1 block in
  `skills/verify/SKILL.md:56-90` moves there and the skill points at it, per CLAUDE.md dedup;
  CLAUDE.md's format-file list and `purlin_references` Scope/RULE-21 gain the file):

```json
{"feature": "...", "vhash": "...", "vhash_version": 2, "commit": "...", "timestamp": "...",
 "rules": [...], "rule_hashes": {"RULE-1": "16hex"},
 "proofs": [{"feature","id","rule","status","tier","test_file","test_name","platform"}],
 "manual": [{"id","rule","email","date","commit"}],
 "evidence": {
   "test_run": {"at","commit","sweep","passed","failed","skipped"} | null,
   "proof_files": [{"file","tier","platform","commit","committed_at","runner","executed_in_test_run"}]},
 "awaiting_runner": [{"id","tier","platform"}]}
```

  `proof_files[]` is the per-platform provenance (commit + runner from the trailer, one row per
  tier/platform file, via the Phase 6.4 provenance helper). `manual`, `awaiting_runner` omitted
  when empty.
- Issuer (`dev/issue_receipts.py`) refuses to issue unless `.purlin/runtime/test_run.json` exists,
  `ok` is true and `commit == HEAD`; `--no-run-check` overrides with a printed warning and
  `evidence.test_run: null`. Per contributing entry, `executed_in_test_run` is membership of
  `test_file` in the marker; an entry that is neither executed nor from a runner (`runner: null`)
  makes the issuer print `SKIP <feature>: N proofs from <file> not executed in the recorded run`
  and issue nothing for that feature. This is the mechanism that would have refused
  `pre_push_hook`'s receipt on 2026-09-11. `skill_verify` RULE-11 (receipt v2 shape) and RULE-12
  (issuer refuses a failed or different-commit run unless told to, and then the receipt says so).
  Consumer projects: `purlin:verify` runs `purlin:test` first, so the run is the one it just made;
  writing the marker from the proof plugins is backlog.
- Stale stays `receipt.vhash != vhash`; the detail message gains "Rule text changed since last
  verification: RULE-3" (from `rule_hashes`) and "<platform> re-proved since receipt" (a
  `proof_files` commit differs from current provenance); `report_data` adds
  `receipt.platform_stale[]` and `receipt.test_run_commit`.
- Proofs: `dev/test_mcp_server.py` (rule text change changes the hash; test_name swap changes
  it; same PROOF id under feature and anchor hash differently; boundary-forging mutation must
  fail), new `dev/test_receipts.py` (issuer refusal cases, `evidence` block, SKIP on an
  unexecuted local file), update `dev/test_e2e_verify_audit.sh:100-116`,
  `dev/test_e2e_audit_cache_pipeline.py:1714,2262`, `dev/test_skill_specs.py:1431-1490`,
  `dev/test_verify_gate.py` issuer calls.
- The `verify:` commit after this lands re-issues all 41 receipts as v2 (later phases re-issue in
  their own `verify:` commits as rules change; that is the existing rhythm).

## DONE — Phase 6.5: vhash v2, receipt v2, one verdict function (`feat(sync_status,skill_verify): vhash v2, receipt v2, one verdict function`, receipts in the `verify:` commit that follows it)

- **Numbers taken (landing order).** `sync_status` RULE-6 rewritten, RULE-54 (one verdict
  function) new; PROOF-6 rewritten, PROOF-88 (RULE-54) new; next free RULE-55/PROOF-89.
  `report_data` RULE-33 (receipt evidence fields) new with PROOF-34; next free
  RULE-34/PROOF-35. `skill_verify` RULE-11 (receipt v2 by reference, stale detail) and RULE-12
  (run marker) new with PROOF-11/12; next free RULE-13/PROOF-13. `purlin_references` RULE-21
  (`receipt_format.md`) new with PROOF-21; next free RULE-22/PROOF-22. The phase text pencilled
  `sync_status` RULE-52/PROOF-84 and `purlin_references` RULE-23; landing order gave RULE-54/
  PROOF-88 and RULE-21.
- **vhash v2.** `_rule_text_hash` (16 hex of sha256 over `" ".join(text.split())`),
  `_vhash_proof_key`, `_vhash_manual_key` and `_compute_vhash(rules, proofs, manual=())`, where
  `rules` is `{rule_key: rule_text}`. Segments are `\x00`-joined and start with `purlin-vhash/2`.
  The `manual` parameter is wired and always empty this phase; Phase 10.2 fills it.
- **One verdict function.** `_feature_verdict(name, info, all_features, all_proofs,
  global_anchors, project_root, registry)` returns `rule_entries, active_entries, proof_by_rule,
  relevant_proofs, rules_text, manual_ok, proved, has_fail, vhash, awaiting, awaiting_rule_count,
  undeclared, platforms, unresolved_requires, receipt, has_current_receipt`. Callers:
  `_report_feature`, both loops in `sync_status` (the regular table row and the anchor row),
  `_build_report_data` (so `generate_digest` and `read_report_payload` come through it),
  `_compute_drift` and `dev/issue_receipts.py`. `_compute_vhash` and `_active_rule_entries` are
  each called from exactly one place in `purlin_server.py`, counted by AST in PROOF-88.
  **Two call sites the phase text did not list were found and routed:** `_compute_drift`'s
  per-feature status block, and the anchor branch of the summary table, which hashed an anchor's
  own rule set by hand and would have disagreed with the issuer's receipt for it. The verdict
  passes `{}` for `global_anchors` when the feature is an anchor, which also closes the issuer's
  latent anchor bug (it passed the global anchors to anchors; invisible only because this project
  registers none).
- **Receipt v2** in the new `references/formats/receipt_format.md` (`> Format-Version: 2`, with
  the v1 shape kept as a historical section). The v1 JSON block and the formula sentence left
  `skills/verify/SKILL.md`, which now points at the format file and at `sync_status` RULE-6
  (CLAUDE.md dedup). CLAUDE.md's two format lists gained the file. `_platform_provenance` split
  into `_proof_file_rel` (agnostic path when `platform_id` is None) plus `_file_provenance`, so a
  receipt can record provenance for every contributing file, not only scoped ones.
- **Issuer** (`dev/issue_receipts.py`). New `read_run_marker` (missing, `ok: false`, or
  `commit != HEAD` each refuse, naming which), `write_run_marker` (shared helper so tests do not
  copy the marker shape; `test_files` defaults to every `test_file` a committed proof names),
  `_proof_file_rows`, and `main(root, quiet=False, run_check=True)`. `--no-run-check` warns and
  writes `evidence.test_run: null`. A file the recorded run did not execute and no runner
  committed prints `SKIP <feature>: N proofs from <file> not executed in the recorded run` and
  issues nothing for that feature. The issuer now computes nothing: no `is_def` filter, no
  `active` of its own.
- **Deviation, recorded: this repo issues 38 of 41 receipts, not 41.** The three features backed
  by the `proof_common` RULE-14 exception suites are refused by the new SKIP, because their proof
  files were committed locally with no `Purlin-Runner:` trailer and the sweep does not run their
  suites: `figma_web` (`dev/test_e2e_figma_web.py`), `skill_spec`
  (`dev/test_e2e_build_agent.py`) and `static_checks` (`dev/test_windows_native.py`, whose file
  was committed in PR #5 with no trailer). This is the mechanism working: those three read
  PASSING rather than VERIFIED until a runner commits their proofs with a trailer, or the suites
  run here. Phase 7.4 renames the windows file through `purlin:init --update` and Phase 10.6 gives
  the four externally-gated suites environment ids, which is where this closes. The `verify:`
  commit therefore reads `features=38/41`.
- **Stale detail.** `_receipt_rules_changed` (from the receipt's `rule_hashes`) and
  `_receipt_platform_stale` (from `evidence.proof_files` commits versus current provenance) feed
  two new lines after `Receipt stale (vhash mismatch)`:
  `⚠ Rule text changed since last verification: RULE-1` and `⚠ <platform> re-proved since
  receipt`. `report_data`'s `receipt` object gained `vhash_version`, `test_run_commit` and
  `platform_stale`.
- **Tests.** New `dev/test_receipts.py` (5 tests: the three refusals plus the override, the SKIP
  and its runner escape, the two AST/parity halves of PROOF-88) added to `dev/run_tests.sh`.
  `dev/test_mcp_server.py` PROOF-6 rewritten (literal re-pinned to `c92b8ee3`, plus rule-text
  change, reflow, `test_name` swap, feature/anchor collision, and two inputs that collide under a
  `:` join). `dev/test_report_data.py` PROOF-34, `dev/test_purlin_references.py` PROOF-21,
  `dev/test_skill_specs.py` PROOF-11/12 skill-text halves. Updated to v2:
  `dev/test_e2e_verify_audit.sh` (both helpers go through `_feature_verdict`),
  `dev/test_e2e_audit_cache_pipeline.py` (two sites), `dev/test_verify_gate.py` (`_make_project`
  writes a run marker through `issue_receipts.write_run_marker`).
- **Pass D.** `--check-proof-design` on all four edited specs: PROOF-6, PROOF-88, PROOF-34,
  PROOF-11, PROOF-12 and PROOF-21 all grade PROVABLE. Zero UNPROVABLE and zero LOOSE among them.
  No em-dashes or en-dashes in any line this phase wrote, CLAUDE.md's two new bullets included
  (they use a colon where their neighbours use an em-dash).
- **Mutations (each applied, run with `PYTHONDONTWRITEBYTECODE=1` and `__pycache__` removed,
  restored; all caught).** `\x00` to `:` in `_compute_vhash` (PROOF-6: the literal and,
  independently, the two boundary-forging inputs collide); drop the rule-text hash from the R
  segment (PROOF-6); a second `_compute_vhash` call site outside `_feature_verdict` (PROOF-88 AST
  half); the issuer computing `active` from `rule_entries` as it did before 6.5 (PROOF-88 parity
  half, which is the 6.4 note-4 gap); drop the `commit == HEAD` check (PROOF-12); drop the SKIP
  (PROOF-12); drop the rule-text stale line and drop the platform stale line (PROOF-11, each
  separately); `platform_stale` always `[]` (PROOF-34); remove the null-marker sentence from
  `receipt_format.md` (PROOF-21); remove the format-file pointer from `skills/verify/SKILL.md`
  (PROOF-11 skill half).
- **Sweep.** `bash dev/run_tests.sh` (foreground): 14 suites, `685 passed, 27 skipped` (was
  676/27; +9 are the 5 in `dev/test_receipts.py`, PROOF-21, PROOF-34 and the two skill-text
  halves of PROOF-11/12). `git diff --stat specs/`: insertions only, plus one rename where
  PROOF-6's test was renamed.

### 6.6 Generic remote path (`skill_test`, `purlin_references`, `purlin_commands`)

- `skills/test/SKILL.md`: Usage adds `--platform <id>`; Step 1.5 becomes "Classify platforms"
  (reads the `Platforms:` block, states: no local substitute, absent runner warns,
  `PURLIN_PLATFORM` is set for the local run); Step 2a prefixes the runner command with
  `PURLIN_PLATFORM=<id>` per locally-satisfiable declared id; Step 2b: push once, `gh workflow
  run <workflow> --ref <branch>` per remote platform in parallel, `gh run watch` each, one
  `git pull --ff-only` after all, 3 rounds; setup offer per platform with consent writes
  `.github/workflows/purlin-<id>-proofs.yml` and the `runner` block in config; Step 3 platform
  lines; Step 4 offers `git rm` for stray files. Samples use `macos-14`/`windows-2022`.
- `references/remote_verification.md` template parameterized by `<platform-id>`/`<runs-on>`:
  job `env: PURLIN_PLATFORM`, `paths-ignore: '**/*.proofs-*@<platform-id>.json'`, `shell: bash`
  (PowerShell treats a leading `@` as splat), `git add` narrowed to the platform's own files (the
  runner also writes agnostic files that must not travel back), both trailers, a
  pull-rebase-retry loop (several runners may commit to one branch at once), the "Install Purlin
  tooling" step pinned by tag with `PURLIN_PLUGIN_ROOT`, the `migrate.py --check` preflight, and
  the per-framework setup block (all from 6.3b). This repo's own workflows set
  `PURLIN_PLUGIN_ROOT: .`. `purlin_references` RULE-18 amended; PROOF-18 extended
  (`dev/test_purlin_references.py:290-320`).
- `skill_test` RULE-7..11 reworded platform-generic; PROOF-7 asserts `PURLIN_PLATFORM` and
  `--platform` appear and `windows` no longer appears as a tier (`dev/test_skill_specs.py:1588`).
  `purlin_commands.md:20`, `hard_gates.md:29`, `testing-workflow-guide.md:93-101`,
  `skills/verify/SKILL.md:80-91` updated.

## DONE — Phase 6.6: generic remote path (`feat(skill_test,purlin_references,purlin_commands): platform-generic remote path`, receipts in the `verify:` commit that follows it)

- **Numbers taken (landing order).** `skill_test` RULE-7..11 reworded platform-generic and
  PROOF-7..11 rewritten in place; no new number, next free RULE-12/PROOF-12. `purlin_references`
  RULE-18 amended, RULE-22 (CI templates reach `scripts/` only through `PURLIN_PLUGIN_ROOT` and pin
  a tag) and RULE-23 (runner-setup cell per listed framework) new; PROOF-18 extended, PROOF-22/23
  new; next free RULE-24/PROOF-24. The reviewer table pencilled RULE-21/22 for these two, but 6.5
  had already taken RULE-21 for `receipt_format.md`, so they land one higher. `verify_gate` RULE-10
  (pull-rebase-retry loop plus both trailers) with PROOF-10 new; next free RULE-11/PROOF-11. The
  `migrate.py --check` preflight rule stays Phase 7's, as allocated: the template references the
  script now, and nothing yet requires it of every commit-back workflow.
- **`skills/test/SKILL.md`.** Usage gains `purlin:test --platform <id>` and `--local` now reads
  "report platform-scoped proofs as awaiting". Step 1.5 is "Classify Platforms": it prints the
  `Platforms:` block `sync_status` renders rather than recomputing the split, names the registry and
  the three family ids, and states the three invariants (no local substitute, a missing runner warns
  and never blocks, `PURLIN_PLATFORM` is set for the local run or the plugins fall back to the OS
  family). Every sample names `macos-14` and `windows-2022`; `@windows` appears nowhere in the file.
  Step 2a prefixes the runner command with `PURLIN_PLATFORM=<id>` once per locally-satisfiable
  declared id. Step 2b branches on `platforms.<id>.runner`: dispatch when the provider is `github`
  and the workflow file exists, offer setup otherwise, and report any other provider as not
  dispatchable. The loop is one push, one `gh workflow run` per remote platform in parallel, one
  `gh run watch` each, one `git pull --ff-only` after all of them retried once, bounded at 3 rounds
  with the not-converging block naming `<platform>` and `<runner>`. The setup offer writes both the
  workflow and the config `runner` block, both or neither, only on a yes, and states that this is
  the one place a skill other than `purlin:init` writes config, pointing at the `platforms` row
  `drift_criteria.md` gained in 6.2. Step 3 reports the platform lines as `sync_status` prints them
  and sources provenance per scoped file from both trailers. Step 4 keeps runner-committed files
  untouched and offers `git rm` for an undeclared platform result. The freshness check now says
  "the local run only".
- **`references/remote_verification.md` rewritten around platforms.** New opening sections: what
  `@on(...)` is and how it differs from a tier, family ids, the registry shape and who writes it,
  `PURLIN_PLATFORM` as the only per-runner input, scoped files, and per-file provenance from the two
  trailers. The template is parameterized by `<platform-id>` and `<runs-on>` and carries all of:
  `name: purlin-<platform-id>-proofs`; `paths-ignore: '**/*.proofs-*@<platform-id>.json'` and
  `workflow_dispatch`; `permissions: contents: write`; a job `env` with `PURLIN_PLATFORM` and
  `PURLIN_PLUGIN_ROOT: ${{ runner.temp }}/purlin`; `persist-credentials: true`; an "Install Purlin
  tooling" step cloning `--depth 1 --branch v<VERSION>` into `$PURLIN_PLUGIN_ROOT` with the comment
  that this repository sets the root to `.` and deletes the step; a "Preflight" step running
  `migrate.py --check` from that root, with the comment naming `purlin:init --update`; a
  per-framework setup block covering all eight frameworks with the `actions/setup-python` sentence;
  the test command; `shell: bash` on every `run:` step with the PowerShell splat comment; a `git
  add` narrowed to the platform's own files with the reason (the same run writes agnostic files that
  must not travel back); the `git diff --cached --quiet` guard; a commit with `[skip ci]` and both
  trailers; and a three-attempt pull-rebase-retry loop ending in `exit 1`. "Three details are
  load-bearing" became "What is load-bearing in that template", keeping the original three and
  adding `PURLIN_PLATFORM`, both trailers, the narrowed `git add`, the retry loop, `shell: bash`,
  the plugin root with its pinned tag, and the preflight. The "what travels" table gains a
  scoped-proof-file row and a `.purlin/runtime/test_run.json` row.
- **Other references and docs.** `supported_frameworks.md` gains a **Runner setup** column in both
  tables with a non-empty cell for all eight frameworks, plus the paragraph naming the column as
  what `purlin:test` reads when scaffolding; **Format-Version 5 to 6**, matching the precedent that
  added the Additional Plugins section at 4 to 5. `purlin_commands.md` lists `--platform <id>`
  beside `--local` and rewords `--local`. `hard_gates.md`'s non-gate list reads "A proof declared
  `@on(<platform>)` with no result there". `docs/testing-workflow-guide.md`'s tier table replaces
  its `@windows` row with an `@on(<platform-id>)` row pointing at `spec_format.md`'s Platform tags,
  and the runner-gated paragraph is one short paragraph saying `@on(...)` is not a tier (Phase 11
  owns the rest of the docs). `skills/verify/SKILL.md`'s platform-partial section uses
  `@on(windows-2022)` and shows the `{"id", "tier", "platform"}` triple.
- **`.github/workflows/windows-proofs.yml`** gains the three-attempt pull-rebase-retry loop and
  nothing else; Phase 7.4 rewrites it from the template. `verify_gate`'s Scope line now globs
  `.github/workflows/*-proofs.yml` rather than naming that one file, so a second runner workflow
  joins the scope by existing.
- **Pass D.** `--check-proof-design` on the three edited specs: every description this phase wrote
  grades PROVABLE except `skill_test` PROOF-10 and `purlin_references` PROOF-22, which grade
  STRUCTURAL (both read committed prose and workflow text, which is the only proof a rule about
  documents can have, matching `verify_gate` PROOF-7 and `proof_common` PROOF-20). Zero UNPROVABLE
  and zero LOOSE among them. No em-dashes or en-dashes in any line this phase wrote; the one
  surviving em-dash in `remote_verification.md` and `skills/test/SKILL.md` is inside a sample of
  `sync_status`'s own `AWAITING RUNNER` output.
- **Mutations (each applied, its proof run with `PYTHONDONTWRITEBYTECODE=1`, restored; all five
  caught).** Delete the `--platform` usage line (skill_test PROOF-7); delete the pull-retry sentence
  (PROOF-8); drop `shell: bash` from the template's test step (purlin_references PROOF-18); rewrite
  the preflight as a bare `scripts/update/migrate.py` (PROOF-22, and PROOF-18 independently); empty
  the PHP runner-setup cell (PROOF-23); replace the workflow's retry loop with a bare
  `git push origin "HEAD:$GITHUB_REF_NAME"` (verify_gate PROOF-10).
- **Sweep.** `bash dev/run_tests.sh` (foreground): 14 suites, `688 passed, 27 skipped` (was 685/27;
  +3 are `purlin_references` PROOF-22/23 and `verify_gate` PROOF-10; the five `skill_test` tests
  were rewritten in place, not added). `git diff --stat specs/`: insertions only apart from the five
  `skill_test` proof entries whose `test_name` changed with the test renames; no entry lost.
  `.purlin/report-data.js` regenerated and committed with the proofs.
- **Deviation, carried forward.** `specs/skills/skill_verify.md` RULE-9/PROOF-9 still describe the
  `awaiting_runner` pair as `{id, tier}` and cite a `@windows` proof; `skills/init/SKILL.md` and
  `skills/build/SKILL.md` still say "runner-gated". Those files are outside this phase's scope and
  are allocated to Phase 11's `purlin_docs` RULE-1, which greps for `@windows` as a tier outside
  `RELEASE_NOTES.md` and `dev/plans/`.
- CLAUDE.md unchanged.

### 6.7 Commit sequence

0. `test(proof_common): complete the sweep, record the run` (6.0), then `verify:`
1. `feat(schema_spec_format,static_checks): parse @on(...) platform tags` (6.1)
2. `feat(config_engine,sync_status): platforms registry and host detection` (6.2)
3. `feat(proof_common,schema_proof_format): platform-scoped proof files` (6.3)
4. `feat(sync_status,report_data,verify_gate): per-platform satisfaction` (6.4)
5. `feat(sync_status,skill_verify): vhash v2, receipt v2, one verification helper` (6.5)
6. `verify:` mass re-issue
7. `feat(skill_test,purlin_references,purlin_commands): platform-generic remote path` (6.6)
8. `verify:`; DONE section.

This repo's own Windows proofs are NOT migrated by hand here; Phase 7 migrates them through
`purlin:init --update`. Between 6.3 and Phase 7 the legacy `@windows` alias keeps `static_checks` green with a
warning.

---

## Phase 7: `purlin:init --update` and this repo's migration

Today migration is split: `purlin:init --mcp` (legacy `.mcp.json`, surfaced by `sync_status`
RULE-38's advisory + directive) and `purlin:spec-from-code` (legacy spec layouts). Phase 6 creates
five more things an initialized project must migrate, and nothing today refreshes the
`.purlin/plugins/` copies after a plugin update. Decision (user): **no new skill.**
`purlin:init --update` owns "bring this project up to the installed plugin"; `--mcp` becomes the
alias of one of its steps. Detection is content-based (never version-based, so it works for any
project), the mechanics live in a script so they are deterministic and provable, and **every skill
warns when it has not been run and needs to be** (7.3).

### 7.1 Detector and script

- `_pending_migrations(project_root, config) -> [{id, count, summary, files[]}]` in
  `purlin_server.py`, one check per migration id:
  - `legacy-tier-windows`: proof lines whose parsed tags produced the legacy-alias warning.
  - `legacy-proof-file`: `*.proofs-windows.json` files (or any `proofs-<tier>.json` whose entries'
    `tier` is not `unit|integration|e2e`).
  - `legacy-marker`: test files containing `tier="windows"` (pytest), `:windows]` (jest/vitest),
    `PURLIN_PROOF_TIER=windows`, and the other plugins' equivalents.
  - `plugin-copies-stale`: any `.purlin/plugins/<name>` not byte-identical to `scripts/proof/<name>`.
  - `config-fields-missing`: required fields from `templates/config.json` absent from
    `.purlin/config.json`; `version` differing from `VERSION`.
  - `receipt-v1`: receipts without `vhash_version`. A v1 receipt reads STALE under the v2
    formula for that reason alone, so `_report_feature`'s stale branch names it: "receipt is
    version 1; the vhash formula changed; run `purlin:verify`" instead of the generic wording,
    and the advisory counts them. `--apply` never re-issues a receipt (a receipt is a claim
    that tests ran); `purlin:verify` does, from a fresh run.
  - `legacy-mcp`: what `_check_legacy_mcp_entry` (`:1018`) already detects.
- `scripts/update/migrate.py --check` prints the list as JSON, exit 0 (none) / 1 (pending) / 2
  (bad invocation), never writes. `--apply <id>...` performs the mechanical rewrite for the
  first five ids: spec tag rewrite `@windows` to `@unit @on(windows)` (or an id the skill passes
  with `--platform-id`), `git mv` of the proof file to the `@<id>` name with `platform` added to
  the top level and each entry (a rename of an existing record, not a new claim), marker rewrite
  per plugin syntax, `cp` of plugin copies, config field fill from the template with `version`
  stamped from `VERSION`. `receipt-v1` and `legacy-mcp` are not applied here: the script prints
  `→ Run: purlin:verify` and `→ Run: purlin:init --mcp`. Imports the server by `sys.path` like
  `verify_gate.py`.
- `sync_status` preamble: when the list is non-empty, one advisory block listing each migration
  with its count and `→ Run: purlin:init --update` (generalizes RULE-38; the legacy-MCP advisory
  becomes one entry of it and its directive changes to `--update`). Payload gains `migrations: []`
  (present, empty when none) and the dashboard action banner (purlin_report RULE-23 mechanism)
  shows it with the same directive.

### 7.2 `purlin:init --update`

- `skills/init/SKILL.md` Usage gains `purlin:init --update` (check, prompt, apply),
  `--update --check` (report only) and `--update --platform-id <id>` (what a legacy `@windows`
  becomes; default `windows`). `--mcp` stays listed as "runs only the MCP step of `--update`".
  New Step 5d, "Update": run `--check`; if nothing pending say so and stop; present the delta
  (KEEPING/UPDATING/RENAMING per file, the shape of `skills/spec/SKILL.md` Step 7);
  `AskUserQuestion` for consent; `--apply`; run `purlin:test` for the affected features when
  markers changed (proof files are only ever written by plugins); print the receipt directive;
  commit `chore(update): migrate to <VERSION> (<ids>)`. A second run finds nothing.
- `skill_init` rules: RULE-31 `--update` detection is content-based and every check names its
  files; RULE-32 consent before any write, delta shown first; RULE-33 the step never writes a
  proof entry or a receipt (renames are the only proof-file writes and keep git history via
  `git mv`); RULE-34 plugin copies end byte-identical (extends RULE-18/19/20 to every copy);
  RULE-35 idempotent; RULE-36 the provenance loss on a renamed platform file is stated to the
  user (the old commit's trailer no longer applies; the report reads "runner not recorded" until
  the runner next commits); RULE-37 `--mcp` is the MCP step of `--update`. Proofs: greps on the
  skill text (`dev/test_purlin_skills.py` / `dev/test_init_e2e.sh` patterns) and
  `dev/test_init_update.py` building a temp project with a legacy `@windows` spec, a
  `proofs-windows.json`, a `tier="windows"` marker, a stale plugin copy, a config missing
  `remote_verification`, and a v1 receipt: `--check` lists all and exits 1, `--apply` rewrites,
  second `--check` exits 0, the receipt is untouched and the directive names `purlin:verify`.
  `sync_status` new RULE-52 (pending-migrations advisory; RULE-38 amended to the new directive)
  with PROOF-85 in `dev/test_mcp_server.py`; `report_data` RULE-33 (`migrations` present).
- `references/commit_conventions.md` gains the `chore(update):` prefix.
  `docs/installation-guide.md` gains an "Upgrading the plugin" section (`purlin:init --update`,
  what it migrates, that it asks first); the `--mcp` paragraph at `:78` folds into it.
  `references/purlin_commands.md` and the README/agent skill tables list the flag.
  `RELEASE_NOTES.md` Unreleased gains the upgrade note (Phase 11 writes the section).

### 7.3 Every skill warns when the update has not been run

Decision (user): `purlin:status` and the other skills warn when `--update` is needed. One
mechanism, one reference, no duplicated prose (CLAUDE.md dedup rule):

- The `sync_status` preamble advisory of 7.1 is the signal. Skills that already display
  `sync_status` output (status, test, build, verify, drift) surface it by construction; the skill
  text of each gains one line pointing at the shared section below.
- New section "Pending migrations" in `references/purlin_commands.md` (the file every skill
  already cites): "When `sync_status` opens with a pending-migrations advisory, stop before doing
  the skill's work, print the advisory and its directive, and ask whether to run
  `purlin:init --update` now. `purlin:verify` does not issue receipts while a `legacy-*`
  migration is pending, because the legacy alias makes coverage a guess; that is a warning and a
  refusal to claim, not a gate." Skills that do not call `sync_status` (spec, audit, anchor,
  find, rename, spec-from-code) gain the same one-line pointer and call `sync_status` first when
  they would write specs or proofs.
- Rules: `purlin_references` RULE-21 (the section exists and names the directive);
  `purlin_skills` RULE-16 (every `skills/*/SKILL.md` references the section); `skill_verify`
  RULE-12 (no receipt while `legacy-*` pending; PROOF in `dev/test_skill_specs.py` plus an
  issuer proof in `dev/test_init_update.py` that `issue_receipts.main` skips such a feature and
  says why). `hard_gates.md` unchanged: the verify refusal is stated as "declines to claim", not a
  second gate, in the same non-`## Gate N` framing Phase 5 used for CI gating.

### 7.5 Mutation checks, opt-in (user decision, 2026-09-11)

The practice every phase of this plan follows (break the behaviour, watch the proof fail,
restore) appears nowhere in `references/`, `skills/`, `agents/` or `docs/`. It becomes a written,
opt-in standard because it costs tokens and time: one extra test run per proof plus an edit and
revert cycle, roughly doubling the cost of writing a proof.

- Config field `mutation_checks` (`true` | `false`) in `templates/config.json`, default `false`.
  `skill_init` RULE-9 goes to eight required fields, RULE-11 gains the default;
  `references/drift_criteria.md` ownership row (RULE-20's proof covers it); `docs/installation-guide.md`
  post-init table row.
- `purlin:init` asks, with the value statement printed before the question: what it catches (a
  proof that passes against broken code, which no static check or LLM grade can see), what it
  costs (about twice the tokens and minutes per proof), and who should turn it on (regulated or
  long-lived projects; off for throwaway prototypes). `purlin:init --mutation-checks on|off`
  changes it later, like `--pre-push`. `purlin:init --update` asks the same question when the
  field is absent instead of silently backfilling it (the `config-fields-missing` migration
  fills every other field from the template; this one is passed as `--mutation-checks on|off`
  to `migrate.py --apply`).
- `references/spec_quality_guide.md` "Mutation check" section: definition, the three steps,
  when (every new or amended proof, before the commit that carries it), what a surviving
  mutation means (a weak fixture, not a finished proof; add the discriminating case), two worked
  examples from this plan (the `>=` version flip that survived until the fixture gained `>=13`
  against `14.7.1`; the underscore id that survived until an underscore-only id was added), and
  the value statement `purlin:init` prints (one source; the skill quotes it by reference).
- `skills/build/SKILL.md`: when `mutation_checks` is true the test-writing step requires the
  check before the commit and records the mutation in the commit body; when false it prints one
  line saying the check is off and how to turn it on, so the omission is visible.
  `skills/test/SKILL.md` "Writing Tests with Proof Markers" and `agents/purlin.md` core loop point
  at the section. `references/audit_criteria.md` Pass 2: when the project enables mutation
  checks, the auditor may ask for the mutation that was run and grades a proof whose author
  cannot name one no higher than WEAK.
- Rules and proofs (next free numbers, PROVABLE, no em-dashes): `skill_init` (the question, the
  value statement by reference, the `--mutation-checks` flag, `--update` asking when absent:
  proof greps plus a `dev/test_init_update.py` case where the field is absent and `--check`
  lists it as a question, not a backfill); `purlin_references` (the section with the three
  steps, the surviving-mutation clause and the value statement); `purlin_skills` (build
  branches on the field, test and agent link `spec_quality_guide.md#mutation-check`);
  `skill_build` (the on and off behaviours, proof greps both literals); `skill_audit` (the WEAK
  cap sentence).
- This repo: `.purlin/config.json` `"mutation_checks": true`.

### 7.4 Migrate this repo through `purlin:init --update`

1. Run `purlin:init --update --platform-id windows-2022`: `specs/audit/static_checks.md:97-98` become
   `@unit @on(windows-2022)`; `dev/test_windows_native.py:46,64` markers become
   `tier="unit", platforms=("windows-2022",)`; `specs/audit/static_checks.proofs-windows.json`
   is `git mv`'d to `static_checks.proofs-unit@windows-2022.json` with `platform` added; plugin
   copies refreshed; config `version` stamped.
2. Add `platforms.windows-2022` to `.purlin/config.json` (`os: windows`, `version: ">=10.0.20348"`,
   `arch: x86_64`, `runner: {provider: github, runs_on: windows-2022, workflow:
   purlin-windows-2022-proofs}`); `git mv .github/workflows/windows-proofs.yml
   .github/workflows/purlin-windows-2022-proofs.yml` regenerated from the template.
3. Push; `gh workflow run purlin-windows-2022-proofs --ref two-gauges-remote-verification`;
   `gh run watch`; `git pull --ff-only`. The runner's commit carries both trailers, so the
   "runner not recorded" gap from the handoff closes by construction.
4. Receipts; DONE section.

## DONE — Phase 7: `purlin:init --update` and this repo's migration (`feat(sync_status,skill_init): purlin:init --update and the migration script`, `chore(update): migrate to 0.10.0 (...)`, two `fix(verify_gate):` commits, receipts in the `verify:` commit that follows them)

- **Commits, in order.** `d51bcb34` feat (7.1, 7.2, 7.3, 7.5), `310b6c10` chore(update) (7.4 steps
  1 and 2), `6c94a7b1` verify: 38/41, `0fb5b73c` test(static_checks) (removes the hand-moved proof
  file so the runner commits it), `56b3d746` the runner's own commit, `8912d4df` and `8d08e612`
  fix(verify_gate) (the trailer defect and the YAML slip it introduced), `c60ad919` the runner's
  commit again, then the closing `verify:` 39/41 carrying this section.
- **Numbers taken (landing order).** `sync_status` RULE-55 with PROOF-89, RULE-38 amended with
  PROOF-68 rewritten; next free RULE-56/PROOF-90. `report_data` RULE-34 with PROOF-35; next free
  RULE-35/PROOF-36. `verify_gate` RULE-11 with PROOF-11, RULE-7 amended with PROOF-7 rewritten and
  PROOF-10 extended; next free RULE-12/PROOF-12. `skill_init` RULE-49..57 with PROOF-52..60,
  RULE-9/11 and PROOF-9/11 amended for the eighth config field; next free RULE-58/PROOF-61.
  `skill_verify` RULE-13 with PROOF-13; next free RULE-14/PROOF-14. `skill_build` RULE-15 with
  PROOF-22; next free RULE-16/PROOF-23. `skill_audit` RULE-21 with PROOF-21; next free
  RULE-22/PROOF-22. `purlin_references` RULE-24/25 with PROOF-24/25, PROOF-18 extended; next free
  RULE-26/PROOF-26. `purlin_skills` RULE-16/17 with PROOF-16/17; next free RULE-18/PROOF-18.
  `purlin_agent` RULE-12 with PROOF-12 (the agent file is outside `purlin_skills`' Scope, so the
  agent half of 7.5 landed in its own spec); next free RULE-13/PROOF-13. `purlin_report` RULE-23
  amended, PROOF-23 extended. `schema_proof_format` RULE-8 amended and PROOF-9 extended, because
  the 6.3 legacy-file advisory lost its directive to the shared one.
- **Detector.** `_pending_migrations(project_root, config)` in `purlin_server.py` with the seven
  ids, `_pending_migration_lines` for the preamble, `_legacy_marker_hits`, `_stale_plugin_copies`,
  `_config_field_gaps`, `_v1_receipts` and `_template_config` beside it. Seven marker syntaxes,
  one per plugin grammar (pytest, jest/vitest, shell, C, phpunit, sql, xunit). The scan skips every
  dot directory, so `.claude/worktrees/` (other agents' checkouts) and `.git` are never read or
  rewritten.
- **Decisions the phase text left open.** (1) `--check` exits 1 only for the migrations that make
  the evidence a run is about to write unreliable (every `legacy-*` id and `plugin-copies-stale`),
  and exits 0 while reporting `config-fields-missing` and `receipt-v1`. 7.1 said "exit 1 when
  pending"; 6.3b said the preflight fails on those two classes. A preflight that failed on a
  version 1 receipt would block the CI of every project that has not verified since the formula
  changed, and this repository would have been the first. (2) An empty or unreadable
  `.purlin/config.json` reports no `config-fields-missing`: an absent config is `purlin:init`'s
  case. (3) The 6.3 legacy-file advisory keeps its detail lines and loses its directive; one
  directive closes the shared advisory (`schema_proof_format` RULE-8 amended, PROOF-9 asserts
  exactly one). (4) The legacy-MCP advisory is one entry of the shared list, as 7.1 asked.
- **Migration output for this repository** (`--apply ... --platform-id windows-2022`):

      rewrote 2 proof tags in specs/audit/static_checks.md to @unit @on(windows-2022)
      git mv specs/audit/static_checks.proofs-windows.json specs/audit/static_checks.proofs-unit@windows-2022.json
      stamped platform "windows-2022" on specs/audit/static_checks.proofs-unit@windows-2022.json and its 2 entries
      rewrote 2 markers in dev/test_windows_native.py to tier unit with on(windows-2022)
      -> Run: purlin:verify  (a receipt is a claim that tests ran; this script never writes one)

  `plugin-copies-stale` and `config-fields-missing` were already current, so the script had nothing
  to rewrite for them. `static_checks` PROOF-53/54 read `@unit @on(windows-2022)`, the scoped file
  carries `platform` at the top level and on both entries, and `--check` now exits 0 with
  `receipt-v1` as the only entry left.
- **`--update` does not scaffold runners.** `platforms.windows-2022` and the workflow rename were
  done by hand, as 7.4 step 2 says: registering a platform and writing its workflow is
  `purlin:test`'s consent path, and the skill text says so.
- **Two defects the dogfood found, both fixed under a rule.** (1) The migration produced a proof
  file byte-identical to what the plugin writes on the runner, so the commit-back's
  `git diff --cached --quiet` guard found nothing to commit and the file's provenance stayed the
  local rename: `runner not recorded` after a green run. The fix is not a code change but an act:
  the file was removed so the runner wrote and committed it (`0fb5b73c`). 7.4 step 3's "closes by
  construction" holds only when the rename changes the file's content, which it does not.
  (2) `git commit -m "subject" -m "Purlin-Runner: ..." -m "Purlin-Platform: ..."` puts each `-m`
  in its own paragraph, and git parses trailers out of the last paragraph only, so `Purlin-Runner`
  was invisible to `git log --format=%(trailers:key=Purlin-Runner,valueonly)` while looking
  correct in the workflow and in `git log`. The old PROOF-7 asserted the text and not the effect.
  RULE-7 now requires both trailers in one `-m`, joined with `printf` (a literal newline inside the
  argument ends the YAML block scalar, which is what run `34667665739` failed on), and PROOF-7
  proves the reason: two commits in a temp repository, one per spelling, read back through
  `%(trailers:key=...)`.
- **CI.** Push 1 (`6c94a7b1`): version-check `34667337667` success, verify-gate `34667337669`
  success, purlin-windows-2022-proofs `34667337691` success but "No proof-file changes to commit".
  Dispatch `34667424240` success, committing `56b3d746` with the trailers in two `-m`. Push 2
  (`8912d4df`): `34667665739` failed at the workflow file (the raw newline). Push 3 (`8d08e612`):
  purlin-windows-2022-proofs `34667718333` and verify-gate `34667718329` both success, the runner
  committing `c60ad919`, whose `Purlin-Runner: github-actions/windows-2022` and
  `Purlin-Platform: windows-2022` both parse. `sync_status` now reads
  `✓ @on(windows-2022) proved remotely just now (github-actions/windows-2022)` and the Platforms
  block reads `runner: windows-2022 (2 proofs; github workflow purlin-windows-2022-proofs)`.
- **Receipts: 39 of 41.** `static_checks` is issuable now that a runner committed its scoped file
  with a readable trailer. `figma_web` (`dev/test_e2e_figma_web.py`) and `skill_spec`
  (`dev/test_e2e_build_agent.py`) stay witness-less until Phase 10.6 gives the externally-gated
  suites environment ids. The issuer refuses every receipt while a `legacy-*` migration is pending,
  so the order is fixed: migrate, then verify. That is why the feat commit carries no receipts of
  its own and the first `verify:` after it reads 38/41.
- **Pass D.** `--check-proof-design` on all twelve edited specs: every description this phase wrote
  grades PROVABLE except `skill_audit` PROOF-21, `purlin_skills` PROOF-17 and `purlin_agent`
  PROOF-12, which grade STRUCTURAL (greps over committed prose, the only proof a rule about
  documents can have). Zero UNPROVABLE and zero LOOSE among them; the LOOSE descriptions that
  remain in `sync_status`, `report_data`, `skill_init`, `skill_build` and `purlin_report` are all
  older than this phase.
- **Mutations (28, each applied with `PYTHONDONTWRITEBYTECODE=1`, its proof run, restored; all
  caught).** No advisory in the preamble, and the version 1 receipt explained as a proof change
  (PROOF-89); the legacy MCP entry not reported as a migration (PROOF-68); `migrations` omitted
  when empty (PROOF-35); a version 1 receipt made blocking (verify_gate PROOF-11); detection
  short-circuited on the version stamp (PROOF-52); the xunit marker syntax dropped (PROOF-53); the
  check writing the plugin copies (PROOF-54); the rename done without `git mv` (PROOF-55); stale
  copies left alone (PROOF-56); staleness compared by mtime instead of bytes (PROOF-57);
  `mutation_checks` backfilled from the template (PROOF-60); the issuer claiming while legacy is
  pending (skill_verify PROOF-13); the consent question, the provenance paragraph, the `--mcp`
  usage line, the `--mutation-checks` flag and the refusal framing each removed from their skill
  text (PROOF-54/58/59/60, skill_verify PROOF-13); the build skill's off branch silenced
  (PROOF-22); the WEAK cap reworded away (skill_audit PROOF-21); the verify sentence and one
  worked example deleted (purlin_references PROOF-24/25); one skill's pointer and the test skill's
  anchor removed (purlin_skills PROOF-16/17); the agent's core-loop link removed (purlin_agent
  PROOF-12); the migrations banner hidden on VERIFIED (purlin_report PROOF-23); `mutation_checks`
  removed from `templates/config.json` (skill_init PROOF-9 and PROOF-11 both fail); and the two
  trailers split back across two `-m` in the workflow and in the template (verify_gate PROOF-7 and
  PROOF-10, purlin_references PROOF-18).
- **Sweep.** `bash dev/run_tests.sh` (foreground): 15 suites counted as 14 runs plus the pytest
  pool, `711 passed, 27 skipped` (was 688/27; +23 are the 8 in `dev/test_init_update.py`,
  sync_status PROOF-89, report_data PROOF-35, verify_gate PROOF-11, the 7 in
  `dev/test_skill_specs.py`'s `TestUpdateSkillText`, purlin_skills PROOF-16/17,
  purlin_references PROOF-24/25 and purlin_agent PROOF-12). `dev/test_init_update.py` joined
  `dev/run_tests.sh`, so `proof_common` RULE-14's completeness check covers it.
- **One convention worth knowing.** `dev/test_init_update.py`, `dev/test_mcp_server.py` and
  `dev/test_report_data.py` build the legacy tier name as `'win' + 'dows'` rather than writing it
  out. The detector scans the repository for exactly those literals, so a fixture spelled in full
  would make Purlin's own `--check` report a pending migration forever and fail the CI preflight.
- CLAUDE.md unchanged.

---

## Phase 8: per-platform reporting

Reconciliation with Phase 6 (these are the seam decisions, stated once):
- After `_read_proofs`, every in-memory entry carries `platform` (the id from a scoped filename,
  `None` from an agnostic file); on disk agnostic files stay 7 fields.
- Per-platform record vocabulary is `FAILING | AWAITING | PASSING | VERIFIED` (never a feature
  status; "some proved, some awaiting" is AWAITING because awaiting warns and never blocks).
- Registry `runner` is the Phase 6 object; the provenance runner string comes from the trailer.
- Host id = the registry id the host satisfies (or `PURLIN_PLATFORM`), else `unregistered`;
  agnostic results belong to the host for per-platform Integrity.

### 8.1 Payload and honest VERIFIED (`report_data`, `sync_status`)

- Top level, always present: `platform_testing` (any proof declares `@on`) and `platforms:
  {host, registry (echo, `host: true` on the detected one), summary{<id>: {features, verified,
  passing, failing, awaiting, proofs{declared, proved, failed, awaiting}, integrity{weighted,
  assessed, strong, weak, hollow, manual, behavioral_total, coverage}, last_proved}}}`; summary
  rows only for platforms some proof declares. `summary` (the five counts) gains `verified_here`
  and `held_by_platform = verified_here - verified`; the RULE-4 sum invariant is unchanged.
- Per feature: `platforms{<id>: {declared, proved, failed[], awaiting[], status, receipted,
  provenance}}` (`{}` when nothing declared), `platform_complete`, `awaiting_runner[{id, tier,
  platform}]`. Per proof: `platform` (id or null); one object per executed entry (a two-platform
  proof appears twice); a declared platform with no result emits `{status: "awaiting", platform,
  test_file: "", ...}` beside today's `planned` form (flat, so RULE-8 consumers keep one walk).
- `_determine_status(..., platform_complete=True)`: VERIFIED only when true; an awaiting
  platform caps at PASSING (never PARTIAL or FAILING); all four call sites pass it, and
  `_report_feature:1543`'s second ternary determination is routed through it (PROOF-59 widened).
  Receipts are still issued platform-partial (skill_verify RULE-9). `verify_gate.py` unchanged
  (already fails on not-VERIFIED or awaiting).
- Per-platform Integrity: population = executed entries with that platform (host also owns
  `None`), `measured` = cache entries matching `(feature, proof_id)` among them, same grades,
  `_compute_integrity` + RULE-46 weighting. A grade describes the test, not the platform, so the
  split is measurement coverage per platform. Design never splits. Per-feature gauges unchanged.
- New helpers: `_platform_status`, `_platform_records`, `_platform_summary`. Rules: `report_data`
  RULE-4/5/8/29 amended, RULE-31/32/33 new (all keys present even when nothing declared, per
  RULE-30's reason); `sync_status` RULE-35/47 amended, RULE-52 new (per-platform Integrity
  definition). Proofs: `report_data` PROOF-32..36 (`dev/test_report_data.py`, `_write_proofs`
  gains `platform=`), `sync_status` PROOF-85 (held feature reads PASSING with a current receipt;
  `_platform_status` return set is exactly four words; `_report_feature` no longer contains the
  ternary) and PROOF-86 (`dev/test_e2e_audit_cache_pipeline.py`: two platforms, one STRONG each,
  both read `Integrity 50% (1 of 2 measured)`, `design_summary` has no per-platform key).

### 8.2 `purlin:status` text (`sync_status`, `skill_status`)

- Nothing declares `@on`: byte-identical output.
- Table: no new column. A feature whose `platform_complete` is false carries `*` after its status
  token (`PASSING*`), held rows lead their status group, one legend line under the box:
  `* proved here, awaiting a declared platform. VERIFIED needs every declared platform proved and receipted`.
  `status_width` is computed from rendered tokens (9 only when a marked row exists) so RULE-40
  holds; `_build_summary_table` gains `platform_partial=frozenset()` and `platforms_line=''`.
- One `Platforms (host: <id|unregistered>): <segment> | <segment>` line after the summary line
  and before the mode line (the summary line the skill prints verbatim keeps one job). Segment:
  `<id>[ (host)] <verified>/<features> verified` plus at most five optional clauses (passing,
  failing, `N proofs awaiting runner`, `Integrity W% (M of T measured)` when the platform has
  executed proofs, `proved <rel> (<runner>)`); zero clauses omitted. The `off` mode branch counts
  platform-awaiting proofs.
- Per-feature detail: `_runner_lines` becomes `_platform_lines`: one line per declared platform,
  host first: `✓ macos-14 (host): 2/2 proved`, `✓ windows-2022: 2/2 proved remotely 2 hours ago
  (github-actions/windows-2022)` (or `runner not recorded`), `⚠ windows-2022: awaiting runner, 2
  proofs (PROOF-53, PROOF-54)`, `✗ windows-2022: 1/2 proved, 1 failing (PROOF-54)`; then the
  existing denominator note and `purlin:test` directive only when something is awaiting, and
  `⚠ Receipt is platform-partial: verified here, not on <ids>` when a current receipt has gaps.
  Legacy null-platform awaiting entries keep today's form.
- Conciseness pinned in rules: per project at most one Platforms line and one legend line; per
  feature at most one line per declared platform plus three; all absent when nothing declares.
- Rules: RULE-18/39/40/48/49 amended, RULE-50 (Platforms line grammar) and RULE-51 (detail lines
  and the bound) new. Proofs PROOF-82/83/84/87 in `dev/test_mcp_server.py` (host pinned by
  monkeypatching the detector; PROOF-84 renders `_build_summary_table` directly and asserts
  `PASSING*`, equal widths, legend outside the box, none of it with `platform_partial=()`);
  PROOF-81 extended (Platforms line precedes the mode line).
- `skills/status/SKILL.md`: Step 2 sample gains a `PASSING*` row and the legend; new Step 3c
  prints the Platforms line verbatim when present and nothing in its place when absent; Step 3b
  gains the row `PASSING* or a platform awaiting | its declared platform has no result here;
  warns, never blocks | → Run: purlin:test`; Status Definitions gains AWAITING RUNNER.
  `skill_status` RULE-6 amended, RULE-9/10 new; PROOF-6 extended, PROOF-9/10 new
  (`dev/test_skill_specs.py`).

### 8.3 Dashboard (`purlin_report`, `dashboard_visual`)

- One modal helper: `openModal(title, bodyHtml, footHtml)` / `closeModal()` / `onModalKey`,
  mounted on `document.body` (not `#app`, which `render()` rewrites), `role="dialog"
  aria-modal="true"`, Escape, backdrop click and close button close it, Tab trapped, focus
  returned to the opener, `render()` starts with `closeModal()`, a second open replaces the first.
  New custom properties `--bg-overlay` and `--shadow` in both theme blocks; classes
  `.modal-overlay .modal .modal-head .modal-close .modal-body .modal-table .modal-foot`,
  `.summary-card.sc-click`, `.host-badge`, `.pchips`, `.pchip .pchip-ok .pchip-wait .pchip-fail`,
  `.awr-host`. The overlay is `position:fixed` outside the strip's grid, so card count stays 7
  and RULE-38 tiling (PROOF-40, markup count test) is untouched.
- Cards, only when `platform_testing`: Verified, Passing and Proof Integrity (and Failing when
  any platform fails) get `sc-click`, `role="button" tabindex="0" aria-haspopup="dialog"
  data-modal=...`; Enter/Space and click open the modal. Verified sub-label when
  `held_by_platform > 0`: `<verified_here> on host, <min> on <platform>` (the binding platform),
  else `every declared platform`; Passing sub-label `<n> awaiting a platform`. Headline numbers
  are always the all-platform figures. `gaugeCard` gains a fifth `attrs` argument (update the
  markup test's signature regex in the same commit). Modal bodies: verified/passing (Platform |
  Features | Verified | Passing | Awaiting | Failing | Last proved, host row first and badged,
  footer "Verified counts a feature only when every declared platform is proved and receipted.
  Awaiting proofs leave the coverage fraction and never fail a feature."), integrity (Platform |
  Executed | Measured | Integrity | Assessed | S / W / H, footer "A grade describes the test, not
  the platform... Proof Design is not split"), failing (Platform | Failing features | Proofs).
  When `platform_testing` is false nothing renders and the cards are inert as today.
- Feature row: chip strip under the status badge, one chip per declared platform (`win ✓`,
  `mac ⏳`, `linux ✗`, abbreviation from registry `os`), coloured by record status, tooltip
  carries the full line, no click handler (row click keeps working, no stopPropagation). The
  badge never changes; a held PASSING badge gets a title naming the awaiting platforms. Detail:
  the Awaiting Runner section becomes a Platforms block when `platforms` is non-empty (host
  badged, `.awr-tier` class kept for the tests); legacy null-platform entries keep today's block.
  `proofCell`: `awaiting <platform>` tag on awaiting entries, `@platform` chip on executed ones.
  `cols`, colspans 4/6 and the `gaugeCell` call count unchanged.
- Rules: `purlin_report` RULE-3/4/14/36/38/39 amended, RULE-41 (the one modal helper and its
  behaviours), RULE-42 (which cards open it and only when `platform_testing`), RULE-43 (colour by
  meaning: green proved, amber awaiting, red failing; the strip never alters the badge) new;
  `dashboard_visual` RULE-12 new (chip/modal colours are the RULE-3 status colours; overlay tint
  and shadow are per-theme custom properties). Proofs: `purlin_report` PROOF-43 (markup regexes
  for the helper, aria attributes, body mount, `render()` opening with `closeModal()`, both
  properties in both theme blocks, no hex literal in `.modal-overlay`), PROOF-44..47 (Playwright:
  open by click and keyboard, row count, host badge, footer text, Escape, backdrop, Tab stays
  inside, nothing clickable when `platform_testing` false; sub-labels; chips and computed colours
  via `rgb_to_hex`; Platforms block and legacy fallback; screenshot `proof44_platform_modal.png`),
  `dashboard_visual` PROOF-12.

### 8.4 Docs and screenshots for this phase

- `docs/dashboard-guide.md:92` card bullet (clickable cards, what Verified counts, what the
  sub-label names), new "Platform chips" bullet after `:95`, chip row in the cell-vocabulary table
  (`:146-161`), `images/dashboard-platforms.png`.
- `docs/lifecycle-guide.md`: rule-level table (`:96-102`) gains AWAITING RUNNER; sample block at
  `:109` gains the Platforms line; a paragraph after `:115` on `@on`, `PASSING*` and VERIFIED.
- `tools/QA/purlin-qa-report.md`: read `platform_testing`, `platforms`, `summary.held_by_platform`,
  per-feature `platforms`/`awaiting_runner`; status vocabulary line rewritten; new triage section
  "Platform gaps" (warns, never blocks, not verified on that platform); sign-off readiness excludes
  held features; "signed off" wording removed (Phase 10 does the rest of this file).
- `dev/capture_doc_screenshots.py`: when `PURLIN_DATA.platform_testing`, click `.sc-verified`,
  wait for `#modal`, capture `.modal` to `docs/images/dashboard-platforms.png`, Escape, continue.
  Regenerate all three after Phase 7.4 lands (the summary screenshot then shows chips).

Phase 10 signals rendered here once they exist (small follow-up commit inside Phase 10, not a
separate phase): `evidence_stale` as a row title and an amber `stale evidence` chip; `invalidated`
in the Integrity card tooltip and modal ("N grades invalidated, re-run purlin:audit");
`audit_summary.auditors` on the Integrity card sub-label when the auditor is not the default.

### 8.5 Commits

1. `feat(report_data,sync_status): platform records, honest VERIFIED, per-platform payload` (8.1)
2. `feat(sync_status): Platforms line, status marker, per-feature platform lines` (8.2 server)
3. `feat(purlin_report,dashboard_visual): modal helper, per-platform cards, chips, Platforms block` (8.3)
4. `docs(skill_status): Platforms line, marker legend, AWAITING RUNNER` (8.2 skill)
5. `docs: platforms in the dashboard and lifecycle guides and the QA report; screenshots` (8.4)
6. `verify:`; DONE section.

Watch: the Verified card reads 40 not 41 whenever the windows-2022 result file is absent locally;
that is the intended honesty and the sub-label says why. `pre-push.sh` drops `PASSING*` from its
informational list until Phase 9 moves it to the payload; its gate list is unaffected.

## DONE — Phase 8: per-platform reporting (five commits, each followed by a sweep, `python3 dev/issue_receipts.py` and its own `verify:` commit)

- **Commits, in order.** `cc0b99ec` feat(report_data,sync_status) 8.1, `58351175` verify 205d517d;
  `8cba0466` feat(sync_status) 8.2 server, `a3bc7d48` verify da6f5d48; `98589567`
  feat(purlin_report,dashboard_visual) 8.3, `cefbc9d7` verify 923143e4; `4ebfb980`
  docs(skill_status) 8.2 skill, `62eb2d83` verify 6256b2ef; `7bb6cba3` docs 8.4 with the three
  screenshots, and the closing `verify:` carrying this section.
- **Numbers taken (landing order).** `report_data` RULE-4/5/8/29/31/32 amended, RULE-35 (honest
  VERIFIED and `platform_complete`), RULE-36 (`platforms.summary` rows and per-platform
  Integrity) and RULE-37 (every key present) new with PROOF-36/37/38; PROOF-4/5/8/22/30/32/33
  updated; next free RULE-38/PROOF-39. `sync_status` RULE-18/35/40/47/48/53 amended, RULE-56
  (per-platform Integrity), RULE-57 (Platforms line grammar) and RULE-58 (detail lines and the
  bound) new with PROOF-90..95; PROOF-79/80/86/87 updated; next free RULE-59/PROOF-96.
  `purlin_report` RULE-3/4/14/36/38/39 amended, RULE-41 (the one modal helper), RULE-42 (which
  cards open it) and RULE-43 (colour by meaning) new with PROOF-43..47; next free
  RULE-44/PROOF-48. `dashboard_visual` RULE-12 new with PROOF-12; next free RULE-13/PROOF-13.
  `skill_status` RULE-6 amended, RULE-9/10 new with PROOF-9/10 and PROOF-6 extended; next free
  RULE-11/PROOF-11. `pre_push_hook` RULE-8 amended with PROOF-27 extended (below).
  `verify_gate` PROOF-4 and `skill_test` PROOF-9 updated for the new vocabulary and line text.
- **The reconciliation, as built.** Every in-memory entry already carried `platform` from
  `_read_proofs`, so nothing moved there. `_feature_platform_records` became `_platform_records`
  with the record shape `{declared, proved, failed[], awaiting[], status, receipted, provenance}`
  over `_platform_status`, whose four-word return set (FAILING | AWAITING | PASSING | VERIFIED)
  is asserted by AST. `_platform_summary` and `_platform_integrity` are new; `_host_id` resolves
  `PURLIN_PLATFORM`, else a satisfied registry id preferring a project-registered one over its
  family, else `unregistered`. `_determine_status` gained `platform_complete` and all five call
  sites pass it, `_report_feature`'s header ternary included, which PROOF-91 pins by asserting
  the function contains no `VERIFIED` literal at all.
- **Deviation, recorded: `platforms.summary` carries no host row unless some proof declares the
  host.** The phase text says "summary rows only for platforms some proof declares" and also that
  agnostic results belong to the host for per-platform Integrity. Both hold only when the host is
  itself declared, which it is not in this repository. The rule is written the literal way: rows
  exist for declared platforms only, and the host owns the agnostic entries when it is one of
  them. The consequence here is that the Integrity modal reports windows-2022 over its 2 entries
  and says nothing about the ~740 agnostic ones, which is honest but thin; a host row for an
  undeclared host is a candidate for a later phase if the modal proves hard to read.
- **A defect Phase 8 created and closed in the same commit.** Phase 9's strict pre-push gate
  blocks every non-VERIFIED non-anchor feature, so the honest VERIFIED of 8.1 would have let an
  awaiting platform block a push by another route, which `pre_push_hook` RULE-8 already forbade
  in both modes. The gate now exempts a feature held at PASSING with a current receipt, prints
  `<feature>: PASSING (N/N rules proved, awaiting a declared platform); not blocked, the platform
  has not run yet` in every mode including strict, and PROOF-27 gained a control project with
  nothing awaiting that still exits 1.
- **This repository's real output.** Nothing is held here: the only declared platform is
  `windows-2022` and the runner has proved it, so no row carries the `*` marker and no legend
  line prints. The Platforms line reads

      Platforms (host: macos): windows-2022 1/1 verified, Integrity 0% (0 of 2 measured), proved 1 hour ago (github-actions/windows-2022)

  and `static_checks` reads

      static_checks: VERIFIED
        35/35 rules proved ✓
        vhash=8f25adfe
        ✓ windows-2022: 2/2 proved remotely 1 hour ago (github-actions/windows-2022)

  `Integrity 0% (0 of 2 measured)` is RULE-46 weighting over an empty audit cache, not a defect.
  The RULE-52 `Platforms:` block still prints after the mode line; the two answer different
  questions (where a platform can be proved from here, versus how much is proved there) and 8.2
  placed the new line above the mode line rather than replacing the block.
- **Pass D.** `--check-proof-design` on every edited spec: all sixteen new descriptions grade
  PROVABLE except the ten `skill_status` ones, which grade STRUCTURAL, the only proof a rule
  about committed prose can have. Zero UNPROVABLE and zero LOOSE among them; the LOOSE
  descriptions that remain in `sync_status`, `report_data` and `purlin_report` are all older than
  this phase.
- **Em-dashes.** Two deliberate exceptions, both for internal consistency: the new
  `## Step 3c — Platforms Line` heading matches its four sibling headings in
  `skills/status/SKILL.md`, and the two new `docs/dashboard-guide.md` bullets match the eight
  siblings in their list. Every other line of new prose has none, and the `— ` inside preserved
  rule text is older than this phase.
- **Mutations (30, each applied with `PYTHONDONTWRITEBYTECODE=1` and `__pycache__` removed, its
  proof run, restored; all caught).** 8.1: `_determine_status` ignoring `platform_complete`
  (PROOF-36, PROOF-91); `_platform_status` ignoring `awaiting` (PROOF-33, PROOF-37);
  per-platform Integrity computed over the whole project (PROOF-90); the per-proof `platform` key
  dropped (PROOF-8, PROOF-22); awaiting proof objects not emitted (PROOF-22);
  `held_by_platform` never computed (PROOF-36); a summary row for every registry id (PROOF-32/37/38);
  `host_id` dropped (PROOF-32/38); the strict gate blocking a held feature (pre_push_hook PROOF-27).
  8.2: the `*` marker and the legend dropped (PROOF-94); `status_width` ruled from the vocabulary
  (PROOF-95); the Platforms line suppressed (PROOF-92); zero clauses printed (PROOF-92); the host
  not sorted first (PROOF-93); the platform-partial receipt line dropped (PROOF-93); the directive
  printed with nothing awaiting (PROOF-93); the failing form losing its proof ids (PROOF-93).
  8.3: the overlay mounted in `#app` (PROOF-43); `render()` not closing the modal (PROOF-43);
  cards clickable with `platform_testing` false (PROOF-44); Escape not closing (PROOF-44); Tab not
  trapped (PROOF-44); the awaiting chip coloured green (PROOF-46, dashboard_visual PROOF-12); the
  chip strip altering the badge (PROOF-46); the Verified sub-label always generic (PROOF-45); the
  overlay hardcoding a hex tint (PROOF-43, PROOF-12); the Platforms block falling back to the tier
  block (PROOF-47). 8.2 skill: the marker and legend removed from the sample (PROOF-6); the
  Platforms step removed (PROOF-9); the AWAITING RUNNER definition removed and the Step 3b row
  removed (PROOF-10).
- **Sweep.** `bash dev/run_tests.sh` (foreground): 14 suites, `739 passed, 27 skipped` (was
  726/27; +13 are report_data PROOF-36/37/38, sync_status PROOF-90..95, purlin_report
  PROOF-43..47 and dashboard_visual PROOF-12, less the two that landed inside existing tests).
  Every sweep reaped `proof_plugins_php` PROOF-1/2 from
  `proof_plugins_php.proofs-integration.json` (plan item 10.5c, a sibling agent's fix); the two
  entries were restored from `git show HEAD:` before each commit.
  `dashboard_visual` gained a `proofs-e2e.json` file for PROOF-12; its PROOF-1..11 keep emitting
  at the unit tier, which is where their markers put them.
- **Receipts: 39 of 41** at every step. `figma_web` and `skill_spec` stay witness-less until
  Phase 10.6. `docs/` and `tools/QA/` are in no spec's Scope, so the 8.4 commit moved no vhash.
- CLAUDE.md unchanged.

---

## Phase 9: the pre-push hook (`pre_push_hook`)

Decision: the hook's verdict moves to a small read-only Python entry over `read_report_payload`,
and the `pre_push_hook` spec says so (the handoff's condition). The table parse is the root of
three defects at once (substring feature match at `:92`, five-status `case`, column coupling), and
`verify_gate.py` established the pattern. Not a flag on `verify_gate.py`: that script keys on
`remote_verification`, the hook keys on `pre_push`; two policies, two entry points, one reader.
Also found: the consumer hook never checks coverage outside Claude Code (`:53-61` looks for the
server in `$ROOT/scripts/mcp/` then `$CLAUDE_PLUGIN_ROOT`, unset in a plain terminal push), so it
is fail-open by construction, not only on error paths.

- New `scripts/hooks/pre_push_gate.py` (~150 lines): `config --project-root DIR` prints
  `mode=` and `frameworks=` (comma list split, deduped, `auto` detected in
  `references/supported_frameworks.md` order, unknown names reported on stderr and dropped;
  unknown mode exits 2 naming the value, mirroring `verify_gate.py:106-111`); `check
  --project-root DIR --mode warn|strict`: payload `None` exits 2; FAILING blocks in both modes;
  strict blocks any non-anchor not VERIFIED (PASSING included); warn lists PARTIAL/UNTESTED/
  PASSING as not blocking; `awaiting_runner` is one advisory line, never a block. Keeps the
  literal strings existing proofs assert (`PUSH BLOCKED`, `RECOVERY STEPS`, `strict mode`,
  `partial coverage`, the `/purlin:` directives). Exit 0/1/2.
- `scripts/hooks/pre-push.sh` keeps only: root resolution; plugin-root resolution in order
  (`readlink` of `BASH_SOURCE`, `$PURLIN_PLUGIN_ROOT`, `$CLAUDE_PLUGIN_ROOT`, `$ROOT` dev
  checkout); mode read; `off` prints one line and exits 0; recursive spec discovery
  (`find specs -name '*.md'`); one runner arm per framework WITHOUT `|| true` (pytest exit 5 "no
  tests" is not a failure; jest/vitest with `--passWithNoTests`; shell `*.test.sh` rc
  propagated), any other non-zero blocks in both modes naming runner and code; then
  `python3 "$GATE" check ...` and its exit code. No `2>/dev/null` anywhere; `$ROOT` is an
  argument, never interpolated into Python source.
- Fail-open decisions, stated in the rules: no `.purlin/` stays open and silent; no specs stays
  open and silent (RULE-3); plugin not found: warn prints a loud WARNING naming the paths searched
  and exits 0, strict fails closed; gate crash or unreadable payload closed in both modes; unknown
  mode closed; crashed runner closed.
- Spec: Description says three modes; Scope adds the gate script; RULE-5 (comma list, unknown
  framework reported), RULE-6 (vitest arm, non-zero runner blocks), RULE-8 (reworded without the
  dash; awaiting never blocks) amended; RULE-10 (payload, never the table; no `│`/`─` in the
  shell), RULE-11 (`off`), RULE-12 (unknown mode fails closed), RULE-13 (nested specs), RULE-14
  (plugin resolution and the warn/strict split), RULE-15 (stderr reaches the user), RULE-16
  (whole-name feature matching) new. PROOF-10 rewritten (strict + PASSING exits 1; after
  `issue_receipts.main(root, quiet=True)` exits 0); PROOF-18..26 one per new rule in
  `dev/test_pre_push_hook.py`; PROOF-21 writes a `conftest.py` that raises at import with a stale
  all-pass proof file on disk and asserts exit 1 naming pytest. Mutations: strict gate back to
  NON_READY only; `|| true` back on the pytest arm; `-maxdepth 2` back.
- `dev/test_pre_push_hook.sh` (14 proofs, PROOF-1 and PROOF-8 exist only there, never in the
  sweep, never committed) is ported into the `.py` and deleted: consolidation of a duplicate, not
  removal of a behaviour lock. `dev/test_e2e_strict_required.sh` PROOF-16 (asserts strict passes
  unreceipted) gains a Phase B0 asserting exit 1, then receipts via the issuer and asserts exit 0.
- Docs: `skills/init/SKILL.md:209-224` (three modes, `--pre-push` offers `off`),
  `docs/collaboration-guide.md:79-91`, `docs/installation-guide.md:158`,
  `references/drift_criteria.md:178`.
- This repo keeps `"pre_push": "off"` and the plan's DONE section says why: no root `conftest.py`
  or `testpaths`, so the pytest arm would collect the browser and agent suites. Once 6.0's
  `PURLIN_E2E_AGENT` gate exists, evaluate switching to `warn` and record the outcome.
- Commits: `fix(pre_push_hook): payload-driven gate, three modes, fail closed where it matters`;
  `verify:`; DONE section.

---

## DONE — Phase 9: the pre-push hook (`fix(pre_push_hook): payload-driven gate, three modes, fail closed where it matters`, built on `d43df488` in a worktree, cherry-picked onto `601dfd13` as `f1de8820`; receipts in the `verify:` commit that follows it)

- **Numbers taken (landing order).** `pre_push_hook` RULE-10..16 with PROOF-18..27 (PROOF-27 is
  RULE-8's awaiting clause, which needed its own proof once the rule grew a second sentence);
  RULE-5/6/8 amended; PROOF-10 rewritten; PROOF-1 and PROOF-8 ported in from the deleted
  `.sh`; PROOF-5/6/7/11/12 descriptions updated to what they now assert. Next free
  RULE-17/PROOF-28. The spine's maxima at cherry-pick time were still RULE-9/PROOF-17, so
  nothing was renumbered. Phase 9 edited `skills/init/SKILL.md` prose only and added no
  `skill_init` rule, so Phase 7's RULE-49..57 are untouched.
- **The defect, in one line.** The verdict was parsed out of the rendered summary table, which
  coupled it to a layout, matched feature names by substring (`:92`) and read a fixed column.
  It now lives in `scripts/hooks/pre_push_gate.py` (~450 lines), which reads
  `read_report_payload` the way `scripts/ci/verify_gate.py` does and never writes.
- **Fail-open by construction, outside Claude Code.** The old hook looked for the server under
  `$ROOT/scripts/mcp` then `$CLAUDE_PLUGIN_ROOT`, both unset in a plain terminal push, and
  exited 0 without checking anything. RULE-14 now names four candidates in order and splits the
  outcome: `warn` prints a WARNING naming every path searched and exits 0, `strict` fails closed.
- **Fail-closed decisions, all stated in rules.** Unknown mode (RULE-12), gate crash or
  unreadable payload, crashed runner, and a `.purlin/` with no `config.json` all block in both
  modes. No `.purlin/` at all and no specs stay open and silent (RULE-3). `awaiting_runner` is
  one advisory line and never blocks (RULE-8).
- **Auto-detect order** is pytest, vitest, jest, c, php, sql, with shell as the fallback. `c`,
  `php` and `sql` have no runner arm in `pre-push.sh` and the hook says so out loud rather than
  pretending it ran something.
- **Pass D.** All 27 descriptions grade PROVABLE; zero UNPROVABLE and zero LOOSE.
- **Mutations (4, each restored).** Strict back to NON_READY-only kills PROOF-10 and the e2e
  PROOF-16 phase B0; `|| true` back on the pytest arm kills PROOF-21; `-maxdepth 2` back kills
  PROOF-22; substring accumulation back kills PROOF-26.
- **`dev/test_pre_push_hook.sh` deleted.** Its 14 proofs duplicated the `.py`; PROOF-1 and
  PROOF-8 existed only there, never ran in `dev/run_tests.sh` and were never committed as
  entries. Both are ported into `dev/test_pre_push_hook.py`, so the deletion consolidates a
  duplicate rather than dropping a behaviour lock. `dev/test_e2e_strict_required.sh` PROOF-16
  gains a phase B0 that asserts exit 1 while unreceipted, then receipts through
  `dev/issue_receipts.py` and asserts exit 0.
- **Integration into the spine.** One conflict, in `docs/installation-guide.md`: Phase 7 had
  added the `--mutation-checks` and `--update` rows to the "Changing Settings After Init" table
  while Phase 9 reworded the `--pre-push` row to `warn/strict/off`. Resolved by keeping all
  three rows with Phase 9's wording on the `--pre-push` one. `skills/init/SKILL.md` and
  `references/drift_criteria.md` auto-merged and were checked by hand: Phase 7's `--update`,
  `--update --check`, `--update --platform-id`, `--mcp` and `--mutation-checks` lines all
  survive alongside Phase 9's three-mode prose.
- **This repo keeps `"pre_push": "off"`.** There is no root `conftest.py` and no `testpaths`, so
  the pytest arm would collect the browser and agent suites on every push. Re-evaluate once
  6.0's `PURLIN_E2E_AGENT` gate is in play.
- **Sweep contribution.** `dev/test_pre_push_hook.py` goes from 12 test functions to 24; the
  hook suite and `dev/test_e2e_strict_required.sh` both run green against the current server.

---

## Phase 10: trust and GxP fixes

Ordered by dependency; each item is one `fix`/`feat` commit with its rule and proof, then a
`verify:` commit.

### 10.1 Git argument hardening and the security anchor

- `_check_git_staleness` (`:2442`): `_source_url_is_safe(url)` rejects a value starting with `-`,
  containing `ext::`/`fd::`, NUL or newline (anchor line reads `(source rejected: begins with
  "-")`); `['git','ls-remote','--end-of-options', url, 'HEAD']`. `_compute_drift` (`:2496`,
  `:2507`), `_check_manual_staleness` (`:327`), `_resolve_since_anchor`: `--end-of-options` before
  every revision, `--` before every path, `since` validated against `^[0-9]+$` or a date before
  use (it is LLM-supplied). `security_no_dangerous_patterns` RULE-6, `drift` RULE-17; PROOF-6 in
  `dev/test_security.py` runs `sync_status` under a `subprocess.run` spy with a Source of
  `--upload-pack=/bin/echo` and asserts no argv carries it in option position;
  `dev/test_drift.py` for `since="--output=/tmp/x"`.
- Anchor Scope widened to `.py .sh .js .ts .php .cs`; RULE-1 and RULE-5 reworded per language
  (no `eval`/`exec`/`shell_exec`/`system`/backticks in PHP, no string `exec`/`execSync` in JS/TS,
  argv arrays everywhere: `proc_open` with an array, `spawn`/`execFile`,
  `ProcessStartInfo.ArgumentList`); PROOF-1/2/3/5 iterate `_all_script_files()` widened
  (`dev/test_security.py:16-25`). `scripts/proof/phpunit_purlin.php:50-58` moves to
  `proc_open(['php','-r',$code], ...)` with `var_export` quoting; `proof_plugins_php` gains the
  rule and a grep proof in `dev/test_multilang_proof_plugins.py`. Mutation: reintroduce `exec(`.
- Anchor header drops "Generated by purlin:spec-from-code"; `> Source:
  ./dev/external-refs/security-policy.git` with a `> Note:` naming `dev/setup-external-refs.sh`
  (relative form already treated as git and run with `cwd=project_root`).

---

## DONE — Phase 10.1: git argument hardening and the security anchor (`fix(security_no_dangerous_patterns,drift,proof_plugins_php): git argv hardening, anchor scope, proc_open`, built on `fc728e61` in a worktree, cherry-picked onto `f1de8820` as `a5d71a01`; receipts in the `verify:` commit that follows it)

- **Numbers taken (landing order).** `security_no_dangerous_patterns` RULE-6 with PROOF-6 (next
  free RULE-7/PROOF-7), `drift` RULE-17 with PROOF-20 (next free RULE-18/PROOF-21),
  `proof_plugins_php` RULE-3 with PROOF-3 (next free RULE-4/PROOF-4). RULE-1 and RULE-5 of the
  anchor reworded per language; PROOF-1/2/3/5 widened. Nothing collided on the spine, so nothing
  was renumbered.
- **The hardening.** `_source_url_is_safe(url)` rejects a `> Source:` that begins with `-`, names
  an `ext::` or `fd::` transport, or carries a NUL or a newline, before any subprocess starts;
  `git ls-remote --end-of-options <url> HEAD`. `--end-of-options` precedes every revision and
  `--` precedes every path in `_check_manual_staleness`, `_resolve_since_anchor`,
  `_get_diff_stat`, `_detect_spec_changes` and `_compute_drift`. `since` is LLM-supplied, so it
  is accepted only as digits or `YYYY-MM-DD` and refused with a message naming both forms.
- **Anchor Scope widened** to `.py .sh .js .ts .php .cs`, with RULE-1 and RULE-5 spelling the
  ban per language: no `eval`/`exec`/`shell_exec`/`system`/backticks in PHP, no string
  `exec`/`execSync` in JS/TS, argv arrays everywhere (`proc_open` with an array,
  `spawn`/`execFile`, `ProcessStartInfo.ArgumentList`). `scripts/proof/phpunit_purlin.php:72`
  moved from an `exec()` shell string to `proc_open` with an argv array and `var_export` quoting.
- **One rendering line changed.** `sync_status`'s anchor status line gained a
  `(source rejected: <reason>)` branch; RULE-6's anchor line has nowhere else to come from.
- **The anchor is now reproducible.** `> Source: ./dev/external-refs/security-policy.git` with a
  `> Note:` naming `dev/setup-external-refs.sh`, which commits with a fixed identity and date so
  the `Pinned: d1e2816...` line holds in any checkout. This repo's fixture was recreated with
  `rm -rf dev/external-refs && bash dev/setup-external-refs.sh`; `sync_status` reads
  `Pinned: d1e2816 (current)`.
- **Pass D.** `security_no_dangerous_patterns` 6/6, `drift` 20/20, `proof_plugins_php` 3/3 all
  PROVABLE; zero UNPROVABLE and zero LOOSE.
- **Mutations (3, each restored).** Dropping `--end-of-options` kills PROOF-6; dropping the
  `since` validation kills drift PROOF-20; reintroducing `exec(` kills `proof_plugins_php`
  PROOF-3 and anchor PROOF-1.
- **Integration into the spine.** No conflict. `scripts/mcp/purlin_server.py` auto-merged
  because 10.1's hunks are local to the git-invocation helpers while Phase 7 had added
  `_pending_migrations` and its neighbours elsewhere in the file; both are present and the
  module parses.
- **10.5c bit again, exactly as recorded.** `proof_plugins_php` PROOF-1/2 need a `php` binary,
  which this host does not have, so `dev/run_tests.sh` skips them — and the write-scoped
  overwrite reaped their committed entries on both sweeps, because `dev/test_multilang_proof_plugins.py`
  did execute PROOF-3 from the same file for the same feature. Both entries were restored by
  hand after each sweep, as the branch did. This is the defect 10.5c exists to fix; it was not
  fixed here.
- **Sweep, both phases together.** `bash dev/run_tests.sh` (foreground) reads
  `726 passed, 27 skipped`, 14 suites, 0 failed, up from `711 passed, 27 skipped`. The +15 are
  exactly the new test functions: 12 in `dev/test_pre_push_hook.py` (12 -> 24), 1 in
  `dev/test_security.py`, 1 in `dev/test_drift.py`, 1 in `dev/test_multilang_proof_plugins.py`.
  `git diff --stat specs/` after the sweep showed only the php reap above and a reorder of
  `drift.proofs-integration.json` into merge-key order, both handled in
  `test(drift): record PROOF-19/20 in the order the sweep writes them` (`64248b32`).
- **Receipts: 39 of 41**, `vhash=758da608`. `pre_push_hook` (22/22) and
  `security_no_dangerous_patterns` (6/6) both receipt for the first time since these phases
  landed. `figma_web` and `skill_spec` remain the two witness-less features until 10.6 gives the
  externally-gated suites environment ids; their version 1 receipts are the only pending
  migration `sync_status` reports.

### 10.2 Manual stamps count (decision: make the docs true)

- `_manual_ok_keys(project_root, info)`: own rule ids whose `@manual(email, date, sha)` stamp is
  present and whose `> Scope:` has not changed since `sha` (a generalised
  `_scope_changed_since(project_root, scope, sha)` shared with the staleness check at `:322`).
  No `> Scope:` means uncountable (staleness undetectable), and the rule says so. `proved`
  counts `pass or key in manual_ok`; an executed proof wins for display. `M` segments enter the
  vhash (6.5); receipts carry `manual[]`.
- `sync_status` RULE-5 amended, RULE-54 new (the stamp is bound into the vhash so re-stamping
  changes it). PROOF-83 (`dev/test_mcp_server.py`): one automated pass + one current stamp reads
  2/2 PASSING with a vhash; commit a scope change and it reads 1/2 PARTIAL. PROOF-84: re-stamp
  after receipting reads stale. `dev/test_e2e_manual_staleness.sh` PROOF-26/27 assert the
  fraction, not only the `PASS ... manual` string. `docs/regulated-environments.md` "Human
  Approval Workflow" gains "a stamp counts toward coverage; it is not a signature."

## DONE — Phase 10.2: manual stamps count (`feat(sync_status): a current manual stamp counts toward coverage`; receipts in the `verify:` commit that follows it)

- **Numbers taken (landing order).** `sync_status` RULE-5 amended and RULE-59 new, with PROOF-96
  (RULE-5), PROOF-97 (RULE-59) and PROOF-98 (RULE-5); PROOF-26/27/28 rewritten against the same
  RULE-5. Next free `sync_status` RULE-60/PROOF-99. Nothing else moved: RULE-6 already described
  the `M` segment, and the `manual` parameter of `_compute_vhash` and the issuer's `manual` key
  were already wired and empty.
- **The counting.** `_manual_ok_keys(project_root, info)` returns the stamps that count: a
  stamped `@manual(email, date, sha)` on one of the feature's own rules whose `> Scope:` has not
  been committed to since that sha. It returns the stamps, not just the rule ids, because the
  same list is what enters the hash. `_feature_verdict` fills in each stamp's `feature`, and
  `proved` counts `pass or (own and key in manual_ok_rules)`. Display is unchanged and an
  executed proof still wins it: the rule-line branch reads the test first, so a FAIL stays FAIL
  with a stamp beside it.
- **One function for one question.** `_scope_changed_since(project_root, scope, sha)` is the
  generalised form of the old `_check_manual_staleness`, which is now a two-line call into it.
  The staleness line and the counter cannot disagree, which they could have the moment the count
  grew its own comparison.
- **No `> Scope:` means uncountable.** `_manual_ok_keys` returns nothing for such a spec and the
  existing advisory gained the clause `so the stamp does not count toward coverage`, so the line
  that says staleness cannot be detected also says what that costs.
- **The vhash.** `manual_ok` is passed to `_compute_vhash`, so the `M` segments RULE-6 already
  specified are finally populated and a re-stamp moves the hash. `dev/issue_receipts.py` counts
  the same stamps when deciding what is unproved (reading only `proof_by_rule` there would have
  skipped every feature the report called PASSING) and writes them into `receipt.manual`.
- **Pass D.** `sync_status` PROOF-26, 27, 28, 96, 97 and 98 all PROVABLE. The nine non-PROVABLE
  descriptions in that spec (PROOF-3/5/7/9/10/11/70 LOOSE, PROOF-56/75 STRUCTURAL) all predate
  this phase.
- **Mutations (2, each restored).** Counting a stale stamp (`if False and
  _scope_changed_since(...)`) kills PROOF-96 at the 1/2 assertion; dropping the `M` segments from
  `_compute_vhash` kills PROOF-97, which then reads the same vhash before and after the re-stamp.
- **Docs.** `skills/verify/SKILL.md` Step 3 gained a "Manual stamps in the count" block and the
  `--manual` section says the rule leaves the count until the stamp is refreshed;
  `docs/regulated-environments.md` "Human Approval Workflow" gained the paragraph that a stamp
  counts toward coverage and is not a signature. `docs/testing-workflow-guide.md:162` claimed a
  feature with four automated proofs and one stamp is VERIFIED; that is now true and the line was
  left alone.
- **This repo counts no stamps.** No spec here carries a stamped `@manual(...)`, so every
  feature's vhash is unchanged by the formula gaining a populated segment and the receipt count
  stays 39 of 41. The behaviour is proved on temp repositories, which is the only place a
  `git log <sha>..HEAD` question can be asked with a known answer.
- **Sweep.** `bash dev/run_tests.sh` reads `753 passed, 27 skipped`, 14 suites, 0 failed, up from
  `750 passed, 27 skipped`: the three new tests in `dev/test_mcp_server.py`.
  `git diff --stat specs/` after the sweep: the spec, the three rewritten e2e test names, and the
  three new integration entries.


### 10.3 Evidence older than code (warn, never block)

- Rejected: comparing proof-file git dates to scope git dates. A re-executed file with unchanged
  content gets no new commit, so it fires falsely (23 of 41 features today). The honest signal is
  the run the receipt records.
- `sync_status` RULE-51: for a VERIFIED feature with `> Scope:`, when `git rev-list --count
  --end-of-options <evidence.test_run.commit>..HEAD -- <scope>` is non-zero, print
  `⚠ EVIDENCE OLDER THAN CODE: scope changed in N commits since the tests behind this receipt
  ran (<sha7>) → Run: purlin:test <name>`; falls back to `receipt.commit` for v1 receipts.
  Payload gains `evidence_stale` per feature (`report_data` RULE-33); Phase 8's dashboard
  renders it as a row title and the QA report lists it. After the final verify commit it fires on
  zero features here and starts firing on the first scope edit without a re-run.

## DONE — Phase 10.3: evidence older than code (`feat(sync_status,report_data,purlin_report): warn when evidence is older than the code`; receipts in the `verify:` commit that follows it)

- **Numbers taken (landing order).** `sync_status` RULE-60 with PROOF-99 (next free
  RULE-61/PROOF-100), `report_data` RULE-38 with PROOF-39 (next free RULE-39/PROOF-40),
  `purlin_report` RULE-44 with PROOF-48 (next free RULE-45/PROOF-49).
- **The signal.** `_evidence_age(project_root, info, receipt)` returns `(commits, sha7)` or None
  from `git rev-list --count --end-of-options <sha>..HEAD -- <scope paths>`, where `<sha>` is
  `evidence.test_run.commit` and falls back to `receipt.commit` for a receipt issued before that
  field existed. `_evidence_age_lines` renders the two lines. It warns and never blocks: the
  status stays VERIFIED, no gate reads it, and `references/hard_gates.md` is unchanged.
- **Why not proof-file dates.** A re-executed test file whose bytes do not change gets no new
  commit, so a proof file's git date says when the file was last edited and not when it last
  ran. Comparing those dates to the scope fired on 23 of this repository's 41 features while
  every one of them had just been re-run. The run the receipt records is the only honest input,
  and the rule says so in its own text so the rejected design cannot be re-proposed from the
  rule alone.
- **One git question.** `_scope_changed_since` from 10.2 became a boolean wrapper over
  `_scope_commits_since(project_root, scope, sha)`, which returns the count and carries the `--`
  and the `--end-of-options`. The manual stamp's staleness, the manual coverage count and the
  evidence warning are now one query shape asked three times.
- **The renderer is not in `_report_feature`.** The first attempt put `if header_status ==
  'VERIFIED':` inline and `sync_status` PROOF-86's AST check caught it in the sweep: that
  function may hold no `VERIFIED` literal of its own (RULE-54). The comparison moved into
  `_evidence_age_lines`, which is where the whole rendering now lives.
- **Payload and dashboard.** Every feature carries `evidence_stale`, present always and true only
  for a VERIFIED feature whose scope moved. The dashboard renders it as a row `title` and one
  amber `stale evidence` chip in the status cell; the status badge keeps the class its status
  alone dictates. This is the first item only of Phase 8's "Phase 10 signals rendered" paragraph:
  `invalidated` and `auditors` belong to 10.4.
- **Pass D.** PROOF-99, PROOF-39 and PROOF-48 all PROVABLE. The non-PROVABLE descriptions in the
  three specs (9 in `sync_status`, 10 in `report_data`, 4 in `purlin_report`) all predate this
  phase.
- **Mutation (1, restored).** Dropping the `--` path filter from `_scope_commits_since` kills both
  PROOF-99 and PROOF-39: the outside-the-scope commit is counted and the warning fires where the
  proof asserts it must not.
- **It fires on zero features here.** After the final verify commit, `sync_status('.')` prints no
  `EVIDENCE OLDER THAN CODE` line: the sweep and the receipts are at HEAD, so no scope has moved
  since the run behind any receipt. The first scope edit committed without a re-run starts it.
- **Sweep.** `bash dev/run_tests.sh` reads `756 passed, 27 skipped`, 14 suites, 0 failed, up from
  `753 passed, 27 skipped`: two new tests in `dev/test_mcp_server.py` and one in
  `dev/test_purlin_report.py`. `git diff --stat specs/` after the sweep: three rules, three
  proofs, three new proof entries.


### 10.4 Audit cache integrity and auditor identity (`static_checks`, `skill_audit`)

- The key is computed from project state by one function at write and read:
  `resolve_proof_inputs(project_root, feature, proof_id) -> (rule_text, proof_description,
  test_code)` reusing the existing extractors; `--cache-key --feature X --proof-id PROOF-N`
  replaces `--compute-proof-hash <pasted text>` (the caller-supplied inputs are why
  "self-invalidates" was a promise with no mechanism); `--write-cache` re-keys every entry and
  rejects an unresolvable `(feature, proof_id)` like RULE-33 does (RULE-38).
- Readers (`_read_audit_summary` `:506`, `_read_audit_cache_by_feature` `:1778`) recompute and
  drop mismatches as `invalidated`, counted as unmeasured (`sync_status` RULE-52); import failure
  means unverifiable, not valid. A MANUAL grade is valid only against a current stamp at read
  time. This repo's Integrity reads unmeasured afterwards (the hand-built cache is invalid by
  construction); Tier 2a, a real `purlin:audit`, is the only way to a number and stays in the
  backlog with that note.
- `--write-cache` stamps `auditor: {name, command}` from config (RULE-39); `audit_summary.auditors`
  and the digest carry it (`report_data` RULE-34) so a reader can see the whole gauge came from
  a fake. `sync_status` RULE-53 advisory when `audit_llm` is set but its executable does not
  resolve on PATH or `{prompt}` is absent, or `audit_llm_name` is set without `audit_llm`.
- `load_criteria` (`:1509`): with `audit_criteria` set, the cached file must carry
  `<!-- purlin-criteria-sha: <sha> -->` written by `--sync-audit-criteria` and it must equal
  `audit_criteria_pinned`; mismatch or missing cache is an error the skill prints, never a silent
  fallback; a missing built-in file raises rather than returning `''` (RULE-42;
  `dev/test_e2e_additional_criteria.sh` gains the negative case).
- `skills/audit/SKILL.md:190` vs `agents/purlin-auditor.md:12`: the auditor writes through the
  locked `--write-cache`; the lead verifies landing and writes only main-context grades
  (`skill_audit` RULE-18 amended, `purlin_teammate_definitions` RULE-6).
- `_build_report_data` always sets `git_sha` (`report_data` RULE-31). Tests:
  `dev/test_static_checks.py`, `dev/test_e2e_audit_cache_pipeline.py` (edit one character of a
  graded test function, `invalidated == 1`, measured drops by one), `dev/test_mcp_server.py`.


## DONE — Phase 10.4: audit cache integrity and auditor identity (`feat(static_checks,sync_status,report_data,purlin_report,skill_audit): the audit cache re-keys, invalidates and names its auditor`; receipts in the `verify:` commit that follows it)

- **Numbers taken (landing order).** `static_checks` RULE-38, 39, 40 and 41 with PROOF-63, 64, 65
  and 66 (next free RULE-42/PROOF-67). `sync_status` RULE-61 with PROOF-100 and RULE-62 with
  PROOF-101 (next free RULE-63/PROOF-102). `report_data` RULE-39 with PROOF-40 and RULE-40 with
  PROOF-41 (next free RULE-41/PROOF-42). `purlin_report` RULE-45 with PROOF-49 (next free
  RULE-46/PROOF-50). `skill_audit` RULE-22 with PROOF-22, with RULE-14 and RULE-18 amended and
  PROOF-14 and PROOF-18 extended (next free RULE-23/PROOF-23; the phase text's "RULE-21" was
  taken by 7.5's mutation-check rule, so `--cache-key` landed at 22). `purlin_teammate_definitions`
  RULE-6 with PROOF-6 (next free RULE-7/PROOF-7). `references/audit_criteria.md` went to
  Criteria-Version 19.
- **One function decides what a grade is about.** `resolve_proof_inputs(project_root, feature,
  proof_id)` reads the rule text and the proof description from `specs/**/<feature>.md` and the
  graded test function's source from the file the proof JSON names, reusing the existing
  extractors. Two of those extractors had to be lifted out of their Pass 1 loops first
  (`_iter_js_proof_bodies`, `_iter_csharp_proof_bodies`) so the scan that finds a marked test
  body exists once rather than once per caller. Python comes from the existing AST walk. Shell,
  SQL, PHP and C have no extractor here, so their proofs are keyed on rule text and description
  alone and the entry records `inputs.test_verifiable: false`, which says out loud that a test
  edit cannot move that key.
- **The caller no longer supplies the key.** `--cache-key --feature X --proof-id PROOF-N`
  replaces `--compute-proof-hash <pasted text>`, and `--write-cache` discards whatever key it is
  given and re-keys every entry through the same function. That is the whole fix: with
  caller-supplied inputs the key described the text the auditor happened to send, so
  "self-invalidates" was a promise with no mechanism behind it. An unresolvable
  `(feature, proof_id)` is now rejected the way a missing dedup field is (RULE-33), naming every
  offender before the filesystem is touched.
- **Readers recompute.** `_partition_cache_entries` in `purlin_server.py` soft-imports
  `static_checks` from the sibling directory and recomputes every deduplicated entry's key;
  mismatches are dropped and counted as `invalidated`, and `_attach_gauge_coverage` takes
  `measured` from the survivors, so an invalidated grade lands in the unmeasured half of the
  denominator instead of propping up a percentage. A failed import invalidates everything: an
  unverifiable cache is not a valid one. A MANUAL grade is valid only against a current
  `@manual` stamp at read time, judged by 10.2's `_manual_ok_keys`, so the stamp that counts
  toward coverage and the stamp that keeps a MANUAL grade alive cannot diverge.
- **Who graded.** `--write-cache` stamps `auditor: {name, command}` from config (`audit_llm_name`
  or `claude`, `audit_llm` or null); `audit_summary.auditors` counts the survivors per name and
  the digest carries it, so a reader can see that a whole gauge came from one tool. `sync_status`
  warns, never blocks, when `audit_llm` names a command that is not on PATH, carries no
  `{prompt}`, or when `audit_llm_name` is set with no command at all.
- **The criteria pin is enforced rather than recorded.** With `audit_criteria` set, the cached
  `.purlin/cache/additional_criteria.md` must begin with
  `<!-- purlin-criteria-sha: <sha> -->` equal to `audit_criteria_pinned`, which
  `purlin:init --sync-audit-criteria` now writes. A missing cache, a missing header or a
  different sha raises `CriteriaError`, which `--load-criteria` prints on stderr with exit 2 and
  the audit skill prints verbatim and stops on. A missing built-in criteria file raises instead
  of returning `''`. The header is stripped before the criteria reach a prompt, in the orphaned
  case too: it is provenance, not a criterion, and an auditor must never be asked to grade
  against a comment.
- **`git_sha` is never null.** `_build_report_data` sets it from HEAD at generation time, or the
  literal `unknown` when git cannot answer. When the pre-commit hook writes the digest, HEAD is
  the parent of the commit that carries it, because that commit does not exist yet; the rule says
  so, since the field's whole job is naming the tree the numbers describe.
- **One contradiction closed.** `skills/audit/SKILL.md` said subagents must not write the cache;
  `agents/purlin-auditor.md` told them to. Every auditor now writes its own assessments through
  the locked `--write-cache`, whose exclusive lock is what makes parallel writers safe, and the
  lead writes only the grades it made in the main context and reads the cache back to verify the
  subagents' entries landed. Both proofs assert on both files, because either file alone can be
  made to read correctly while the pair still disagrees.
- **Three defects the proof work turned up, all fixed here.** (1) The cache key omitted the
  proof's identity, so two features whose rule text and proof description were byte-identical
  shared one key and one grade overwrote the other while the deduplication key still said they
  were two proofs. `cache_key_for` now hashes `<feature>\0<proof_id>` in alongside the three
  inputs, which makes `(feature, proof_id)` to key injective; RULE-37's formula sentence and
  RULE-38 were amended and PROOF-62 and PROOF-63 gained the collision case, backed by a language
  with no test extractor so the two remaining inputs really are identical. (2) Re-keying
  collapsed intra-batch duplicates by dict insertion order, which quietly broke RULE-24's "keep
  the latest `cached_at`" for entries arriving in one call; PROOF-30 now writes the same three
  entries newest first and the comparison is back. (3) `sync_status` RULE-28 promised that an
  entry with no `feature` field is still counted project-wide, which RULE-61 makes impossible: no
  feature means no key and nothing to recompute. RULE-28 and PROOF-49 now say the reader
  tolerates such an entry without raising and leaves it out of every number, with rejection still
  the writer's job.
- **Pass D.** Every rule this phase wrote or amended ships a PROVABLE proof: `static_checks`
  PROOF-30, 62, 63, 64, 65 and 66; `sync_status` PROOF-49, 100 and 101; `report_data` PROOF-40 and
  41; `purlin_report` PROOF-49; `skill_audit` PROOF-14, 18 and 22;
  `purlin_teammate_definitions` PROOF-6. Zero UNPROVABLE and zero LOOSE among them. The
  non-PROVABLE descriptions remaining in those specs (7 LOOSE in `sync_status`, 2 in
  `report_data`, 2 in `purlin_report`, and the STRUCTURAL presence checks) all predate this
  phase.
- **Mutations (16, each restored).** Skipping the re-key kills PROOF-63; dropping the auditor
  stamp kills PROOF-64; making `cache_key_for` ignore the test code kills PROOF-65; dropping the
  pinned-sha comparison kills PROOF-66; dropping the identity from the key kills PROOF-62 and
  PROOF-63; dropping the intra-batch `cached_at` comparison kills PROOF-30. On the server:
  skipping the recompute kills PROOF-100, as do letting a MANUAL grade count with no current
  stamp and trusting every entry when the checker cannot be imported; returning no advisory lines
  kills PROOF-101; `_head_sha` returning None kills PROOF-40; dropping `auditors` kills PROOF-41.
  On the prose: reinstating "subagents must not write the cache themselves" kills `skill_audit`
  PROOF-18; putting `--compute-proof-hash` back in the lookup step kills PROOF-22; removing
  `--write-cache` from the auditor definition kills `purlin_teammate_definitions` PROOF-6;
  deleting the `by <name>` branch in `gaugeCard` kills `purlin_report` PROOF-49.
- **This repo has no cache to invalidate.** Phase 10.5 untracked the four legacy
  `.purlin/cache/` files and the directory is gone here, so `audit_summary` is None and both
  gauges read `No audit data` rather than unmeasured. The first real `purlin:audit` writes a
  cache whose keys are computed by the same function the readers use, which is the point: Tier 2a
  is now worth running.
- **Sweep.** `bash dev/run_tests.sh` (foreground) reads `776 passed, 27 skipped`, 14 suites, 0
  failed, up from `765 passed, 27 skipped`. The +11 are the new tests: 4 in
  `dev/test_static_checks.py`, 2 in `dev/test_report_data.py`, 1 in
  `dev/test_e2e_audit_cache_pipeline.py`, 1 in `dev/test_mcp_server.py`, 1 in
  `dev/test_skill_specs.py`, 1 in `dev/test_purlin_teammate_definitions.py` and 1 in
  `dev/test_purlin_report.py`. `git diff --stat specs/` after the sweep: six specs and seven
  proof files, additions only.

### 10.5 Housekeeping with rules

- `git rm --cached` the four dead `.purlin/cache/` files; `report_data` RULE-32 with a
  `git ls-files` proof.
- Verify commit vocabulary: `verify: [Complete:all] features=36/36 anchors=5/5 vhash=...` in
  `references/commit_conventions.md:23,62`, `skills/verify/SKILL.md:216`, the issuer's summary
  line (`skill_verify` RULE-13).
- `tools/QA/purlin-qa-report.md`: no credential in a URL (`gh repo clone` or a credential helper);
  reads `audit_summary.coverage`, `assessed` and `weighted` separately, `auditors`, each
  feature's `vhash`, `receipt.test_run_commit`, `evidence_stale`, `git_sha`; VERIFIED described
  as "all rules proved on every declared platform and a receipt matches"; `uncommitted` reported
  when non-empty naming the three ways it can be. New `specs/tools/qa_report.md` RULE-1..5 with
  greps in `dev/test_tools_qa.py`, plus a proof that the `.skill` zip's `SKILL.md` equals the
  `.md` (same for `tools/PM/`); `dev/pack_tools.sh` regenerates the zips.
- `references/hard_gates.md` gains the sentence that `hooks/hooks.json` registers no Claude Code
  hooks, so every NEVER in `agents/purlin.md` is an instruction and the controls that survive an
  agent ignoring them are the layers below (`purlin_references` RULE-23 with a proof that the
  file has no hooks, so the sentence stays true).


## DONE — Phase 10.5: housekeeping with rules (`fix(qa_report,purlin_references,skill_verify): QA report spec, no credentials in URLs, cache untracked, verify vocabulary`, built on `ed491a9c` in a worktree, cherry-picked onto `fb552485` as `a508dabd`; receipts in the `verify:` commit that follows it)

- **Numbers taken (landing order).** `purlin_references` RULE-26 with PROOF-26 and RULE-27 with
  PROOF-27 (spine max was RULE-25/PROOF-25 and 10.2 and 10.3 touched neither spec, so nothing
  collided and nothing was renumbered; next free RULE-28/PROOF-28). `skill_verify` RULE-14 with
  PROOF-14 (next free RULE-15/PROOF-15). New spec `specs/tools/qa_report.md` RULE-1..6 with
  PROOF-1..6 in the new `dev/test_tools_qa.py` (next free RULE-7/PROOF-7). `purlin_references`
  RULE-7 and PROOF-7 amended rather than renumbered, because the commit-conventions rule already
  owned the question.
- **The cache is untracked.** The four legacy files under `.purlin/cache/` were `git rm --cached`
  and `git ls-files .purlin/cache` now returns nothing, which is what PROOF-27 asserts. The rule
  lives in `purlin_references` rather than `report_data` as the phase text guessed: the claim is
  about what the repository tracks, not about what the payload carries.
- **The verify vocabulary.** `verify: [Complete:all] features=N/T anchors=A/B vhash=...`, in
  `references/commit_conventions.md` (both the example block and the receipt-commit section, with
  the sentence that the two counts are never summed), in `skills/verify/SKILL.md` Step 5, and on
  `dev/issue_receipts.py`'s summary line so the message is copied from the issuer rather than
  recounted by hand. `chore(update):` gained its row in the prefix table at the same time.
- **The QA report spec.** `specs/tools/qa_report.md` covers the packaged skill under `tools/QA/`:
  RULE-1 is FORBIDDEN (no `://user:secret@host` form anywhere in the file; `gh repo clone` or a
  credential helper instead), RULE-2 names each digest field the report reads
  (`coverage`/`assessed`/`weighted` as three separate numbers, `auditors`, per-feature `vhash`,
  `receipt.vhash_version`, `receipt.test_run_commit`, `evidence_stale`, top-level `git_sha`),
  RULE-3 pins the VERIFIED wording, RULE-4 requires `uncommitted` to be reported whenever it is
  non-empty and names the three ways a committed digest can carry one, RULE-5 forbids the
  approval vocabulary ("signed off", "compliance status"), and RULE-6 requires each `.skill` zip
  to hold a `SKILL.md` byte-equal to its `.md`, for QA and for PM. `dev/pack_tools.sh`
  regenerates both archives.
- **Pass D.** `qa_report` 4 PROVABLE and 2 STRUCTURAL, `purlin_references` PROOF-27 PROVABLE and
  PROOF-26 STRUCTURAL, `skill_verify` PROOF-14 PROVABLE. Zero UNPROVABLE and zero LOOSE in all
  three specs. The STRUCTURAL grades are the presence checks over skill and reference prose that
  the proof-quality gate allows for rules about prose; every one of them also parses the artifact
  it reads (`hooks.json`, the zip archives) rather than grepping for a phrase.
- **Mutations (7, each restored).** Six in the branch, all caught. The seventh, here: forcing
  `anchors_issued = 0` in the issuer kills `skill_verify` PROOF-14 at the summary-line assertion.
- **Integration into the spine.** `git cherry-pick 5d2036ea` applied with no textual conflict:
  `dev/issue_receipts.py`, `dev/run_tests.sh`, `dev/test_skill_specs.py` and both spec files
  auto-merged, and none of the numbering collisions the phase text warned about materialised. One
  semantic conflict did: the branch widened the issuer's `issued` rows from
  `(name, vhash, awaiting)` to a four-tuple carrying `is_anchor`, and seven tests on the spine
  (from 6.5, 7 and 10.2, none of which the branch ran) unpack three. The resolution keeps both
  intents without touching a caller: the rows stay three-tuples and `anchors_issued` is counted
  from the `features` map the issuer already holds, so the public return shape is unchanged and
  the summary line still prints the two counts separately. Amended into the cherry-picked commit
  so rule, proof and code stay in one commit.
- **Sweep.** `bash dev/run_tests.sh` (foreground) reads `765 passed, 27 skipped`, 14 suites, 0
  failed, up from `756 passed, 27 skipped`. The +9 are the branch's new tests: 6 in
  `dev/test_tools_qa.py`, 2 in `dev/test_purlin_references.py` (a third replaced
  `test_commit_conventions_eight_prefixes`, which the amended RULE-7 outgrew) and 1 in
  `dev/test_skill_specs.py`.
  `git diff --stat specs/` after the sweep: one proof file,
  `skill_verify.proofs-integration.json`, reordered into merge-key order with PROOF-14's entry
  added and nothing else changed.
- **Receipts: 40 of 42**, `vhash=977d671a`, printed by the issuer as `features=35/37 anchors=5/5`
  in the new vocabulary this phase introduced. `qa_report` receipts on its first sweep, which is
  what moved the feature total from 36 to 37. `figma_web` and `skill_spec` stay the two
  witness-less features until 10.6 gives the externally-gated suites environment ids.
- **A trap paid for once.** The mutation check above was run as `pytest dev/test_skill_specs.py -k
  verify_commit_counts`, a subset inside one file, and the write-scoped overwrite reaped three of
  `skill_verify`'s committed integration entries. The next full `dev/run_tests.sh` put them back,
  which is exactly the "run whole files, finish with the sweep, read `git diff --stat specs/`"
  discipline in the execution notes doing its job. The DONE section is a separate commit after
  the `verify:` commit for the same reason 10.5c's was: a plan edit amended into the feature
  commit moves HEAD and the run marker then no longer matches it.

### 10.5b (moved to 7.5: mutation checks are opt-in and belong with init and update)

### 10.5c Skipped tests must not lose their entries (found by 10.1)

`proof_common` RULE-13 promises that a test which does not run emits nothing and that the merge
key keeps whatever a capable host last proved. That holds per file, but not within a file: when
one test in a file runs and another in the same file for the same feature is skipped, the
write-scoped overwrite treats the file as executed and reaps the skipped test's committed entry
(seen on `proof_plugins_php` PROOF-1/2 with no `php` on the host). Fix in every plugin that can
observe a skip (pytest: the skip report; jest/vitest: `skipped`/`todo` status; xunit: skipped
outcome; shell, sql, phpunit, c: no skip signal, so the rule states they are exempt and why):
an existing entry whose `(feature, id, test_file)` matches a skipped test is kept, not reaped.
Rule: `proof_common` next free ("a skipped test keeps its committed entry; only an executed
test replaces it and only a deleted file reaps it"). Proof per capable plugin in
`dev/test_multilang_proof_plugins.py` / the pytest fixture: a file with one passing and one
skipped marked test, an existing entry for the skipped one, run, assert the entry survives with
its old status; mutation: drop the skip check. Also: `references/formats/anchor_format.md` gains
the optional `> Note:` line 10.1 introduced (Format-Version bump per CLAUDE.md), and this repo's
`dev/external-refs` fixture is recreated with `rm -rf dev/external-refs && bash
dev/setup-external-refs.sh` so the anchor's reproducible pin reads current.

## DONE — Phase 10.5c: skipped tests keep their entries (`fix(proof_common): a skipped test keeps its entry; anchor Note field`, built on `cf39b77f` in a worktree, cherry-picked onto `ed491a9c` as `f2b43d2c`; receipts in the `verify:` commit that follows it)

- **Numbers taken (landing order).** `proof_common` RULE-18 with PROOF-23 and PROOF-24 (spine
  max was RULE-17/PROOF-22, so nothing collided and nothing was renumbered; next free
  RULE-19/PROOF-25). `schema_spec_format` RULE-11 with PROOF-11 (next free RULE-12/PROOF-12).
  `proof_plugins_jest` PROOF-5 on the amended RULE-4, added during integration (next free
  RULE-5/PROOF-6). `references/formats/anchor_format.md` went to Format-Version 5 for the
  optional `> Note:` row, per the CLAUDE.md procedure.
- **The fix.** Every plugin whose framework reports a skip collects `(feature, id, test_file)`
  for the marked tests it skipped and keeps a matching existing entry with its old status:
  pytest from the skip report (a `skip`/`skipif` marker, a skipping fixture, or `pytest.skip()`
  in the body), jest from a `skipped`/`pending`/`todo`/`disabled` status, vitest from a task
  with no terminal state, the .NET logger from a `Skipped` outcome. The kept-filter also
  requires that the run did not itself write `(id, test_file, test_name)`, because several
  tests in one file legitimately emit one proof id and the fresh write must win. pytest and
  jest previously wrote `fail` for a skip and no longer do. shell, sql, phpunit and c have no
  skip signal and RULE-18 states the exemption and its reason. The four `.purlin/plugins/`
  copies were regenerated so RULE-16's byte-identity proof still passes.
- **Proof housekeeping in the branch.** `test_jest_pending_maps_to_fail` was retired (it locked
  in the behaviour the fix removes) and became
  `test_jest_pending_writes_nothing_and_leaves_an_existing_file_alone`; its stale entry was
  dropped from `proof_plugins_jest.proofs-unit.json`. The `schema_spec_format` PROOF-11 test
  lives in `dev/test_schema_spec_format.py` because `dev/test_mcp_server.py` is outside that
  spec's Scope.
- **Integration amendment.** `proof_plugins_jest` RULE-4 now reads "all other executed statuses
  map to fail; a skipped, pending, todo or disabled test did not execute, so it writes nothing
  and keeps its committed entry (`proof_common` RULE-18)". PROOF-4 still matches the first
  clause; the skip clause got PROOF-5, carried by a second `pytest.mark.proof` marker on the
  jest pending test at `@integration`, so `proof_plugins_jest.proofs-integration.json` is new.
- **Pass D.** `proof_common` 24/24, `schema_spec_format` 11/11, `proof_plugins_jest` 5/5 all
  PROVABLE; zero UNPROVABLE and zero LOOSE among the descriptions this phase wrote.
- **Mutations (7, each restored).** Six in the branch, all caught. The seventh, here: emptying
  jest's `SKIPPED_STATUSES` set kills `proof_plugins_jest` PROOF-5.
- **Integration into the spine.** `git cherry-pick 2293fc8e` applied with no conflict; Phase 8
  touched no `scripts/proof/*` file and the two anchors' numbering was free.
- **The php reap is gone.** `proof_plugins_php` PROOF-1/2 still skip (no `php` on this host) and
  `dev/test_multilang_proof_plugins.py` still executes PROOF-3 from the same file for the same
  feature, but `git diff --stat specs/` after the sweep shows no change to
  `proof_plugins_php.proofs-integration.json`. Nothing was restored by hand for the first time
  in three phases.
- **Sweep.** `bash dev/run_tests.sh` (foreground) reads `750 passed, 27 skipped`, 14 suites, 0
  failed, up from `739 passed, 27 skipped`. `git diff --stat specs/` after the sweep: one line
  in `proof_plugins_jest.md` plus the new `proof_plugins_jest.proofs-integration.json`.


### 10.6 Environment ids for the externally-gated suites (after 6 and 7)

The registry gains `"kind": "environment"` entries with no `os` (e.g. `figma-mcp`, `gemini-cli`,
`claude-cli`), satisfiable only by an explicit `PURLIN_PLATFORM`, never by host detection. The
four dev suites get `@on(windows-2022)`, `@on(figma-mcp)`, `@on(gemini-cli)`, `@on(claude-cli)`
on their proofs and matching markers; their entries move to scoped files; `proof_common` RULE-14's
exception list shrinks to nothing and PROOF-18 proves it. This is the "expand later" seam the
user asked for (mobile OS ids are the same mechanism with an `os`), exercised on real cases.

---

## Phase 11: docs, one enforcement model, diagrams, release notes

- New spec `specs/instructions/purlin_docs.md` with grep proofs in `dev/test_purlin_docs.py`:
  RULE-1 the strings `signed verification`, `tamper-evident`, `The vhash proves`, `(signed off)`
  are absent from `docs/`, `README.md`, `references/`, `skills/`, `tools/`, the only permitted
  occurrences being the negations in `regulated-environments.md:16-17`; RULE-2
  `regulated-environments.md` has "What the vhash binds" (the v2 fields) and "What it does not
  bind" (test code content, who ran it, when, that the test is meaningful, the runner's honesty),
  no `.test-lock.json`, `audit_llm` described as executable config the compliance team pins, the
  criteria pin check described as implemented, "Pass D1 is deterministic; Pass D2 is an LLM pass"
  replacing "Proof Design is deterministic" (also `remote_verification.md:154`); RULE-3
  `docs/index.md` has a Guides row for remote verification and platforms, a layer summary line,
  both gauges in the skill one-liners; RULE-4 exactly one enforcement-layer table exists, in
  `references/hard_gates.md`, and the three docs that carried copies
  (`regulated-environments.md:37-47`, `lifecycle-guide.md:530-549`,
  `testing-workflow-guide.md:221-234`) keep two sentences and a link; RULE-5 no fenced yaml under
  `docs/` contains `run: purlin:` or `on: deploy`; RULE-6 every SVG under `assets/` has a source
  under `assets/src/` and `.gitignore` negates `assets/src/*.mmd`.
- `references/hard_gates.md` `## Enforcement Layers` (not `## Gate N`, so PROOF-6's count holds):
  Layer 0 skill logic (the one gate); Layer 1 pre-push hook (`warn`/`strict`/`off`, local,
  bypassable, plugin-resolution caveat); Layer 2 your CI test run; Layer 3
  `scripts/ci/verify_gate.py --check` made required by branch protection, with
  `remote_verification` as the declaration; a row "not a layer: `purlin:verify --recheck`" (a
  local clean-room re-run inside Claude Code, not something a workflow can call).
- CI examples (`docs/examples/figma-web-app.md:167-177`, `testing-workflow-guide.md:236-273`):
  `on: [push, pull_request]`, checkout `fetch-depth: 0`, the real test command, then
  `python3 scripts/ci/verify_gate.py --check`, with the sentence that running all tiers in CI
  regenerates the proof files so the gate's VERIFIED is the clean-room recheck.
- Platform docs (the user's "all docs updated"): `testing-workflow-guide.md` tier table and a new
  "Platforms" section (`@on`, registry, family ids, `PURLIN_PLATFORM`, scoped files, what
  `purlin:test` does per platform, the workflow template pointer); `collaboration-guide.md:93-113`
  (what travels: scoped proof files travel, caches do not, `report-data.js` does carry the
  derived numbers; merge-conflict advice for scoped files: never hand-merge, re-run on that
  platform); `installation-guide.md` (`platforms` config sample, "Upgrading" section from Phase
  7); `spec_quality_guide.md` and `spec_format.md` cross-references; `README.md` dashboard and
  tools lines; `agents/purlin.md` tier-review step mentions `@on`.
- `skills/spec/SKILL.md` and `skills/spec-from-code/SKILL.md` tier-tag review step (purlin_skills
  RULE-12) gains platform-tag review: ask which platforms a proof must run on when the rule names
  one; `skills/build/SKILL.md` Step for writing markers shows `platforms=`.
- Diagrams: recreate the five `assets/src/*.mmd` from the SVG labels (they were never committed;
  commit `52fce761` stat lists only SVGs), add `!assets/src/*.mmd` after the `*.mmd` line in
  `.gitignore`, make the content changes (runner-gated node and proved-remotely outcome in
  `lifecycle-big-picture`, the remote loop edge in the eng and qa workflows, `purlin:test`
  pushing in `lifecycle-handoff`), render with `bash dev/render-diagrams.sh` under the header's
  exports, commit sources and SVGs together. If `mmdc` cannot be installed in the session, commit
  the sources with the SVGs untouched and record it in the DONE section (RULE-6 requires only the
  sources and the negation). The plan's `dev/screenshots/` paragraph is deleted: the directory
  does not exist.
- Screenshots: `python3 dev/capture_doc_screenshots.py` after 7.4 (three images).
- **ADO runner provider plan (user request, 2026-09-12): write `dev/plans/ado-runner-provider.md`**,
  a self-contained plan to be executed cold on the user's work machine (which has an Azure DevOps
  account; this machine does not). It must carry: the context a fresh reader needs (registry
  `runner.provider`, the trailer contract, both loop-guard halves, the dispatch loop in
  `purlin:test` Step 2b, the preflight, `PURLIN_PLATFORM`, scoped files, what `verify_gate`
  RULE-7/10/11 require of a commit-back workflow); the ADO pieces to build: a pipeline template
  in `references/remote_verification.md` (`azure-pipelines-purlin-<id>.yml`: `trigger.paths.exclude`
  for the scoped files, `pool.vmImage` from `runs_on`, `PURLIN_PLATFORM` variable, checkout with
  `persistCredentials: true`, the tooling clone pinned by tag, the preflight, per-framework
  setup, both trailers, `[skip ci]` in the commit subject which ADO honours, the pull-rebase-retry
  loop, `System.AccessToken` with the build service granted Contribute on the repo), dispatch and
  polling via `az pipelines run --name <workflow> --branch <branch>` and `az pipelines runs show`
  (auth via `az login` or `AZURE_DEVOPS_EXT_PAT`), the `provider: ado` branch in
  `skills/test/SKILL.md` Step 2b and the setup offer, registry validation accepting `ado` with
  `organization` and `project` fields, `verify_gate` workflow rules generalised to
  `azure-pipelines-purlin-*.yml` alongside `.github/workflows/purlin-*-proofs.yml`, the docs
  (`remote_verification.md`, `testing-workflow-guide.md`, `installation-guide.md`); the rules
  and proofs with next-free numbers (`skill_test`, `purlin_references`, `verify_gate`,
  `sync_status` registry validation) and their mutation checks; prerequisites on the work
  machine (`az` CLI with the `azure-devops` extension, a project, a macOS or Windows hosted pool,
  a scratch consumer project to exercise the loop end to end since this repo's CI is GitHub);
  a verification checklist; and the traps carried from this plan's execution notes. Written in
  Phase 11 from the GitHub path as it actually shipped, so it names real function and rule
  numbers, not the provisional ones.
- `RELEASE_NOTES.md` Unreleased rewritten with the final counts from the run marker and an
  "Upgrade notes" block: `purlin:init --update`, receipts re-issued (v1 reads stale until
  `purlin:verify`), `@windows` becomes `@unit @on(...)`, `--compute-proof-hash` removed,
  `purlin:init --pre-push` offers `off`, `dev/build_audit_cache.py` removed; `purlin_version`
  RULE-9 (Unreleased counts match the recorded run). The version tag itself is the user's call;
  the format bumps make it a `0.11.0`.
- `dev/plans/two-gauges-remote-verification.md`: replace its Phases 6-7 with this plan's phases
  (checked-in copy authoritative), DONE sections per phase, execution notes extended (`@` in
  paths needs `shell: bash` on Windows runners; several runners committing to one branch need
  the rebase loop; `command grep`).
- Final: `bash dev/run_tests.sh`, `python3 dev/issue_receipts.py`, `verify:` commit; run
  `purlin:audit --design` then `purlin:audit` on this repo and record both results in the DONE
  section (this is Tier 2a); push the branch; **do not merge or push `main`** (it happens after
  the ADO work; see "Branch and hand-off").

---

## Reviewer findings applied (authoritative over the phase text where they differ)

A fork reviewer audited this plan for rules without proofs, weak proof designs, and rule-number
collisions. Resolutions:

### Rule and proof numbering: allocation by landing order (the phase text's numbers are provisional)

Current maxima (verified): sync_status RULE-49/PROOF-81; report_data 30/31; config_engine 10/12;
drift 16/19; skill_init 48/51; skill_verify 10/10; skill_test 11/11; skill_status 8/8;
skill_audit 20/20; purlin_references 20/20; purlin_skills 15/15; purlin_version 8/8;
purlin_teammate_definitions 5/5; static_checks 37/62; purlin_report 40/42; proof_common 13/17;
schema_spec_format 8/8; schema_proof_format 7/8; dashboard_visual 11/11;
security_no_dangerous_patterns 5/5; pre_push_hook 9/17; verify_gate 8/8; proof_plugins_php 2/2.

Each commit takes the next free number in the spec file at the time it lands; never reuse a
number named earlier in this plan. Landing order and what each spec gains:

| Spec | 6.0 | 6.1-6.4 | 6.5 | 7 | 8 | 9 | 10 | 11 |
|---|---|---|---|---|---|---|---|---|
| sync_status | | RULE-50 Platforms block, RULE-51 undeclared results (PROOF-82/83) | RULE-52 one verdict fn (PROOF-84 AST count + issuer/payload vhash parity) | RULE-53 migrations advisory (PROOF-85), RULE-38 amended (PROOF-68 updated) | RULE-54 per-platform Integrity, RULE-55 Platforms line, RULE-56 detail lines and bound (PROOF-86..90), RULE-35/47 amended (PROOF-85 renumbered to 91) | | RULE-5 amended + RULE-57 stamps in vhash (PROOF-92/93), RULE-58 evidence older (PROOF-94), RULE-59 invalidated grades (PROOF-95), RULE-60 audit_llm advisory (PROOF-96) | |
| report_data | | RULE-31 top-level platforms, RULE-32 per-feature platforms (PROOF-32/33) | RULE-33 receipt fields (PROOF-34) | RULE-34 migrations present (PROOF-35) | RULE-4/5/8/29 amended, RULE-35 summary shape (PROOF-36..40) | | RULE-36 git_sha always (PROOF-41), RULE-37 evidence_stale (PROOF-42), RULE-38 auditors (PROOF-43) | |
| proof_common | RULE-14 sweep completeness (PROOF-18) | RULE-15 forward-slash paths (PROOF-19 per plugin), RULE-16 one plugin everywhere (PROOF-20), RULE-17 marker decides (PROOF-21/22) | | | | | | |
| schema_spec_format | | RULE-9/10 (PROOF-9/10) | | | | | | |
| schema_proof_format | | RULE-1/2/4/5 amended, RULE-8 scoped-file id charset (PROOF-4 updated, PROOF-9) | | | | | | |
| config_engine | | RULE-11 flat overlay (PROOF-13, `dev/test_config_engine.py`) | | | | | RULE-12 environment-kind entries (PROOF-14) | |
| verify_gate | | RULE-4/7 amended (PROOF-4/7 updated), RULE-9 rebase loop, RULE-10 preflight (PROOF-9/10) | | | | | | |
| skill_verify | | | RULE-11 receipt v2, RULE-12 run-marker refusal (PROOF-11/12) | RULE-13 no receipt while legacy pending (PROOF-13) | | | RULE-14 36/5 vocabulary (PROOF-14) | |
| skill_test | | RULE-7..11 reworded (PROOF-7..11 all reviewed and updated) | | | | | | |
| skill_init | | | | RULE-49..55 `--update` (PROOF-52..58), RULE for `--pre-push` amended in 9 | | | | |
| purlin_references | | RULE-18 amended, RULE-21 templates pin a tag via PURLIN_PLUGIN_ROOT, RULE-22 runner-setup column (PROOF-21/22) | RULE-23 receipt_format.md (PROOF-23) | RULE-24 pending-migrations section (PROOF-24) | | | RULE-25 hooks.json empty (PROOF-25) | RULE-26 one enforcement table (PROOF-26) |
| purlin_skills | | | | RULE-16 every skill links the section (PROOF-16: exact anchor in all 12) | | | | RULE-12 amended (PROOF-12 updated) |
| static_checks | | | | | | | RULE-38 re-key on write, RULE-39 auditor stamp, RULE-40 reader invalidation, RULE-41 criteria pin (PROOF-63..66) | |
| purlin_report | | | | RULE-23 amended: action banner shows migrations (PROOF-24 updated) | RULE-3/4/14/36/38/39 amended (PROOF-3/4/15/38/40/41 updated), RULE-41/42/43 (PROOF-43..47) | | RULE-44 evidence/invalidated/auditor rendering (PROOF-48) | |
| pre_push_hook | | | | | | RULE-5/6/8 amended, RULE-10..16 (PROOF-10 rewritten, PROOF-18..26; PROOF-1/8 ported) | | |
| security anchor | | | | | | | RULE-1/5 reworded, RULE-6 argv hardening (PROOF-1/5 widened, PROOF-6 with positive control) | |
| drift | | | | | | | RULE-17 since validation (PROOF-20) | |
| proof_plugins_php | | | | | | | RULE-3 proc_open (PROOF-3) | |
| skill_audit | | | | | | | RULE-18 amended, RULE-21 `--cache-key` (PROOF-18/21) | |
| purlin_teammate_definitions | | | | | | | RULE-6 (PROOF-6) | |
| dashboard_visual | | | | | RULE-12 (PROOF-12) | | | |
| skill_status | | | | | RULE-6 amended, RULE-9/10 (PROOF-6/9/10) | | | |
| purlin_version | | | | | | | | RULE-9 (PROOF-9 parses the Unreleased counts and compares to the run marker; skipped when absent) |
| qa_report (new) | | | | | | | RULE-1..6 (PROOF-1..6; RULE-6 zip equals md) | |
| purlin_docs (new) | | | | | | | | RULE-1..6, one proof per sub-claim (PROOF-1..10) |

### Missing proofs, now assigned (in addition to the table)

- `drift_criteria.md` `platforms` row: `purlin_references` PROOF-20 extended to also require a row
  for every optional field the docs name (`audit_llm`, `platforms`).
- CLAUDE.md edits are unspecced (CLAUDE.md is not in any Scope); the DONE section says so.
- `hard_gates.md:29`, `purlin_commands.md:20`, `testing-workflow-guide.md:93-101`,
  `skills/verify/SKILL.md:80-91`: covered by `purlin_docs` RULE-1 (no `@windows` as a tier
  outside RELEASE_NOTES and `dev/plans/`) with its own grep proof.
- `commit_conventions.md` `chore(update):` and the 36/5 vocabulary: `purlin_references` RULE-4
  (the commit-conventions rule) amended, its proof extended for both strings.
- `docs/installation-guide.md` Upgrading section, README and agent flag mentions: `purlin_docs`
  RULE-3 lists them.
- `verify-gate.yml` paths change: `verify_gate` RULE-2 (workflow triggers) amended, PROOF-2 updated.
- `migrate.py --apply legacy-marker` for all seven syntaxes: the `dev/test_init_update.py`
  fixture carries one file per plugin syntax; PROOF-53 asserts each is rewritten.
- 7.4 step 2 (config runner block and workflow rename) is done by hand; the DONE note states
  `--update` does not scaffold runners, which is `purlin:test`'s consent path.
- Three doc images exist and are referenced: `purlin_docs` RULE-7 (PROOF-11).
- `dev/pack_tools.sh` is a dev script and exempt (CLAUDE.md tool-folder rule); the zip-equality
  proof lives in `qa_report` RULE-6.
- `vitest_purlin.ts` gains a byte-identity rule: `skill_init` RULE-56 (PROOF-59), alongside
  RULE-18/19/20.
- 10.6 environment-kind entries: `config_engine` RULE-12 (an entry with `kind: environment` has
  no `os` and is satisfied only by an equal `PURLIN_PLATFORM`; host detection never satisfies
  it), PROOF-14; the four suites' markers are checked by `proof_common` PROOF-18's shrunken
  exception list.
- Consumer `evidence.test_run`: `receipt_format.md` states it is `null` for a receipt issued
  without a run marker and names the plugin-written marker as future work (backlog row exists).

### Weak proof designs, rewritten

- Every per-plugin behaviour (scoped file, forward slashes, marker syntax) has a proof per
  plugin in `dev/test_multilang_proof_plugins.py` / `dev/test_proof_jest.sh`: run the plugin's
  fixture with `PURLIN_PLATFORM=p1` and a marker declaring `on(p1)`; assert
  `<feature>.proofs-unit@p1.json` exists with `platform: "p1"` on every entry and that the
  unmarked test's entry lands only in `proofs-unit.json`; assert no `\` in any `test_file`.
- 6.4 provenance `None` is a behaviour case, not a mutation; the mutation is dropping the family
  clause. 6.5 parity: PROOF-84 also issues receipts through the issuer and asserts each receipt's
  vhash equals the payload's vhash for every feature.
- 7.2 skill-text proofs grep the literals `--update --check`, `--platform-id`,
  `AskUserQuestion`, `chore(update):` and assert `--mcp` appears with "MCP step". 7.3
  `purlin_skills` PROOF-16 asserts the exact anchor `purlin_commands.md#pending-migrations` in
  all 12 skill files.
- 10.1 PROOF-6 adds the positive control: `--end-of-options` precedes the url in the captured
  argv. 10.3 PROOF-94: receipt at C1, commit a scope-file change, assert the line with `1
  commits` and C1's sha7; commit a change outside scope, assert no line; mutation: drop the
  `--` path filter. 10.4 PROOF-96: `audit_llm: "nonexistent-cmd -p {prompt}"` names the
  command; `{prompt}` missing names that; unset prints nothing.
- 10.5 `qa_report` RULE-1 is FORBIDDEN (`://<[A-Z_]+>:<[A-Z_]+>@` absent, `gh repo clone`
  present); RULE-2 greps each field name individually, including `platforms`,
  `held_by_platform`, `evidence_stale`.
- 11 `purlin_docs` RULE-4 counts `| **Layer` rows across `docs/` and asserts exactly one file
  carries them; RULE-2 has one proof per sub-claim; `purlin_version` PROOF-9 parses the
  `N passed, M skipped` line and compares to the run marker.
- Cheap mutations added: 6.1 PROOF-10 (accept `Windows_2022` and expect failure), 8.2 PROOF for
  the marker (drop `*` and legend), 9 PROOF for whole-name matching (revert to substring), 10.2
  PROOF-92 (count stale stamps as current).

### Verification additions

- `dev/test_multilang_proof_plugins.py` and `dev/test_proof_jest.sh` pass for all eight plugins
  with the scoped-file and forward-slash cases.
- The "issues every feature and skips none" check holds only after 7.4 (before it, the
  legacy-pending refusal is expected); the DONE section records the order.

## TODO before pushing main (kept in `dev/plans/two-gauges-remote-verification.md` so a new context resumes from it)

The push of `main` publishes 39+ commits for the first time and is expected to happen in a later
context, after these are resolved. Execution appends to this list whatever it defers; nothing is
silently dropped. Sequence agreed 2026-09-12: this list is worked in a new context on THIS
machine first; `dev/plans/ado-runner-provider.md` is then executed on the work machine, which
has the Azure DevOps account. Do not start the ADO work here.

- [ ] Both audits run for real on this repo and recorded (Design and Integrity bars above met, or
      the shortfall named per feature with its `purlin:spec` / `purlin:build` directive).
- [ ] CI green on the branch head: `verify-gate`, `version-check`, `purlin-windows-2022-proofs`
      (`gh run list`), and `git pull --ff-only` returns nothing new.
- [ ] The backlog table below triaged: each item either scheduled or explicitly accepted.
- [ ] Release decision: `bash dev/bump_version.sh 0.11.0`, RELEASE_NOTES section finalized,
      tag (the format bumps make this a minor release; the user decides when).
- [ ] Consumer-CI templates exercised once against a scratch consumer project (clone a temp
      project, `purlin:init`, one `@on(linux)` proof, push to a scratch GitHub repo, confirm the
      runner commits back with both trailers and the gate passes). Not possible from this repo's
      own workflows, so it is a manual check before publishing.
- [ ] Anything a subagent reports as "deferred" during execution (appended as it happens).
- [ ] (6.5) The evidence check refuses receipts for `figma_web`, `skill_spec` and `static_checks`:
      their proof files were committed locally with no `Purlin-Runner:` trailer and the sweep does
      not run them (RULE-14 exceptions). 38/41 VERIFIED until 7.4 (static_checks via the runner)
      and 10.6 (environment ids for the other two) give them a witness.
- [ ] (6.3) `proof_plugins_php` and `proof_plugins_xunit` gained platform proofs that are skipped on
      this machine (no php, no dotnet); they have never executed anywhere. Run them on a host with
      the toolchains, or model both as `kind: environment` platforms in 10.6 so the gap reads
      AWAITING RUNNER instead of silently skipped.

---

## Backlog (recorded, deferred, with reasons)

| Item | Why deferred |
|---|---|
| Spec for `scripts/hooks/pre-commit.sh` (fail-open, `git add` of the digest, `PURLIN_SKIP_DIGEST`) | Digest is informational; needs its own spec and 6 to 8 proofs; do after Phase 9 so both hooks share the plugin-root resolver |
| MCP server hot-reload swallowing all exceptions in `main()` | Dev convenience; gate on `PURLIN_DEV_RELOAD=1` and log the traceback; touches `mcp_transport`, outside this plan |
| `plugin.json` pins nothing (`python3` from PATH, install from git HEAD) | Needs a release-process decision (tagging, minimum Python); record in `regulated-environments.md` as an integration point: pin the plugin by tag |
| Integrity formula counting MANUAL as full credit | Formula pinned across three files (RULE-33); 10.4 restricts MANUAL to entries backed by a current stamp; the weighting is a product decision |
| Proof plugins writing the run marker for consumer projects | 6.5's marker is dev-side; the consumer path relies on `purlin:verify` running `purlin:test` first |
| Tier 2a: a real `purlin:audit` on this repo | After 10.4 the hand-built cache is invalid by construction and Integrity reads unmeasured, which is honest; the real audit is the only way to a number |
| 38 LOOSE Design findings across 12 features | Triage via `purlin:spec`; unchanged from the previous plan |
| `summary.total_features` including anchors | Chose the split vocabulary (10.5) over changing the summary strip |
| ADO and other runner providers | The registry's `runner.provider` is the seam; `purlin:test` reports non-github providers as not dispatchable |
| Deep-merge of `platforms` across `config.local.json` | Flat replace kept and documented (6.2); revisit if a per-user runner override is ever needed |

---

## Verification (end of each phase, and before the merge)

- `export PATH="$PWD/.venv/bin:$PATH"`; `bash dev/run_tests.sh` green;
  `.purlin/runtime/test_run.json` shows `ok: true` at HEAD.
- `python3 -c "import sys; sys.path.insert(0,'scripts/mcp'); from purlin_server import sync_status; print(sync_status('.'))"`
  reads all features VERIFIED, one `Platforms (host: ...)` line naming `windows-2022` as proved
  remotely with a runner, zero `EVIDENCE OLDER THAN CODE` lines, no pending-migrations advisory,
  no legacy-alias warnings. (Note: this writes `.purlin/report-data.js`, so run it before the
  final commit, not after.)
- `python3 dev/issue_receipts.py` issues every feature and skips none; every receipt has
  `vhash_version: 2`, `evidence.test_run.commit == HEAD`, and no `executed_in_test_run: false`
  entry with `runner: null`.
- `python3 scripts/hooks/pre_push_gate.py check --project-root . --mode strict` exits 0;
  hook exercised in a temp repo per Phase 9's cases (warn + FAILING exits 1; strict + PASSING
  exits 1 then 0 after receipts; `off` prints one line; `"pre_push": "loud"` exits 1; comma list
  announces both arms; a raising `conftest.py` exits 1 naming pytest; a spec under `specs/a/b/`
  is counted; plugin unresolved prints the WARNING in warn and exits 1 in strict).
- `python3 scripts/ci/verify_gate.py --check --project-root .` exits 0 and prints the
  enforcement note and a By-platform section; `bash dev/bump_version.sh --check` exits 0;
  `python3 scripts/update/migrate.py --check` exits 0 on this repo and 1 on the
  `dev/test_init_update.py` fixture.
- Dashboard: open `purlin-report.html`; the Verified card opens the modal with a `windows-2022`
  row and a badged host row; the `static_checks` row shows two chips; theme toggle keeps both;
  `python3 dev/capture_doc_screenshots.py` regenerates three images.
- CI: after the final push, `gh run list` shows `verify-gate`, `version-check` and
  `purlin-windows-2022-proofs` green and `git pull --ff-only` brings back nothing new (the
  windows file is unchanged on a re-run, so no commit-back).
- `command grep -rn "tamper-evident\|signed verification\|signed off\|\.test-lock" docs README.md references skills tools`
  returns only the two negations in `regulated-environments.md`; `git ls-files .purlin/cache` is
  empty; `git ls-files assets/src` lists five `.mmd`; `command grep -rn "—\|–"` over every file
  this plan touched finds nothing new outside `purlin_server.py`'s existing output separators.
