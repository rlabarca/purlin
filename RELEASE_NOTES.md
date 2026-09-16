# Release Notes

## Unreleased — 0.10.0

For a project running 0.9.5. One command moves it forward, and the rest of this page says what
that command changes.

0.10.0 replaces two grading scores and one ladder of seven states with a spec status and three
evidence levels, moves the evidence into the repository, and gives each level one command.
Nothing in it needs a new service or a hosted anything: the evidence is files in git, and the
enforcement is a CI job and a branch rule.

Tests at this commit: 1093 passed, 6 skipped.

### What a 0.9.5 user does

```
purlin:init --update
```

The update reads what the project actually contains rather than its `version` field, shows the
delta, and asks before each write. It untracks and deletes the evidence files and the proof
files that used to be committed, untracks the committed dashboard data, rewrites the hooks,
retires the config keys that no longer exist, asks the gate question once, and rewrites an
operating-system tag to `@env(...)` where the intended system is unambiguous. Every file it
replaces is backed up beside the original. `purlin:init --update --check` prints the pending
list and writes nothing, which is what a preflight in CI runs. Until the update runs, every
skill opens with `→ Run: purlin:init --update`.

The evidence a person wrote under 0.9.5 does not carry forward. Those files bound hashes this
release computes differently, so the update drops them rather than converting them into
something nobody attested to; they stay in git history, and `purlin:sign` walks the list
afterwards.

### What changed, by concept

**The spec status and the three levels.** A rule has a spec status and up to three cells, each
of which reads one word and carries its reasons. The spec status is `drafted` when no proof line
names the rule, `ready` when one does and no blocking free check fires on the proof text. Then:

| Level | The question | Words the cell can read |
|-------|--------------|-------------------------|
| passed | did every tagged test for this rule pass? | `passed`, `failed`, `no test`, `not run`, `code changed` |
| strong | are those tests worth trusting? | `strong`, `weak`, `needs a person` |
| signed | did a person say the rule, the proof and the test belong together? | `signed`, `unsigned`, `stale`, `held`, `not required` |

A cell exists only at or below the project's gate. Above the gate it is absent, not empty, which
is why raising the gate is what makes a column, a tile or a filter appear.

**The gate.** One project setting, `gate` in `.purlin/config.json`, with three values named for
the word the last cell reads when it is met: `passed`, `strong` and `signed`. `purlin:init` asks
one question and derives the rest: `min_strength` unused, 70 and 80; `ai_review_at` never, high
and medium; `sign_at` absent, absent and `medium`; the breaks off under `passed` and on above
it. `purlin:init --gate <value>` changes it later; raising adds what is missing, lowering
deletes nothing. A gate is three things and needs all three: a CI job, a branch rule that blocks
a merge without it, and the setting saying what passing means.

**Three commands, one per level.** `purlin:test` runs the tagged tests and prints each rule's
passed cell. `purlin:audit` runs the tests and the breaks, then the free checks and the model
review where the risk asks, and writes the record; on CI it writes the briefs too. `purlin:sign`
walks the review list one brief at a time when given no rule, and signs, holds or notes a rule
when given one. `purlin:verify`, `purlin:review` and `purlin:approve` are gone, not aliased, and
the skill count falls from 13 to 12.

**Level 2 is fully automatic.** Nobody is asked to do anything to reach `strong`. A person first
appears at level 3.

**Records.** Evidence lives in the tree, as
`.purlin/records/<feature>/<timestamp>-<commit7>-<runner>[-<os>].json`, one file per audit run,
committed. Adding a file never conflicts, so two branches never fight over it. The last commit
touching a record decides its `source`: `ci` when it was written through the git host's API by
the CI identity, `developer` when a person committed it, `local` when it is uncommitted. Under
`passed` every source counts; under `strong` and `signed` only `ci` does, and a record that does
not count leaves the passed cell reading `not run` with the reason naming the source and the
gate. The audit keeps the newest three records per feature per operating system and prunes the
rest; a record named in the message of an annotated `record/<name>` tag is kept for ever.

**Briefs.** One file per rule per set of hashes,
`.purlin/briefs/<feature>/<RULE-N>.<hash8>.brief.json`, written by CI and committed beside the
records. A brief reports four things: the test strength beside the minimum, the free-check
findings on the proof text, the free-check findings on the test body, and what the model review
observed together with whether it could settle the question. **It recommends nothing.** The four
verdict words are retired with it.

**Signatures and holds.** One file per signature,
`specs/<category>/<feature>.signatures/<RULE-N>.<hash8>.<signer-slug>.json`, so two signatures
never conflict either. It binds the hashes of the rule text, the proof text and the test body,
plus the rule's risk, so a risk re-tag stales it like any other change. The people who may sign
are `signers` in `.purlin/config.json`, changed by pull request, so git history records who
could sign and when. A hold is a person's committed statement that the test does not prove the
proof, with the missing case named; while it is current the strong cell reads `needs a person`
and the signed cell reads `held`. A `--note` is the one line a signer writes for a `@manual`
proof or a review the model could not settle.

**CI writes no signature file, ever.** The auto-approval of low-risk rules is gone with the
`.ci.json` file it wrote. A signature directory holds only files a person wrote; CI's one commit,
`purlin: record for <commit7>`, carries the records and the briefs and nothing else. The CI-only
branch ruleset now covers `.purlin/records/**` and `.purlin/briefs/**`.

**The review list** holds only what needs a person: a strong cell reading `needs a person`, or a
signed cell reading `unsigned`, `stale` or `held`. A weak rule is build work and stays on the
board.

**The gate check.** `scripts/ci/verify_gate.py` becomes `scripts/ci/gate_check.py`, its log
prefix `gate:`, its sections `Not passed (n)`, `Weak (n)` and `Not signed (n)`, and its JSON key
`result` in place of `verdict`.

**Breaks engines.** `purlin:audit` breaks the code on purpose at `strong` and above and reports
the share of those breaks the tests caught as the **test strength**, an integer percent. Three
engines ship, chosen by `mutation_engine` in the config: mutmut for Python, Stryker for
JavaScript and TypeScript, and Stryker.NET for C#. SQL and Bash have no engine, so their
strength reads `n/a` and the strong cell rests on the free checks.

**`@env`.** A proof that can only be proved on one operating system carries `@env(windows)`,
`@env(macos)` or `@env(linux)`. Those three are the whole vocabulary. `purlin:init` reads the
tags in `specs/` and writes a CI matrix to match, one job per system named, each running the
same audit and writing its own record. A proof with no tag is satisfied by a record from any
system. On a host that does not match, the test is skipped and the passed cell reads `not run`
with `<os>: no record yet`; `purlin:audit --remote` pushes the branch, waits for the workflow
and pulls the records CI wrote.

**The dashboard.** One HTML page on the design tokens, with no framework and no build step. Its
tiles, columns and filters scale with the gate: three tiles and five columns at `passed`, a
`Strong` tile and two more columns at `strong`, a `Signed` tile, a `Stale` flag card and one
more column at `signed`. It opens from disk and is published by CI as the `purlin-dashboard`
build artifact, linked from the pull request comment.
`scripts/report/scan.py --repo <url>` prints the same rollup for anyone holding only a URL.

**The tools.** `tools/PM/` and `tools/QA/` are Claude Desktop skills for people with no
checkout. The PM tool drafts and edits specs and anchors and opens the pull request; the QA tool
produces the triage report and opens pull requests with proof edits.

**Formats.** spec 11, proofs 8 and anchor 7 change wording only. The record format goes to 2 for
the gate enum, the null strength under `passed` and the source. `approval_format.md` becomes
`signature_format.md` at version 3. The payload schema goes from 4 to 5, and
`references/drift_criteria.md` from criteria version 3 to 4. A tool that parses any of them
should read the version line.

### The words that were retired

Every one of these is gone from the code, the skills, the references, the docs and every line of
output, in any casing:

| Retired | What says it now |
|---------|------------------|
| `tested`, the gate value | `passed` |
| `recorded`, the gate value | `strong` |
| `approved`, the gate value | `signed` |
| `approve`, `approval`, `approvals` | `sign`, `signature`, `signatures` |
| `approver`, `approvers` | `signer`, `signers` |
| `verified`, `verify` as a command name | the cell's own word; `purlin:audit` for the run |
| `verdict` | what the brief reports: strength, findings, observations, settled |
| `Reviewed`, the state | the strong cell's word |
| `re-verify pending` | the passed cell reading `code changed` |
| `Proof ready` | the spec status `ready` |
| `lowest state`, `seven states` | the spec status and the three cells |
| `auto-approval` | nothing: CI writes no signature file |
| `review queue` | `review list` |
| `purlin:verify`, `purlin:review`, `purlin:approve` | `purlin:audit`, `purlin:sign` |
| `verify_gate`, `verify-gate:` | `gate_check`, `gate:` |
| `validated/<name>` tags | `record/<name>` tags |

`audit` is un-retired and means one thing: the level 2 run. An audit proves a rule strong or
weak. The grading scores the earlier `purlin:audit` produced stay retired.
`references/glossary.md` lists each word and the spelling it replaced.

### What was removed

Gone in 0.10.0: the two LLM grading scores and the skill and agent that produced them; the
runner registry and its per-runner proof files, replaced by `@env` and the CI matrix; the
committed evidence files, replaced by records; the committed proof files, which are now runtime
state under `.purlin/runtime/` and are not committed at all; the committed dashboard data, now a
build artifact; the design-tool importer, the visual hash and the live design-tool connection,
replaced by exported files under `designs/` reviewed by pull request; and C and PHP support, so
a project that used either keeps its proofs only by writing a custom proof plugin. Several flags
went with them. A `@manual` proof stays: it has no test, its strong cell reads `needs a person`,
and its evidence is a signature carrying a one-line note.

### The 0.10.0 line that never shipped

An earlier 0.10.0 development line added two LLM grading scores, one for proof descriptions and
one for test bodies, together with a skill and an agent to produce them. A later one added a
seven-state ladder. Neither was released, and 0.10.0 as it ships has neither. What a person needs
before signing a rule is a brief: the free checks, the test strength from the newest record, and
a model review only where the risk warrants it. `references/review_criteria.md` holds those
criteria, and they are the only names a finding ever carries.

## 0.9.5 — Windows-scoped proof checks & C# support

### Fixed

- **`purlin:audit` now runs on Windows.** The audit toolchain shells out to `scripts/audit/static_checks.py`, which was unusable on Windows for three independent reasons, each fixed here (issue #3):
  - **`import fcntl` crashed the module on load.** `fcntl` is POSIX-only, so *every* subcommand (`--read-cache`, `--load-criteria`, `--check-proof-file`, Pass 1, `--write-cache`, `--prune-cache`) died with `ModuleNotFoundError` before doing any work. `fcntl` is now imported under `try/except ImportError` behind a `_HAS_FCNTL` flag, and the audit-cache lock goes through `_lock_exclusive`/`_unlock` helpers that use `fcntl.flock` on POSIX and `msvcrt.locking` on Windows — preserving the exclusive read→merge→write serialization that keeps concurrent subagent writers from clobbering each other (`static_checks` RULE-25/RULE-29).
  - **Text I/O assumed UTF-8.** ~16 `open()` calls omitted `encoding=`, so on a Windows cp1252/ASCII locale they raised `UnicodeDecodeError` reading the tool's own UTF-8 files (e.g. `references/audit_criteria.md`). Every text-mode `open()` now specifies `encoding='utf-8'` (`static_checks` RULE-30).
  - **`--load-criteria` printed non-ASCII to a non-UTF-8 console.** Even after the read fix, the criteria text (which contains `✓`/`⚠` glyphs) raised `UnicodeEncodeError` on an ASCII stdout. `static_checks.py` now reconfigures stdout/stderr to UTF-8 at startup (`static_checks` RULE-30).

### Added

- **Deterministic Pass-1 coverage for C#/.NET tests.** Pass 1 previously recognized only pytest/Jest/Shell markers, so xUnit/NUnit/MSTest tests carrying `[Trait("PurlinProof", "feature:PROOF-N:RULE-N:tier")]` produced zero proofs and the structural checker silently no-op'd on `.cs` files. The new `check_csharp` analyzer parses those trait markers, locates each `[Fact]`/`[Theory]` method body via a C#-aware brace/string scanner, and runs assert-true / no-assertion detection — recognizing xUnit `Assert.*`, NUnit `Assert.That`, MSTest `Assert.*`, FluentAssertions `.Should()`, and Playwright fluent assertions (`Expect(...)`/`Assertions.Expect(...)` chained to a `To*Async()` matcher) as assertions (`static_checks` RULE-31). A bare `Expect(x)` with no matcher chain is still flagged `no_assertions`. The dispatch was extracted into `analyze_test_file()` and now routes `.cs`. `references/supported_frameworks.md` documents the new coverage. To keep this broader structural acceptance from masking weak tests, the Pass-2 audit criteria gained a "presence/visibility-only assertion" WEAK check (`references/audit_criteria.md` → Criteria-Version 17).
- **Portable interpreter guidance in `purlin:audit`.** `skills/audit/SKILL.md` documents a `python3 → python → py -3` fallback for invoking `static_checks.py`, since stock Windows does not put `python3` on PATH (`skill_audit` RULE-15).
- **`purlin:audit` reaches C# tests even when `test_file` is empty.** Under `dotnet test`, `TestCase.CodeFilePath` is often null (no surfaced source info), so the xUnit logger emits proof entries with a blank `test_file` — which previously blocked the audit skill from locating the `.cs` code to scan (Pass 1) or read (Pass 2). `static_checks.py` now exposes `--resolve-source <test_name>`, which derives the declaring type from the fully-qualified `test_name` and locates its `.cs` file (skipping `bin`/`obj`), and `skills/audit/SKILL.md` uses it as a fallback (`static_checks` RULE-32, `skill_audit` RULE-16). Populating `test_file` natively still requires `RunConfiguration.CollectSourceInformation=true` with full PDBs — now documented.

### Testing

- New proofs: `static_checks` PROOF-44/45 (AST structural guards — no unconditional `fcntl` import; `encoding='utf-8'` on every text-mode `open()`), PROOF-46–49 (C# assert-true / no-assertion / multi-framework assertion recognition / `.cs` dispatch), PROOF-50 (Windows lock path driven through an injected fake `msvcrt`, `@integration`), PROOF-51 (full CLI pipeline via real subprocess, `@e2e`), PROOF-52 (the cp1252 failure reproduced by running `--load-criteria` under `PYTHONUTF8=0`/`LC_ALL=C`, `@e2e`); `skill_audit` PROOF-15. PROOF-55 covers the Playwright assertion recognition (and the bare-`Expect` negative). Windows behavior is now verified for real on a `windows-latest` GitHub Actions runner — `.github/workflows/windows-proofs.yml` runs PROOF-53 (native `msvcrt` lock path, `_HAS_FCNTL` genuinely False) and PROOF-54 (`--load-criteria` under the native console codec) in the dedicated `@windows` proof tier and commits the results back — in addition to the host simulation (fake `msvcrt`) and ASCII-locale subprocess repro. Independent audit of the new proofs: STRONG at 100% integrity, 0 WEAK/HOLLOW.

## 0.9.4 — Plugin-bundled MCP server & e2e proof quality

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

## 0.9.3 — Dashboard visibility before tests exist

Quality-of-life release fixing the "empty dashboard" experience after `purlin:spec-from-code`: a freshly specced project now shows its full rule set and coverage plan in `purlin-report.html` before a single test has run.

### Added

- **Planned proofs in the dashboard.** The report data (`.purlin/report-data.js`) now includes the `PROOF-N` entries declared in each spec's `## Proof` section that have no executed result yet — status `"planned"`, tier parsed from the proof's `@tag` (default unit), empty test location (`report_data` RULE-8). The dashboard renders them greyed with a "not run" tag in the Proof column instead of a bare dash (`purlin_report` RULE-33), so the intended coverage plan is visible immediately after spec generation. Planned proofs are display-only: proved/total counts, vhash, rule status, and feature status are computed from executed proofs exactly as before (`report_data` RULE-22). Proof results are still written only when tests run (`purlin:unit-test` / `purlin:build` / `purlin:verify`).

### Changed

- **Category sections are expanded by default.** Previously every category started collapsed, so a project with many small categories looked like it had no specs at all. Categories now render expanded; collapsing one is remembered per browser via localStorage (`purlin_report` RULE-20, persistence unchanged per RULE-21).
- **`purlin:spec-from-code` no longer creates single-spec folders.** A new Phase 2 taxonomy step merges single-feature categories into the closest related category, or — when nothing fits — places the spec directly at `specs/<name>.md` with no folder (`skill_spec_from_code` RULE-29). Uncategorized specs display under "other" in the dashboard.
- **Docs and skill wording aligned with actual behavior.** PASSING criteria say "all rules" (matching `_determine_status`); verify receipt format documented as `features=N/T`; installation/testing/lifecycle guides corrected (committed digest, real GitHub Actions example, shell plugin path); spec-from-code guide documents the post-generation build lifecycle; lifecycle PM diagram regenerated.

### Testing

- New proofs: planned-proof emission and dedup against executed results including required/global anchor rules (`report_data` PROOF-22), coverage isolation (PROOF-23), greyed "not run" rendering with no audit tag (`purlin_report` PROOF-33, Playwright), and the single-spec folder ban (`skill_spec_from_code` PROOF-41). Dashboard PROOF-19/20/21 updated for the expanded-by-default behavior. Independent audit of the changed proofs: 5 STRONG, 0 WEAK/HOLLOW.

## 0.9.2 — .NET test support (xUnit)

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

## 0.9.1 — Vitest reporter & JS/TS audit fixes

Bug-fix release addressing two reported issues in JavaScript/TypeScript proof handling.

### Fixed

- **Vitest reporter silently emitted zero proofs on Vitest 2.x+ (#1).** `scripts/proof/vitest_purlin.ts` collected proofs in `onTaskUpdate`, whose pack shape changed in Vitest 2 (`[id, result, meta]`, where `result` lacks `name`/`file`), so the marker regex never matched and tests passed with no `.proofs-*.json` written. The reporter now collects in `onFinished(files)` via a recursive file→suite→test walk — the hook whose shape is stable across Vitest 2.x–4.x — mapping `result.state` to pass/fail, skipping unrun tasks, and resolving `test_file` from the file task's `filepath`.
- **All Vitest projects now scaffold the native `vitest_purlin.ts`.** Vitest never calls Jest's `onTestResult`/`onRunComplete` hooks, so the previous "Vitest → `jest_purlin.js`" mapping was also silently broken. Vitest loads `.ts` reporters natively via Vite, so one reporter covers both JS and TS projects.
- **`check_js` audit regex misfired on common Vitest patterns (#2).** `scripts/audit/static_checks.py::check_js()` used a lazy `(.*?)\}\s*\)` body matcher that truncated at the first inner `}` (options objects, destructured params, type assertions) and a `[^"']*` title class that dropped titles containing apostrophes. Replaced with a stdlib brace-balancing tokenizer that tracks string/template/regex literals and comments.
- **Claude plugin manifest version lagged the release.** `.claude-plugin/plugin.json` — the version consumers install against via the plugin marketplace — was left at `0.9.0`. It now reads `0.9.1`, and a new guard (`purlin_version` RULE-5 / PROOF-5) asserts the manifest version stays in lockstep with the `VERSION` file, joining the existing `templates/config.json` check so this can't silently recur.

### Testing

- PROOF-29 was strengthened to actually drive the compiled reporter via a synthetic Vitest 2.x+ task tree (the old proof only ran `tsc` + `node` on hand-built JSON and never invoked the reporter). New regression proofs cover the exact issue #2 repro.
- Docs aligned: `references/supported_frameworks.md` (Format-Version 3), `references/formats/proofs_format.md`, and `docs/testing-workflow-guide.md` now describe the native Vitest reporter and tested version range.

## 0.9.0 — Rule-Proof Runtime

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
