# Release Notes

## Unreleased — 0.10.0

For a project running 0.9.5. This section is what differs between 0.9.5 and 0.10.0: what is
new, what changed and what you do differently, what is gone, and what `purlin:init --update`
does to your project.

In 0.9.5 a rule was covered when a test carrying a proof marker passed, `purlin:verify` issued a
receipt, and `purlin:audit` graded each proof `STRONG`, `WEAK` or `HOLLOW`. In 0.10.0 Purlin
keeps two things, the evidence and the sign-off, and shows two facts about them; every rule
carries two cells, `passed` and `strong`. Purlin no longer installs anything in your test suite:
a test is any test in your own suite with one comment above it.

### What is new

- **Two facts, no gate.** The status and the dashboard say whether the tests are met on the committed evidence, and whether this code is signed.
- **The hand-off is run and commit**: purlin:test --all --commit, and your project's own run for any other system.
- **purlin:sign builds the evidence package and signs it**, at any time, in any project; it stops only at hand checks, whose note is optional, and refuses results not taken on this code.
- **An anchor rule with nothing to check passes, and says so.**
- **Slow proofs.** Tag a proof `@slow` and `purlin:test` never starts its test; `purlin:test --all` runs everything. Until it has passed, the status lists it: `1 slow proof to run: purlin:test --all`.
- **A test comment whose proof was reworded is caught** until the test changes.
- **The audit runs heuristic spot tests, then plants one bug per changed proof** in a copy of the project and sees whether the proof's own test catches it; it reports the share of rules it found strong. Run it by hand; nothing blocks on it.
- **The evidence package records who wrote and last changed each rule, proof and test**, from git.
- **The dashboard names the branch and commit its data describes**, and its page is written with its data.
- **A Purlin tool call names its folder**; a call that names none is refused with the fix.
- **Cut:** drift's role views, setup's questions but one, and most settings.
- **The formats** stand at spec 23, anchor 12, evidence 9, signature 15, package 10 and marker 4,
  the drift criteria at 13, and the dashboard's data at schema 14.

In more words:

- **The two facts.** Every status opens `Tests: met` or `Tests: not met`, then
  `Sign-off: signed 0.1.0 at a1b2c3d`, `Sign-off: signed 0.1.0, 4 commits since` or
  `Sign-off: not signed`. The dashboard shows the same two in its header boxes.
- **The summary and `Left to do`.** Every run, every audit and `purlin:status` end on one line
  of counts, `40 rules. 35 pass their tests.`, with
  ` The audit found 30 of 35 rules strong (85%).` added where the audit has read a rule, then
  `Left to do`, one line per kind of remaining work with its count and the command that does it,
  such as `3 rules to fix: purlin:build`. The first line is the next step. A project whose tests
  are met and whose code is not signed ends on
  `Every rule passes its tests on the committed evidence. To sign it: purlin:sign`.
- **Evidence in the repository.** Every run writes `.purlin/evidence/local/<feature>.json`, one
  file per feature with one section per operating system. Nothing is committed unless you pass
  `--commit`, which makes two commits: the specs, the marked tests and the settings the results
  describe, as `purlin: specs, tests and settings for <feature>, ...`, then the evidence, as
  `purlin: evidence at <sha7>`. Your project's own run on another system writes `.purlin/evidence/ci/<feature>.json`. A
  result counts wherever it ran and records who ran it, on which machine and on which commit.
  Results written and not committed are left to do, as
  `1 feature whose results are not committed: purlin:test --commit`.
- **Out of date.** Each section carries a fingerprint of the spec, the code its `> Scope:`
  names and the tests. When any of them changes, the rule's passed cell reads `out of date`,
  naming what changed, until the next run.
- **A run covers what the change touched.** `purlin:test` with no feature named runs only the
  features that are out of date or have no run on this operating system, and prints what it
  selected and why, `Selected 2 of 34 features: login (code changed since a1b2c3d), invoice (no
  run on macOS yet).` `purlin:test --all` runs everything.
- **The audit.** `purlin:audit` runs the tests, then for each rule that passes: six heuristic
  spot tests that read each test as text, with no model; one planted bug per proof whose test or
  covered code changed, made in a copy of the project and never in the project; and the model's
  reading, which explains what was found and decides nothing. A spot test that fires, or a
  planted bug the proof's own test did not catch, makes the rule `weak`, left to do as
  `to strengthen`, and stops nothing. It ends on what the model cost and on
  `The audit found 4 of 5 rules strong (80%).`
- **The sign-off.** `purlin:sign` reads the committed evidence, names who ran the tests, where
  and when, builds `.purlin/evidence/package/<version>.json`, and walks it: an overview, the
  audit's findings as a list you may open, and one stop per hand check, where you may type what
  you saw. One file per signer per version,
  `.purlin/evidence/package/<version>.signoffs/<signer-slug>.json`, in a signed commit
  `sign(<version>): <signer email>`, carrying the package's fingerprint, the signer's name and
  email as git holds them, the time, the key's fingerprint, what the walk showed and every note.
  The first sign-off of a version carries the package and writes the signed tag
  `signed/<version>`; later sign-offs are added and the tag does not move. A sign-off counts when
  its commit carries a signature, made with any key, that verifies over the commit, and its
  package hash is the committed package's: Purlin records who signed and does not decide who may.
  With no key set up, `purlin:sign` shows the commands that set one up, offers to run them and
  carries on. `purlin:sign --show` and `--answers <file>` let the agent walk it with you,
  `--version <version>` names the version, and `--check <file>` checks a package against its
  fingerprint.
- **The sign-off refuses results not taken on this code.** Uncommitted work, evidence not
  committed, a result taken before the code last changed, a rule that does not pass, a broken
  spec, or the branch's copy on the host holding commits the checkout lacks: each prints one line
  naming the command, and nothing is written. A weak rule, a rule not audited and a rule with no
  proof are listed, not refused.
- **A hand check reads `checked at sign-off`**, and after a sign-off shows its last note with the
  version it was signed at and how many commits have come since.
- **A number written twice or a line left from a merge conflict fails the spec.** Every rule of
  that spec reads failed with the reason, a sign-off is refused, and Left to do reads
  1 spec to repair: purlin:spec. `purlin:spec` renumbers a number written twice when you say
  yes, with a dry run first: the number already on the default branch keeps it, and the rule or
  proof from the branch not yet merged moves to the next free number, with its test comments.
- **Drift reads your checkout after a pull or a merge**, in one view: the rules and proofs added,
  changed and moved, each number written twice and which line moves, each test comment whose
  proof's wording changed, and each anchor behind its source. It says how old your copy of the
  default branch is, never fetches and never pulls an anchor.
- **A spec ahead of its code is information, not a warning**:
  `login: 1 file its scope names is not written yet: src/gone.py. Run purlin:build login, or correct the path with purlin:spec login.`
- **Purlin runs the tests where you are.** A proof tagged `@env(<os>)` for a system your machine
  is not is listed by every status, as `22 rules to test on Windows: run purlin:test on Windows`. Reaching
  that system is your project's own setup: ask the AI, and it writes a file for your git host,
  GitHub or Azure DevOps, that runs `scripts/run/purlin_run.py --ci --commit` there and returns
  the results through git. Purlin ships no such file, starts no run on another machine and
  pushes nothing.
- **Worktrees.** Each checkout has its own results, status and dashboard. After merging work
  from a worktree, run `purlin:status` in the main checkout.
- **A mistake in a spec is warned of, with its fix.** The status and every run print one line
  naming the spec, the mistake and the command that fixes it, and carry on: two specs with one
  name, a rule number written twice, a proof line that cannot be read, and a first heading that
  names another feature.
- A spec records the highest rule number it has held in `> Highest-Rule:` and the highest proof number in `> Highest-Proof:`, so a deleted number is never used again.
- A remote anchor is copied as its source holds it. A `> Requires:`, `> Global:` or `> Scope:` line in it is warned of on every status and test run, naming the source's owners as the ones to take it out.
- `purlin:init` asks whether it may commit the files it wrote, and with `--yes` commits them as `chore(init): set up Purlin`.
- A plain `tests/test_*.py` project is suggested pytest.
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
- **A rule without a proof is left to do** as `to write a proof for` once its tests pass, and
  reads `no proof` in its strong cell. A proof is QA's plan in plain language;
  `references/spec_quality_guide.md` is the guideline for a good one.
- **`purlin:test` replaces `purlin:unit-test` and `purlin:verify`.** It runs every marked test of
  the features it runs; there is no tier. `purlin:test <feature>` runs one.
- **`purlin:status`** prints the two facts, then one row per spec,
  `Spec | Rules | Proofs | Tests`, with a `Strong` column where the audit has read a rule, then
  the summary and `Left to do`. `purlin:status <name>` shows one spec's rules.
- **A `@manual` proof** is a hand check: a person looks at it in the sign-off walk and may type
  what they saw, and the note goes into the sign-off. A stamped
  `@manual(<email>, <date>, <sha>)` is read as a plain `@manual`, and the file that carries one
  is named in the warnings.
- **Rule tags.** Nothing reads `(deferred)`, `(assumed ...)` or `(confirmed)`; the text stays
  in the rule's words, and a rule that carried `(deferred)` needs a test like any other.
- **`> Scope:`** is optional; a spec without one runs on every `purlin:test`.
- **The dashboard** is written when `purlin:test`, `purlin:audit`, `purlin:sign` or
  `purlin:status` finishes, page and data together, and at no other time. Its header names the
  branch, the commit and the time its data was written, in your own timezone, as `main at a1b2c3d, written 06:42 EDT`.
  Neither file is committed. It opens from disk.
- **One settings file**, `.purlin/config.json`, committed, holding `version` and `tests`.
  `purlin:init` asks one question, whether to commit what it wrote. A settings file that cannot
  be read stops every command with
  `.purlin/config.json cannot be read: <cause>. Fix the file by hand; nothing ran and nothing was saved.`
- **The skills start Purlin's scripts through the interpreter lookup**,
  `scripts/purlin_python.sh`, which finds Python 3 as the plugin's server does, `py -3` on
  Windows included.
- **An anchor is a set of rules for the whole project.** Its tests check the whole project, and each of its rules is counted and audited once. A rule that holds only for some features is written in each of their specs.
- **A spec names no anchor.** `> Requires:` and `> Global:` are not read, and neither is `> Scope:` on an anchor; each is warned of with its fix, and `purlin:init --update` takes them out.
- **A feature's row counts its own rules.** The dashboard lists the anchors in a section of their own, `Anchors`, above the spec table.
- **Any change to the project makes an anchor's results out of date**, but for the records Purlin writes under `.purlin/evidence/`, the package and its sign-offs among them.
- **No bug is planted for an anchor.** The spot tests and the model's reading alone judge its tests.
- An anchor is copied only from a spec in Purlin's format kept in a git repository. `purlin:anchor add` refuses a text file, a description in words or a file with no rule. The status and `purlin:drift` say an anchor is behind its source and pull nothing; only `purlin:anchor sync` pulls.

### Windows

The parts are proven on Windows and the whole path on the Mac. The whole path on Windows, from
setup to a sign-off, is not walked for 0.10.0.

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
- Every setting but `version` and `tests`: `pre_push`, `test_framework`, `spec_dir`, `report`,
  `digest` and the rest.
- The design tie: `> Visual-Reference:`, `> Visual-Hash:` and a Figma `> Source:`.
- The `tools/` skills for Claude Desktop. Product and QA work in Claude Code on a checkout.
- C and PHP support.
- `purlin:init` flags `--force`, `--add-plugin`, `--list-plugins`, `--sync-audit-criteria`,
  `--audit-llm`, `--pre-push`, `--report`, `--digest` and `--mcp`.
- The shell command line that printed the settings, `python3 scripts/mcp/config_engine.py`.

### What `purlin:init --update` does

It reads what the project contains, not its `version` field, and it upgrades from 0.9.5 only.
Until the update runs, `purlin:status` prints `→ Run: purlin:init --update`, and a test run stops
with
`This project was set up by an older Purlin and not upgraded, so nothing ran. Run purlin:init --update.`
The run goes in this order:

1. It prints every pending migration with the files it touches, then asks before each one, with
   a question ending `[y/N]`. `--yes` answers yes to every question. A declined migration is
   left pending. Every file it rewrites is copied beside itself first, as
   `<name>.local-<sha8>.bak`.
2. It rewrites or removes each line 0.9.5 wrote into a spec that 0.10.0 does not read: the
   `> Visual-Reference:` and `> Visual-Hash:` lines, a `> Source:` that names Figma and the
   `> Pinned:` that goes with it; `> Requires:` and `> Global:` from every spec, and `> Scope:`
   from every anchor; a trailing `@windows` on a proof line becomes `@env(windows)`; and
   `@unit`, `@integration` and `@e2e` go from proof lines.
3. It removes the files 0.9.5 kept that 0.10.0 does not use: the proof files and the receipts
   beside the specs, `.purlin/cache/`, the plugin copies under `.purlin/plugins/` and a workflow
   that committed proof files. It untracks `.purlin/report-data.js` and adds it to `.gitignore`.
4. It removes the `pre-commit` and `pre-push` hooks under `.git/hooks/` that 0.9.5 installed,
   and leaves a hook another tool wrote.
5. It rewrites `.purlin/config.json` to `version` and `tests`, and names every key it drops. It
   turns `test_framework` into `tests`, one entry per framework the tree still runs (`xunit`
   becomes `dotnet`), naming any it drops.
6. It writes `.purlin/evidence/README.md`, and replaces `purlin-report.html` at the project
   root, the link 0.9.5 left or a copy that differs, with the 0.10.0 page. A project with no page
   there is left without one; the first `purlin:status` writes it.
7. It rewrites each 0.9.5 marker as a comment above the same test, one line per file. A shell or
   SQL test file becomes one test that passes when it exits 0. A marker it cannot place, such as
   a module-wide `pytestmark`, is named by file and line and left for you.
8. It removes the `pytest_plugins` entry in `conftest.py` (the file too, when it held nothing
   else) and the reporter entry in the Jest or Vitest configuration or `package.json`, and names
   a `.csproj` that compiles the xUnit logger for you to edit by hand.
9. It commits everything it changed in one commit,
   `chore(update): migrate to 0.10.0 (<ids>)`.

After it, run `purlin:test`. The receipts and `@manual` stamps 0.9.5 wrote do not carry
forward: a version is signed through `purlin:sign`, after `purlin:test --all --commit`.

### Words from 0.9.5, and what to say now

| 0.9.5 | 0.10.0 |
|-------|--------|
| `purlin:verify`, receipt, `*.receipt.json`, vhash | `purlin:test --all --commit` for the evidence, `purlin:sign` for the evidence package and the sign-off |
| `purlin:unit-test` | `purlin:test` |
| proof file, `<feature>.proofs-<tier>.json` | the evidence, `.purlin/evidence/<source>/<feature>.json` |
| proof marker, `@pytest.mark.proof(...)`, `[proof:...]`, `PurlinProof`, `purlin_proof`, `-- @purlin` | the marker comment, `purlin: <feature> PROOF-<n>` |
| proof plugin | your own test command and its report |
| tier, `@integration`, `@e2e` | none: `purlin:test` runs every marked test |
| `@windows` | `@env(windows)` |
| `@manual(<email>, <date>, <sha>)`, `purlin:verify --manual` | a hand check, noted in the sign-off walk |
| `STRONG`, `WEAK`, `HOLLOW` | the strong cell, `strong` or `weak`, with the audit's findings |
| coverage, `PASSING`, `PARTIAL`, `VERIFIED` | the cells, and the summary, `40 rules. 35 pass their tests.` |
| `pre_push`, `warn`, `strict` | none: nothing runs at push time; the status says whether the tests are met |
| `test_framework` | `tests` |
| `purlin:find` | `purlin:status <name>` |
| `.purlin/config.local.json` | `.purlin/config.json` alone |
| `> Requires:`, `> Global: true` | none: every anchor covers the whole project |

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
