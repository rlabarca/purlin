# Release Notes

## Unreleased — 0.10.0

For a project running 0.9.5. This section is what differs between 0.9.5 and 0.10.0: what is
new, what changed and what you do differently, what is gone, and what `purlin:init --update`
does to your project.

In 0.9.5 a rule was covered when a test carrying a proof marker passed, `purlin:verify` issued a
receipt, and `purlin:audit` graded each proof `STRONG`, `WEAK` or `HOLLOW`. In 0.10.0 each rule
goes through up to three steps, `passed`, `strong` and `signed`, one command answers each, and
one project setting, the gate, says how far every rule must go. Purlin no longer installs
anything in your test suite: a test is any test in your own suite with one comment above it.

### What is new

- **The gate and the three steps.** `.purlin/config.json` carries `gate`: `passed` (every
  rule's tests pass, `purlin:test`), `strong` (the tests pass and the audit found them sound,
  `purlin:audit`) or `signed` (both, and a person signed, `purlin:sign`). Every rule is asked
  what the gate asks. `purlin:init --gate <value>` changes the gate; raising it adds what is
  missing and lowering it deletes nothing.
- **The summary and `Left to do`.** Every run, every audit and `purlin:status` end on one line
  of counts, `40 rules. 35 pass their tests. 30 are strong. 20 are signed.`, then `Left to do`,
  one line per kind of remaining work with its count and the command that does it, such as
  `5 rules to audit: purlin:audit`. The first line is the next step. A finished project reads
  `Nothing left to do.`, and at the gate `signed` the line names the push of the tag.
- **Evidence in the repository.** Every run writes `.purlin/evidence/local/<feature>.json`, one
  file per feature with one section per operating system, and the table `.purlin/tests.md`.
  Nothing is committed unless you pass `--commit`, which makes two commits: the specs, the
  marked tests and the settings the results describe, as
  `purlin: specs, tests and settings for <feature>, ...`, then the evidence, as
  `purlin: evidence at <sha7>`. A remote runner writes `.purlin/evidence/ci/<feature>.json`. A
  result counts wherever it ran and records the machine it ran on.
- **Out of date.** Each section carries a fingerprint of the spec, the code its `> Scope:`
  names and the tests. When any of them changes, the rule's passed cell reads `out of date`,
  naming what changed, until the next run.
- **A run covers what the change touched.** `purlin:test` with no feature named runs only the
  features that are out of date or have no run on this operating system, and prints what it
  selected and why, `Selected 2 of 34 features: login (code changed since a1b2c3d), invoice (no
  run on macOS yet).` `purlin:test --all` runs everything.
- **The audit calls a model.** `purlin:audit` runs the tests, then one model call per rule,
  four at a time by default (`audit_parallel`, 1 to 16), and writes what it found into the
  evidence with the model's name on every finding. From the gate `strong` up a finding makes
  the rule `weak`. A proof longer than 60 words, or holding two cases, is written among the
  audit's notes and does not make the rule weak.
- **Test strength, one share per feature.** Mutation testing is optional and off by default;
  where it is on, the share of deliberate breaks the tests caught must reach `min_strength`.
  The share is measured once per feature, in every language, and every rule of the feature is
  judged on it. With breaking on, nothing measured leaves a rule weak: an engine not installed,
  one that ran past its time limit, or one that wrote no report makes the feature's rules `weak`
  with the reason `strength not measured: <reason>`, counted as `rules to measure: purlin:audit`,
  and the reason names the command that fixes it. A spec that names no code files leaves its
  rules weak the same way, counted as `rules to tie to their files: purlin:spec`. An engine that
  cannot run on this system counts as none, and the audit alone decides.
  `purlin:audit --arm-timeout <seconds>` gives the breaking tool longer per feature, 3600
  seconds by default. Engines: mutmut for Python, Stryker for JavaScript and TypeScript,
  Stryker.NET for C#. mutmut does not run on Windows.
- **Signatures.** `purlin:sign` signs a rule, a feature or every rule that waits for a person,
  and with no argument walks them one at a time, asking `sign / case / skip`. A signature is one
  file under `specs/<category>/<feature>.signatures/`, in a signed commit, made over the rule,
  its proof, its test, the code the feature lists, what the audit found and the machine the
  tests ran on for each system; a change to any of them ends it, and the rule is left to do as
  `to sign`. It records the signer's name and email as git holds them, the time and the key's
  fingerprint. It counts when its commit carries a signature, made with any key: Purlin records
  who signed and does not decide who may. With no key set up, `purlin:sign` shows the commands
  that set one up, offers to run them and carries on.
- **The signed tag.** At the gate `signed`, when nothing is left to do and every result came
  from committed work, `purlin:sign` writes the evidence package, commits it, and writes the
  signed tag `signed/<version>` on that commit. You push it. Below `signed` it writes no tag and
  no package. `purlin:sign` exits 1 when it refused the tag for a reason to fix: work or results
  not committed, no version, a package not committed, or git could not write the tag.
- **The evidence package.** `purlin:export` writes `.purlin/evidence/package/<version>.json`,
  one data file describing a version for a regulated document and sign-off system: every rule's
  words, proofs, tests, results, what the audit found, who signed, the count at each step, what
  is left, the state `finished` or `not finished`, and a fingerprint of the file. Purlin makes no
  claim of compliance.
- **A remote runner for one reason**: a proof tagged `@env(<os>)` for an operating system your
  machine is not. It runs on GitHub or Azure DevOps, on a push to a `run/*` branch and on a push
  of a `signed/*` tag. A remote run on a system runs only the tests tied to proofs tagged for
  that system, and a runner file names a remote machine only for a system the machine running
  setup is not. A project with no such proof gets no workflow.
- **Drift by role.** `purlin:drift pm`, `eng` or `qa` reports what your last pull, merge,
  rebase, checkout, clone or reset brought in, read from git's own log of HEAD.
- **A mistake in a spec is warned of, with its fix.** The status and every run print one line
  naming the spec, the mistake and the command that fixes it, and carry on: a `> Scope:` entry
  that finds no file, two specs with one name, a rule number written twice, a proof line that
  cannot be read, and a first heading that names another feature.
- `> Requires:` names anchors only. A name that is a feature's spec is warned of, and its rules do not apply.
- A spec records the highest rule number it has held in `> Highest-Rule:` and the highest proof number in `> Highest-Proof:`, so a deleted number is never used again. The spec format is at version 20.
- `purlin:init` asks whether it may commit the files it wrote, and with `--yes` commits them as `chore(init): set up Purlin at the gate <gate>`.
- `purlin:test --remote` with no `gh` on GitHub or no `az` on Azure DevOps pushes nothing and names the program to install.
- The first test run keeps running examples inside a function's documentation where the project's own test command ran them.
- At the gate `signed`, signing a rule whose spec names no files says, on that rule's line, that the signature does not count until the spec names them.
- Every system a person reads is written `Windows`, `macOS` or `Linux/Unix`.

### What changed, and what you do differently

- **The marker is a comment.** In place of the decorator, the title tag, the trait or the
  harness call, one comment above the test: `# purlin: login PROOF-1` in Python and shell,
  `// purlin: login PROOF-1` in JavaScript, TypeScript, C# and Go, `-- purlin: login PROOF-1`
  in SQL. Where a rule has no proof, the comment names the rule, `purlin: login RULE-2`. A test
  may carry several.
- **Your own test command.** The `tests` setting holds one entry per test tool: the command,
  with the flag that writes a report, where the report lands, its format and the test file
  globs. Setup leaves it empty. The first test run suggests a command for every test tool it
  recognises, and they are written together once you confirm; on Windows the Python command
  starts `py -3 -m pytest`. Purlin runs it and reads JUnit XML, the TRX `dotnet test` writes, or
  the JSON `go test -json` writes; a shell or SQL test file passes when it exits 0. Jest needs
  `jest-junit` to write its report: `npm install --save-dev jest-junit`. Go is new.
- **Proofs are optional at `passed`** and required from `strong` up, where a rule with a test and
  no proof reads `no proof`. A proof is QA's plan in plain language;
  `references/spec_quality_guide.md` is the guideline for a good one.
- **`purlin:test` replaces `purlin:unit-test` and `purlin:verify`.** It runs every marked test of
  the features it runs; there is no tier. `purlin:test <feature>` runs one.
- **`purlin:status`** prints one row per spec, `Spec | Rules | Proofs | Tests`, with `Strong`
  and `Signed` columns as the gate adds them, then the summary and `Left to do`.
  `purlin:status <name>` shows one spec's rules.
- **A `@manual` proof** is a hand check, at any gate: it is left to do as `to test by hand` until
  a person signs it, with a note when they give one,
  `purlin:sign login RULE-4 --note "<what you saw>"`. A stamped
  `@manual(<email>, <date>, <sha>)` is read as a plain `@manual`, and the file that carries one
  is named in the warnings.
- **Rule tags.** Nothing reads `(deferred)`, `(assumed ...)` or `(confirmed)`; the text stays
  in the rule's words, and a rule that carried `(deferred)` needs a test like any other.
- **`> Scope:`** is required at the gate `signed`, where a rule of a spec that names no files is
  signed and its signature does not count. Below `signed` it is optional; a spec without one
  runs on every `purlin:test`.
- **The dashboard** refreshes when `purlin:test`, `purlin:audit`, `purlin:sign` or
  `purlin:status` finishes, and at no other time. Its data, `.purlin/report-data.js`, is not
  committed. It opens from disk.
- **One settings file**, `.purlin/config.json`, committed. `purlin:init` asks the gate, and at
  `strong` and `signed` whether to break the code on purpose. A settings file that cannot be
  read stops every command with
  `.purlin/config.json cannot be read: <cause>. Fix the file by hand; nothing ran and nothing was saved.`
- **The skills start Purlin's scripts through the interpreter lookup**,
  `scripts/purlin_python.sh`, which finds Python 3 as the plugin's server does, `py -3` on
  Windows included.
- An anchor is copied only from a spec in Purlin's format kept in a git repository. `purlin:anchor add` refuses a text file, a description in words or a file with no rule, and `purlin:drift` and `purlin:anchor sync --check` report an anchor made from plain text as `error`.

### Windows

The parts are proven on Windows and the whole path on the Mac. The whole path on Windows, from
setup to a signed tag, is not walked for 0.10.0.

### What is gone

- `purlin:verify` and its receipts, `purlin:unit-test`, `purlin:find` (use
  `purlin:status <name>`) and `purlin:rename` (`agents/purlin.md` says what moves together).
- The proof plugins for every framework, the proof files they wrote beside each spec, and
  the wiring `purlin:init` put in `conftest.py`, the Jest or Vitest configuration and the
  `.csproj`.
- The tier tags `@integration` and `@e2e`, and `@windows` as a tag of its own.
- The `STRONG`, `WEAK` and `HOLLOW` grades, the audit cache, and the external audit model and
  criteria settings.
- The git hooks: nothing runs at commit or at push time, and a push is free.
- The committed project digest and the Claude Code hook that refreshed it.
- The per-person settings file, `.purlin/config.local.json`. A copy left in a project is not
  read.
- The design tie: `> Visual-Reference:`, `> Visual-Hash:` and a Figma `> Source:`.
- The `tools/` skills for Claude Desktop. Product and QA work in Claude Code on a checkout.
- C and PHP support.
- `purlin:init` flags `--force`, `--add-plugin`, `--list-plugins`, `--sync-audit-criteria`,
  `--audit-llm`, `--pre-push`, `--report`, `--digest` and `--mcp`.
- The shell command line that printed the settings, `python3 scripts/mcp/config_engine.py`.

### What `purlin:init --update` does

It reads what the project contains, not its `version` field. Until the update runs,
`purlin:status` prints `→ Run: purlin:init --update`, and a test run stops with
`This project was set up by an older Purlin and not upgraded, so nothing ran. Run purlin:init --update.`
The run goes in this order:

1. It prints every pending migration with the files it touches, then asks before each one,
   `Apply <id>, which will <what it does>?`. `--yes` answers yes to every question and takes
   every default. Every file it rewrites is copied beside itself first, as
   `<name>.local-<sha8>.bak`.
2. `design-refs`: deletes each spec's `> Visual-Reference:` and `> Visual-Hash:` lines, a
   `> Source:` that names Figma and the `> Pinned:` that goes with it, one line per spec.
3. `os-tags`: rewrites a trailing `@windows` on a proof line as `@env(windows)`.
4. `kind-tags`: drops `@unit`, `@integration` and `@e2e` from proof lines.
5. `untracked-files`: deletes the proof files and the receipts beside the specs, untracks
   `.purlin/report-data.js` and `.purlin/cache/`, and adds `.purlin/report-data.js` to
   `.gitignore`.
6. `hooks`: removes the `pre-commit` and `pre-push` hooks under `.git/hooks/` that name Purlin.
7. `config`: rewrites `.purlin/config.json` with `version`, `gate`, `mutation_engine`,
   `min_strength`, `audit_parallel`, `tests` and `ci`, and names every key it drops
   (`spec_dir`, `pre_push`, `report`, `digest` and whichever others the file carried). It asks
   the gate question, defaulting to `strong` where `pre_push` was `strict` and to `passed`
   otherwise; turns `test_framework` into `tests`, one entry per framework the tree still runs
   (`xunit` becomes `dotnet`), naming any it drops; and at `strong` and `signed` asks the
   mutation question where an engine exists, defaulting to no.
8. `evidence`: writes `.purlin/evidence/README.md`.
9. `dashboard`: replaces `purlin-report.html` at the project root, the link 0.9.5 left into its
   own plugin folder or a copy that differs, with the 0.10.0 page, the bytes `purlin:init`
   copies. A project with no page there is left without one.
10. `workflows`: removes a workflow that committed proof files, and, after asking, writes the
    runner file where `purlin:init` writes it, `.github/workflows/purlin.yml` on GitHub or
    `purlin.azure-pipelines.yml` at the root on Azure DevOps, only where a proof is tagged for
    a system the machine running the update is not.
11. `markers`: rewrites each 0.9.5 marker as a comment above the same test, one line per file.
    A shell or SQL test file becomes one test that passes when it exits 0. A marker it cannot
    place, such as a module-wide `pytestmark`, is named by file and line and left for you.
12. `plugins`: removes the plugin copies under `.purlin/plugins/`, the `pytest_plugins` entry
    in `conftest.py` (the file too, when it held nothing else) and the reporter entry in the
    Jest or Vitest configuration or `package.json`, and names a `.csproj` that compiles the
    xUnit logger for you to edit by hand.
13. It commits everything it changed in one commit,
    `chore(update): migrate to 0.10.0 (<ids>)`.
14. It names each spec with no `> Scope:` line,
    `2 specs name no files, so their tests run every time: a, b. Run purlin:spec with each name to add its > Scope: line.`,
    and changes none.
15. It ends as `purlin:status` does, on the summary and `Left to do`.

After it, run `purlin:test`. The receipts and `@manual` stamps 0.9.5 wrote do not carry
forward: nothing in 0.9.5 bound what 0.10.0 signs, so at the gate `signed` every rule is left to
do as `to sign`, and at every gate a rule with a `@manual` proof as `to test by hand`.

### Words from 0.9.5, and what to say now

| 0.9.5 | 0.10.0 |
|-------|--------|
| `purlin:verify`, receipt, `*.receipt.json`, vhash | `purlin:test --commit` for the evidence, `purlin:sign` for the tag |
| `purlin:unit-test` | `purlin:test` |
| proof file, `<feature>.proofs-<tier>.json` | the evidence, `.purlin/evidence/<source>/<feature>.json` |
| proof marker, `@pytest.mark.proof(...)`, `[proof:...]`, `PurlinProof`, `purlin_proof`, `-- @purlin` | the marker comment, `purlin: <feature> PROOF-<n>` |
| proof plugin | your own test command and its report |
| tier, `@integration`, `@e2e` | none: `purlin:test` runs every marked test |
| `@windows` | `@env(windows)` |
| `@manual(<email>, <date>, <sha>)`, `purlin:verify --manual` | a hand check signed with a note |
| `STRONG`, `WEAK`, `HOLLOW` | the strong cell, `strong` or `weak`, with the audit's findings |
| coverage, `PASSING`, `PARTIAL`, `VERIFIED` | the cells, and the summary, `40 rules. 35 pass their tests.` |
| `pre_push`, `warn`, `strict` | the gate |
| `test_framework` | `tests` |
| `purlin:find` | `purlin:status <name>` |
| `dev` as a role | `eng` in `purlin:drift` |
| `.purlin/config.local.json` | `.purlin/config.json` alone |

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
