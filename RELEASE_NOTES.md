# Release Notes

## Unreleased — 0.10.0

For a project running 0.9.5. One command moves it forward, and the rest of this page says what
that command changes.

0.10.0 replaces two grading scores and one ladder of seven states with a spec status and three
evidence levels, moves the evidence into the repository, and gives each level one command. The
whole loop runs on one machine, at every gate: nothing needs a new service, a hosted anything or
a setting on the git host. The evidence is files in git, and the marker that a version met the
gate is an annotated tag a person pushes.

### What a 0.9.5 user does

```
purlin:init --update
```

The update reads what the project actually contains rather than its `version` field, shows the
delta, and asks before each write. It untracks and deletes the evidence files and the proof
files that used to be committed, untracks the committed dashboard data, removes the git hooks an
older Purlin installed, retires the config keys that no longer exist, asks the gate question and
the trust question once each, and rewrites an operating-system tag to `@env(...)` where the
intended system is unambiguous. Every file it
replaces is backed up beside the original. `purlin:init --update --check` prints the pending
list and writes nothing, which is what a preflight runs. Until the update runs, every
skill opens with `→ Run: purlin:init --update`.

The evidence a person wrote under 0.9.5 does not carry forward. Those files bound hashes this
release computes differently, so the update drops them rather than converting them into
something nobody attested to; they stay in git history, and `purlin:sign` walks the list
afterwards.

### What changed, by concept

**The spec status and the three levels.** A rule has a spec status and up to three cells, each
of which reads one word and carries its reasons. The spec status is `drafted` when no proof
line names the rule and `ready` when one does, and nothing more. Then:

| Level | The question | Words the cell can read |
|-------|--------------|-------------------------|
| passed | did every tagged test for this rule pass? | `passed`, `partial`, `failed`, `no test`, `not run`, `code changed` |
| strong | are those tests worth trusting? | `strong`, `weak`, `not audited`, `unsettled`, `manual test`, `held` |
| signed | did a person say the rule, the proof and the test belong together? | `signed`, `unsigned`, `stale`, `held` |

A cell exists only at or below the project's gate. Above the gate it is absent, not empty, which
is why raising the gate is what makes a column, a tile or a filter appear.

**The gate.** One project setting, `gate` in `.purlin/config.json`, with three values named for
the word the last cell reads when it is met: `passed`, `strong` and `signed`. `purlin:init` asks
one question, **what must be true of every rule before a version is proven?**, and derives the
rest: `min_strength` unused, 70 and 80; the default bar `passed`, `strong` and `strong`;
`sign_at` absent, absent and `strong`; the breaks off under `passed` and on above it.
`purlin:init --gate <value>` changes it later; raising adds what is missing, lowering deletes
nothing.

**The whole loop runs on one machine.** `purlin:spec`, `purlin:build`, `purlin:test`,
`purlin:audit`, `purlin:sign`, `git push`. A project at `signed` on one laptop with no CI
anywhere is the ordinary case, at every gate. A record counts whoever wrote it.

**Three commands, one per level.** `purlin:test` runs the tagged tests, writes the test results
and commits them. `purlin:audit` runs the tests and the breaks, then the AI audit on every rule
whose bar is `strong`, and writes the record and the briefs. `purlin:sign` walks the Review list
and then the Sign list one brief at a time when given no rule, signs, holds or notes a rule when
given one, and closes by writing the tag. `purlin:verify`, `purlin:review` and `purlin:approve`
are gone, not aliased, and the skill count falls from 13 to 12.

**The tag is the marker.** When every rule meets the gate, `purlin:sign` writes the annotated tag
`signed/<version>` over the commit, taking the name from the `VERSION` file or from
`--release <name>`, and prints `Run: git push origin signed/<version>`. No tag is written while
any rule falls short, so the tag is the claim. A tag holds the whole tree, so the code, every
record, every brief and every signature are pinned together under one name. `purlin:audit --tag`
and the `record/<name>` tags are gone with it, and nothing else pins a record.

**A push is free.** Any branch, any time, and nothing runs when you make one. The pre-push hook
is removed and `purlin:init` installs no git hook; the rule that an agent never pushes is an
instruction in `agents/purlin.md`. No branch rule is printed and none is asked for.

**Trust.** `purlin:init` asks `Do you trust your own machine for the tests and the signing?
[y/n]` and writes `trust: local` or `trust: remote`. Under `local`, the default, this machine's
runs are the evidence from end to end. Under `remote`, `purlin:sign` refuses a rule whose tests
have no `ci` record for the current commit, so `purlin:test --remote` runs first.

**A remote runner exists for two reasons and no other**: a proof is tagged `@env` for an
operating system this machine is not, or trust is `remote`. With neither, `purlin:init` writes
no workflow at any gate. Where one exists, it starts on a push of a `signed/**` tag and on a
push to a `run/*` branch, and on nothing else: no pull request run, no run on a branch, no
comment and no dashboard artifact. The job is named `purlin`. The tag run reruns the tagged
tests on a clean machine, recomputes every committed record, brief and signature against the
tagged code, checks that every file under `ci/` was committed by the runner's own identity, and
ends with the gate check. No breaks run on a runner.

**Records.** Evidence lives in the tree, as
`.purlin/records/<source>/<feature>/<timestamp>-<commit7>-<runner>[-<os>].json`, one file per
audit run, committed by whoever ran it. The folder is the source: `.purlin/records/local/` is
anyone's, `.purlin/records/ci/` is a remote runner's, and a file whose own `source` field
disagrees with its folder is ignored with a warning. Both count at every gate. A feature keeps
the newest three records per operating system per source and the rest are pruned.

**Test results.** `purlin:test` writes `.purlin/tests/<feature>.json` per feature and one
`.purlin/tests.md` table for the project, and commits them as `purlin: tests at <sha7>`, so a
teammate reads your run on the git host without running anything.

**Platforms.** A rule's passed cell carries one entry per operating system a counting run
covered. The cell reads `partial` when the tests passed on some and failed or did not run on
others, which is not met, and `partial` has its own tile and filter at every gate. Test strength
is platform independent.

**Briefs.** One file per rule per set of hashes,
`.purlin/briefs/<source>/<feature>/<RULE-N>.<hash8>.brief.json`, committed beside the records. A
brief reports three things: the test strength beside the minimum, what the audit observed as the
sentences the audit wrote, and whether it could settle the question. **It recommends nothing.**
The four verdict words are retired with it.

**The free checks fold into the audit.** Their names leave every surface. The scans of the proof
text and the test body run as hints handed to the AI audit, which writes what it observed in
plain sentences; an audit that settled and still observed a gap proves the rule `weak` with that
sentence as the reason. `ready` means the rule has a proof, nothing more.

**The bar replaces risk.** Every rule has a bar, `passed` or `strong`, tagged `[bar: passed]` or
`[bar: strong]`; a rule with no tag takes the project's gate. The bar decides the evidence the
rule needs, whether the AI audit runs on it, and whether it needs a signature. `purlin:spec`
writes no bar tag at `passed`. `risk` and `ai_review_at` are gone, and `sign_at` is `strong` or
`all`.

**Signatures and holds.** One file per signature,
`specs/<category>/<feature>.signatures/<RULE-N>.<hash8>.<signer-slug>.json`, so two signatures
never conflict. It binds the hashes of the rule text, the proof text and the test body, the
rule's bar, and what the audit observed: the strength, the observation sentences and whether it
settled. A re-audit that sees something different stales the signature. The people who may sign
are `signers` in `.purlin/config.json`, changed by pull request, so git history records who could
sign and when. A hold is a person's committed statement that the test does not prove the proof,
with the missing case named; while it is current both the strong cell and the signed cell read
`held`, whatever the tests do. A `--note` is the one line a signer writes for a rule reading
`manual test` or `unsettled`.

**No machine writes a signature file, ever.** A signature directory holds only files a person
wrote.

**Two lists, two tabs.** The Review list holds the rules whose strong cell reads `manual test`,
`unsettled` or `held`, at `strong` and above. The Sign list holds the signable rules at `signed`.
`purlin:sign` walks Review then Sign; the dashboard shows the same two as its Review tab and its
Sign tab. `list` is the word for what the command walks and `tab` for what the page draws. A weak
rule is build work and stays on the board, and so is a rule reading `not audited`.

**The gate check.** `scripts/ci/verify_gate.py` becomes `scripts/ci/gate_check.py`, its log
prefix `gate:`, its sections `Not passed (n)`, `Partial (n)`, `Weak (n)`, `Not audited (n)`,
`To review (n)` and `To sign (n)`, and its JSON key `result` in place of `verdict`.
`purlin:sign` runs it before it writes a tag, and a runner runs it as the last step of every run.

**Breaks engines.** `purlin:audit` breaks the code on purpose at `strong` and above and reports
the share of those breaks the tests caught as the **test strength**, an integer percent. Three
engines ship, chosen by `mutation_engine` in the config: mutmut for Python, Stryker for
JavaScript and TypeScript, and Stryker.NET for C#. SQL and Bash have no engine, so their
strength reads `n/a` and the strong cell rests on what the audit observed.

**`@env`.** A proof that can only be proved on one operating system carries `@env(windows)`,
`@env(macos)` or `@env(linux)`. Those three are the whole vocabulary. Where a project has a
runner, `purlin:init` reads the tags and writes a matrix to match. On a host that does not match,
the test is skipped and the passed cell reads `not run` with `<os>: no record yet`;
`purlin:test --remote` pushes a run branch, finds the run by that branch, waits on it and pulls
the records back.

**The dashboard.** One HTML page on the design tokens, with no framework and no build step. Its
tiles, columns and filters scale with the gate, and its top bar carries the gate, the signed tag
this commit holds and how old the data is. It opens from disk; nothing is published and no
artifact is uploaded. `scripts/report/scan.py --repo <url>` prints the same rollup for anyone
holding only a URL.

**The tools.** `tools/PM/` and `tools/QA/` are Claude Desktop skills for people with no
checkout. The PM tool drafts and edits specs and anchors and opens the pull request; the QA tool
produces the triage report and opens pull requests with proof edits.

**Formats.** The spec, proofs and anchor formats change wording only. The record format, the
signature format (from `approval_format.md`), the new test results format, the payload schema and
`references/drift_criteria.md` each carry a `> Format-Version:` line; a tool that parses any of
them should read that line rather than a number written in prose.

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
| `verdict`, the four verdicts | what the brief reports: the strength, the observations, settled |
| `Reviewed`, the state | the strong cell's word |
| `re-verify pending` | the passed cell reading `code changed` |
| `Proof ready` | the spec status `ready` |
| `lowest state`, `seven states` | the spec status and the three cells |
| `auto-approval` | nothing: no machine writes a signature file |
| `review queue` | review list |
| `purlin:verify`, `purlin:review`, `purlin:approve` | `purlin:audit`, `purlin:sign` |
| `verify_gate`, `verify-gate:` | `gate_check`, `gate:` |
| `validated/<name>` and `record/<name>` tags | `signed/<version>`, which `purlin:sign` writes |
| `needs a person` | `manual test`, `unsettled` or `held`, each naming the work. The one surviving use is the review list's header |
| `risk`, `[risk: ...]`, `ai_review_at` | the **bar**, `[bar: passed]` or `[bar: strong]` |
| `manual audit` | `not audited` and `unsettled` |
| `not required` | removed: the signed cell carries `required` false and reads `signed` or `unsigned` |
| the source `developer` | the folder: `local/` or `ci/` |
| `happy_path_only` and the other free-check names | the sentence the audit wrote about what it observed |
| `pre_push`, the pre-push hook | nothing: a push is free and no hook runs |

`audit` is un-retired and means one thing: the level 2 run. An audit proves a rule strong or
weak. The grading scores the earlier `purlin:audit` produced stay retired.
`references/glossary.md` lists each word and the spelling it replaced.

### What was removed

Gone in 0.10.0: the two LLM grading scores and the skill and agent that produced them; the
runner registry and its per-runner proof files, replaced by `@env` and the runner matrix; the
committed evidence files, replaced by records; the committed proof files, which are now runtime
state under `.purlin/runtime/` and are not committed at all; the committed dashboard data; the
pre-push hook and every branch rule Purlin used to print; the pull request comment and the
dashboard artifact; the design-tool importer, the visual hash and the live design-tool
connection, replaced by exported files under `designs/` reviewed by pull request; and C and PHP
support, so a project that used either keeps its proofs only by writing a custom proof plugin.
Several flags went with them. A `@manual` proof stays: it has no test, its strong cell reads
`manual test`, and its evidence is a signature carrying a one-line note.

### The 0.10.0 line that never shipped

An earlier 0.10.0 development line added two LLM grading scores, one for proof descriptions and
one for test bodies, together with a skill and an agent to produce them. A later one added a
seven-state ladder. Neither was released, and 0.10.0 as it ships has neither. What a person needs
before signing a rule is a brief: the test strength from the newest record, and what the AI audit
observed where the rule's bar asks for one. `references/review_criteria.md` holds those criteria.

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
