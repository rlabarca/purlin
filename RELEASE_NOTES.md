# Release Notes

## v0.9.4 — Plugin-bundled MCP server & e2e proof quality

### Fixed

- **MCP server no longer version-pinned in consumer projects.** `purlin:init` wrote a project-level `.mcp.json` entry with an absolute path into the versioned plugin cache (`~/.claude/plugins/cache/purlin/purlin/<version>/scripts/mcp/purlin_server.py`). Project-scope `.mcp.json` takes precedence over plugin-provided servers and old cache directories stick around, so every plugin update silently stranded the project on the previous release's server — fresh data, stale code, no error (this is exactly how a 0.9.3 project kept rendering dashboards with 0.9.1 logic). The server is now bundled with the plugin itself: `.claude-plugin/plugin.json` declares it under `mcpServers` with `${CLAUDE_PLUGIN_ROOT}`, which Claude Code resolves to the installed plugin path on every launch, so the server always tracks the installed version (`skill_init` RULE-38/39). Init no longer writes a `purlin` entry into the project's `.mcp.json`; it removes the legacy entry while preserving any other MCP servers in the file (`skill_init` RULE-40).

  **Upgrading an existing project:** after updating the plugin, run `purlin:init --mcp` once (new flag — runs only the migration step) to remove the stale entry, then `/reload-plugins` (or restart the session).

- **`sync_status` flags the legacy entry automatically.** When the project's `.mcp.json` defines a `purlin` server pinned to a plugin-cache path, every status report opens with an advisory naming the pinned path and a `→ Run: purlin:init --mcp` directive — so pre-0.9.4 projects surface the migration on their first status call instead of relying on release notes (`sync_status` RULE-38). Dev checkouts (purlin entries pointing outside the plugin cache) are exempt.

### Added

- **E2E proofs must be observable flows.** Reverse-engineering UI-heavy codebases with `purlin:spec-from-code` produced implementation-coupled proofs tagged `@e2e` ("Assert `config.ts` AES-decrypts...", "Assert `loginRedirect` uses scope X") — satisfiable without launching the app, steering builders into unit-style tests that audit WEAK/HOLLOW. The quality guide now has a canonical **"E2E proof descriptions (observable flows)"** section (`references/spec_quality_guide.md`): `@e2e` proofs read as arrange → act → observe through the real running app, never name source files or internal functions, observe data contracts at the boundary they cross (outbound request, rendered output, storage state after a real flow), and stay tool-agnostic — executable by Playwright, Cypress, an MCP-driven browser, or screenshot + vision (`purlin_references` RULE-13).
- **E2E Proof Tier Integrity audit criteria.** `references/audit_criteria.md` (Criteria-Version 16) adds two Pass 2 WEAK criteria at HIGH priority applying to ALL `@e2e` proofs, not just design anchors: **tier mismatch** (test tagged `@e2e` never drives a browser/renderer/full stack — or the converse, a render/flow test with no tier tag) and **source-constant assertion** (asserting a config constant where the rule describes runtime behavior) (`purlin_references` RULE-14). The version bump does not invalidate audit caches — the cache key excludes the criteria version.
- **E2E runner reality check in `purlin:spec-from-code`.** Phase 1 records an `e2e_capable` flag; when a category's generated proofs include `@e2e` and no e2e runner is detected, the skill warns in the category review block and the Phase 4 summary instead of silently emitting unrunnable proofs (`skill_spec_from_code` RULE-32). `references/supported_frameworks.md` gains an **"End-to-end (browser) proofs"** section documenting interim proof emission through the existing Vitest/Jest markers or shell `purlin_proof` wrappers (`purlin_references` RULE-15).

### Changed

- **`purlin:spec-from-code` enforces proof quality at generation time.** The step 7 tier review now runs an inverse check — every `@e2e` description must match its tag or be rewritten/retagged (`skill_spec_from_code` RULE-30) — and step 11 validation rejects proof descriptions naming source files or internal symbols (`skill_spec_from_code` RULE-31). `purlin:spec` applies the same observable-flow check in Validate-Before-Commit (`skill_spec` RULE-8).

### Testing

- New proofs: `skill_spec_from_code` PROOF-42..45, `skill_spec` PROOF-9, `purlin_references` PROOF-13/14/15 (grep guards over the skill and reference text). Independent audit of the new proofs: 0 WEAK/HOLLOW (all structural documentation guards, excluded from integrity scoring); 3 advisory regex-precision findings applied before commit. Full suite 372 passed, 40/40 features VERIFIED.
- `skill_init` PROOF-40/41 now parse `.claude-plugin/plugin.json` directly (asserting `mcpServers.purlin` uses `python3` with `${CLAUDE_PLUGIN_ROOT}` args) and PROOF-42 verifies the legacy `.mcp.json` migration instructions, replacing the old greps for project-level `.mcp.json` creation.

## v0.9.3 — Dashboard visibility before tests exist

Quality-of-life release fixing the "empty dashboard" experience after `purlin:spec-from-code`: a freshly specced project now shows its full rule set and coverage plan in `purlin-report.html` before a single test has run.

### Added

- **Planned proofs in the dashboard.** The report data (`.purlin/report-data.js`) now includes the `PROOF-N` entries declared in each spec's `## Proof` section that have no executed result yet — status `"planned"`, tier parsed from the proof's `@tag` (default unit), empty test location (`report_data` RULE-8). The dashboard renders them greyed with a "not run" tag in the Proof column instead of a bare dash (`purlin_report` RULE-33), so the intended coverage plan is visible immediately after spec generation. Planned proofs are display-only: proved/total counts, vhash, rule status, and feature status are computed from executed proofs exactly as before (`report_data` RULE-22). Proof results are still written only when tests run (`purlin:unit-test` / `purlin:build` / `purlin:verify`).

### Changed

- **Category sections are expanded by default.** Previously every category started collapsed, so a project with many small categories looked like it had no specs at all. Categories now render expanded; collapsing one is remembered per browser via localStorage (`purlin_report` RULE-20, persistence unchanged per RULE-21).
- **`purlin:spec-from-code` no longer creates single-spec folders.** A new Phase 2 taxonomy step merges single-feature categories into the closest related category, or — when nothing fits — places the spec directly at `specs/<name>.md` with no folder (`skill_spec_from_code` RULE-29). Uncategorized specs display under "other" in the dashboard.
- **Docs and skill wording aligned with actual behavior.** PASSING criteria say "all rules" (matching `_determine_status`); verify receipt format documented as `features=N/T`; installation/testing/lifecycle guides corrected (committed digest, real GitHub Actions example, shell plugin path); spec-from-code guide documents the post-generation build lifecycle; lifecycle PM diagram regenerated.

### Testing

- New proofs: planned-proof emission and dedup against executed results including required/global anchor rules (`report_data` PROOF-22), coverage isolation (PROOF-23), greyed "not run" rendering with no audit tag (`purlin_report` PROOF-33, Playwright), and the single-spec folder ban (`skill_spec_from_code` PROOF-41). Dashboard PROOF-19/20/21 updated for the expanded-by-default behavior. Independent audit of the changed proofs: 5 STRONG, 0 WEAK/HOLLOW.

## v0.9.2 — .NET test support (xUnit)

Incremental release adding .NET to the supported test ecosystems, backed by a refactor of the proof-plugin specs.

### Added

- **xUnit/.NET proof plugin.** `scripts/proof/xunit_purlin.cs` is a custom `dotnet test` logger (`ITestLoggerWithParameters`, FriendlyName `purlin`) that collects proof traits in-process — no `.trx` post-parsing — and emits feature-scoped proof JSON per the shared proof-plugin contract. Mark tests with a trait:

  ```csharp
  [Fact]
  [Trait("PurlinProof", "feature_name:PROOF-1:RULE-1:unit")]
  public void ValidLogin() { ... }
  ```

  Because the marker is a test trait rather than a parsed title string, NUnit `[Category]`/`[Property]` and MSTest `[TestProperty]` surface the same way — the logger covers C#, F#, and VB.NET test projects. Run with `dotnet test --logger purlin -- RunConfiguration.CollectSourceInformation=true`. Setup is manual for now (the .NET test platform only discovers loggers from assemblies named `*TestLogger.dll`) — see `references/formats/proofs_format.md` for wiring steps. Proven by an integration suite that drives a real `dotnet test --logger purlin` run; independent audit: 6/6 STRONG.

- **`purlin:init` presents every shipped framework.** The framework selection list now covers all shipped plugins — pytest, Jest, Vitest, C, PHP, SQL, Shell, and xUnit (plus "other") — instead of only the auto-detected subset (`skill_init` RULE-48). Frameworks that need manual wiring (xUnit) print their setup steps after the plugin file is copied.

### Changed

- **Proof-plugin specs split per framework.** The monolithic `proof_plugins` spec is gone, replaced by one spec per plugin (`proof_plugins_pytest`, `_jest`, `_vitest`, `_shell`, `_c`, `_php`, `_sql`, `_xunit`) plus a `proof_common` anchor that holds the shared contract: feature-scoped overwrite, tier file naming, marker→JSON field mapping. Proof markers were re-homed to their per-plugin specs.
- `references/supported_frameworks.md` is now Format-Version 5: adds an **Additional Plugins (manual setup)** section for shipped-but-not-auto-scaffolded plugins (currently xUnit).

### Testing

- New integration proofs drive the compiled xUnit logger through a real `dotnet test` run (`dev/test_multilang_proof_plugins.py::TestXUnitProofPlugin`).
- Strengthened existing proofs: C plugin proofs regenerated from a real `gcc` run, Vitest RULE-1 marker parse now asserted inline, pytest "call phase only" boundary proved, and three audit-pipeline proofs recorded from a full-suite run.

## v0.9.1 — Vitest reporter & JS/TS audit fixes

Bug-fix release addressing two reported issues in JavaScript/TypeScript proof handling.

### Fixed

- **Vitest reporter silently emitted zero proofs on Vitest 2.x+ (#1).** `scripts/proof/vitest_purlin.ts` collected proofs in `onTaskUpdate`, whose pack shape changed in Vitest 2 (`[id, result, meta]`, where `result` lacks `name`/`file`), so the marker regex never matched and tests passed with no `.proofs-*.json` written. The reporter now collects in `onFinished(files)` via a recursive file→suite→test walk — the hook whose shape is stable across Vitest 2.x–4.x — mapping `result.state` to pass/fail, skipping unrun tasks, and resolving `test_file` from the file task's `filepath`.
- **All Vitest projects now scaffold the native `vitest_purlin.ts`.** Vitest never calls Jest's `onTestResult`/`onRunComplete` hooks, so the previous "Vitest → `jest_purlin.js`" mapping was also silently broken. Vitest loads `.ts` reporters natively via Vite, so one reporter covers both JS and TS projects.
- **`check_js` audit regex misfired on common Vitest patterns (#2).** `scripts/audit/static_checks.py::check_js()` used a lazy `(.*?)\}\s*\)` body matcher that truncated at the first inner `}` (options objects, destructured params, type assertions) and a `[^"']*` title class that dropped titles containing apostrophes. Replaced with a stdlib brace-balancing tokenizer that tracks string/template/regex literals and comments.
- **Claude plugin manifest version lagged the release.** `.claude-plugin/plugin.json` — the version consumers install against via the plugin marketplace — was left at `0.9.0`. It now reads `0.9.1`, and a new guard (`purlin_version` RULE-5 / PROOF-5) asserts the manifest version stays in lockstep with the `VERSION` file, joining the existing `templates/config.json` check so this can't silently recur.

### Testing

- PROOF-29 was strengthened to actually drive the compiled reporter via a synthetic Vitest 2.x+ task tree (the old proof only ran `tsc` + `node` on hand-built JSON and never invoked the reporter). New regression proofs cover the exact issue #2 repro.
- Docs aligned: `references/supported_frameworks.md` (Format-Version 3), `references/formats/proofs_format.md`, and `docs/testing-workflow-guide.md` now describe the native Vitest reporter and tested version range.

## v0.9.0 — Rule-Proof Runtime

Complete redesign. Purlin v0.9.0 replaces the v1 system (35 skills, 5 agents, 8 hooks, 8 MCP tools) with a minimal rule-proof runtime.

### What Changed

**Specs replace features.** The `features/` directory and its companion files (`.impl.md`, scenarios, Given/When/Then) are gone. Specs live in `specs/<category>/<name>.md` using a 3-section format: `## What it does`, `## Rules`, `## Proof`. Rules are numbered (`RULE-N`), proofs map to rules (`PROOF-N (RULE-N)`).

**Proofs replace tests.json.** Test runners emit `*.proofs-*.json` files next to specs. Proof markers in tests: `@pytest.mark.proof("feature", "PROOF-1", "RULE-1")` for pytest, `[proof:feature:PROOF-1:RULE-1:tier]` in Jest test titles, `purlin_proof()` for shell.

**`sync_status` replaces `purlin_scan`.** One MCP tool reads specs and proof files, diffs them, reports coverage with `→` directives that tell the agent exactly what to do.

**Verification is new.** `purlin:verify` runs all tests, issues receipts for features with 100% rule coverage. `vhash = sha256(sorted RULE IDs + sorted proof IDs/statuses)`.

**12 skills** (down from 35). All optional — no skill invocation required to write any file.

**2 hard gates** (down from 8). Invariant write protection + proof coverage for receipts.

**2 MCP tools:** `sync_status`, `purlin_config`.

**2 hooks:** `PreToolUse` gate for invariants, `SessionStart` for cleanup.

**1 agent** (down from 5). No modes, no role-based permissions.

### Key Differences from v1

| v1 | v0.9.0 |
|----|--------|
| `features/<category>/<name>.md` | `specs/<category>/<name>.md` |
| Scenarios (Given/When/Then) | Rules (RULE-N) + Proofs (PROOF-N) |
| `tests/<feature>/tests.json` | `specs/<category>/<feature>.proofs-<tier>.json` |
| 3 modes (PM, Engineer, QA) | 1 agent, no modes |
| `purlin_scan` + `purlin_status` | `sync_status` |
| Role-based permissions | No permissions (skills are optional) |
| 35 skills | 12 skills |
| Write guard with file classifications | Gate hook for invariants only |

### New in v0.9.0

- **Invariants with external sources:** `> Source:` + `> Pinned:` metadata. Git-sourced and Figma-sourced. Auto-sync with `purlin:invariant sync`.
- **Manual proof stamps:** `@manual(email, date, commit_sha)` in spec's `## Proof` section. Staleness detection via `> Scope:` file tracking.
- **Verification receipts:** `*.receipt.json` files with `vhash` and commit SHA. `--audit` mode for CI.
- **Feature-scoped proof overwrite:** Each test run replaces only its feature's entries in the proof file, preserving others.

### Tier Rename (0.9.0)

- `default` → `unit` (isolated logic, controlled inputs)
- `slow` → `integration` (real dependencies — DB, APIs, filesystem)
- `e2e` and `manual` unchanged
- Rename your proof files: `*.proofs-default.json` → `*.proofs-unit.json`
- Update pytest markers: `@pytest.mark.slow` → `@pytest.mark.integration`
- Update jest markers: tier segment in `[proof:...]` tag
- Update shell env var: `PURLIN_PROOF_TIER=slow` → `PURLIN_PROOF_TIER=integration`

### MCP Server Spec Split (0.9.0)

- `specs/mcp/mcp_server.md` (34 rules) split into 4 focused specs:
  - `mcp_transport.md` (7 rules) — JSON-RPC transport
  - `sync_status.md` (15 rules) — rule coverage reporting
  - `drift.md` (11 rules) — structured change summary
  - `purlin_config.md` (1 rule) — config read/write
- Tool names: `sync_status`, `purlin_config`, `drift`

### Teammate Spawning Now Invisible (0.9.0)

- "team up" / "create a purlin team" removed as user-facing concept
- Teammates are automatically spawned by verify and audit
- Auditor, builder, reviewer still exist as agents — just no longer user-managed

### Migration

Keep your old `features/` directory — `purlin:spec-from-code` detects it and migrates your existing specs to the new 3-section format. Old scenarios and rules are used as primary input for generating new-format specs, so you don't lose the work you've already done. Remove only the non-spec artifacts (`rm -rf .purlin/ pl-* *.sh`), then run `purlin:init` followed by `purlin:spec-from-code`.
