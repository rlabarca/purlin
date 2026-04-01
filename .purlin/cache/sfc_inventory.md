# SFC Inventory — Purlin Framework

## Directory Map

### agents/
- `purlin.md` — Agent definition (core loop, spec format, hard gates, skill routing)

### dev/ (framework maintenance, not distributed)
- `conftest.py` — Loads pytest_purlin plugin for internal tests
- `run_tests.sh` — Master test suite runner (7 suites)
- `test_mcp_server.py` — MCP server unit tests (JSON-RPC, sync_status, purlin_config, changelog)
- `test_config_engine.py` — Config resolution tests (two-file system)
- `test_gate_hook.sh` — Gate hook integration tests (RULE-1 through RULE-5)
- `test_session_start.sh` — Session cleanup tests
- `test_proof_pytest.sh` — Pytest proof plugin tests (PROOF-1 through PROOF-5)
- `test_proof_jest.sh` — Jest proof reporter tests
- `test_proof_shell.sh` — Shell proof harness tests

### hooks/
- `hooks.json` — PreToolUse (gate.sh) + SessionStart (session-start.sh) hook definitions

### references/
- `commit_conventions.md` — 8 commit prefixes, verification receipt format
- `hard_gates.md` — Gate 1 (invariant protection), Gate 2 (proof coverage)
- `purlin_commands.md` — Full command reference (13 skills)
- `spec_quality_guide.md` — Rule/proof writing guidelines, tier assignment, FORBIDDEN patterns
- `formats/anchor_format.md` — Anchor type prefixes, relationship to invariants
- `formats/invariant_format.md` — Invariant location, metadata, sync protocol
- `formats/proofs_format.md` — Proof file JSON schema, marker syntax per framework, tiers
- `formats/spec_format.md` — 3-section canonical format, metadata fields

### scripts/
- `gate.sh` — Pre-write gate hook (blocks invariant writes unless bypass lock)
- `session-start.sh` — Session cleanup (removes stale runtime files)
- `mcp/__init__.py` — Package init
- `mcp/config_engine.py` — Two-file config resolution (config.json + config.local.json)
- `mcp/manifest.json` — MCP tool definitions (sync_status, purlin_config, changelog)
- `mcp/purlin_server.py` — MCP stdio server (JSON-RPC 2.0, Python stdlib only)
- `proof/pytest_purlin.py` — Pytest plugin: collects @pytest.mark.proof markers, emits proof JSON
- `proof/jest_purlin.js` — Jest reporter: parses [proof:...] in test names, emits proof JSON
- `proof/shell_purlin.sh` — Shell harness: purlin_proof() + purlin_proof_finish, emits proof JSON

### skills/ (12 SKILL.md files)
- `build/SKILL.md` — Inject spec rules, implement code
- `changelog/SKILL.md` — Structured changelog with spec cross-references
- `config/SKILL.md` — Read/write .purlin/config.json
- `find/SKILL.md` — Search specs by name, show coverage
- `help/SKILL.md` — Display command reference
- `init/SKILL.md` — Initialize project for Purlin
- `invariant/SKILL.md` — Sync read-only constraint files from external sources
- `spec/SKILL.md` — Scaffold/edit feature specs in 3-section format
- `spec-from-code/SKILL.md` — Reverse-engineer specs from existing code
- `status/SKILL.md` — Show rule coverage via sync_status
- `unit-test/SKILL.md` — Run tests, emit proof files, report coverage
- `verify/SKILL.md` — Run all tests, issue verification receipts

---

## Detected Tech Stack

- **Python 3.8+** — MCP server, config engine, pytest proof plugin (stdlib only, zero external deps)
- **Bash/Shell** — Hooks, session init, shell proof harness, test suites
- **JavaScript (Node.js)** — Jest proof reporter
- **Markdown** — Specs, agent definitions, skill definitions, reference docs
- **JSON** — Hook config, MCP manifest, proof files, config files
- **MCP (Model Context Protocol) 2024-11-05** — JSON-RPC 2.0 stdio transport
- **pytest** — Test framework with custom proof plugin
- **Jest** — JavaScript test framework with custom reporter

---

## Preliminary Feature Candidates

### Executable Code Features
1. **MCP Server (purlin_server.py)** — JSON-RPC 2.0 stdio server exposing sync_status, purlin_config, changelog tools
2. **Config Engine (config_engine.py)** — Two-file config resolution with copy-on-first-access
3. **Gate Hook (gate.sh)** — Invariant write protection with bypass lock mechanism
4. **Session Start (session-start.sh)** — Runtime state cleanup on session init
5. **Pytest Proof Plugin (pytest_purlin.py)** — Proof marker collection, feature-scoped JSON emit
6. **Jest Proof Reporter (jest_purlin.js)** — Proof marker parsing from test names, feature-scoped JSON emit
7. **Shell Proof Harness (shell_purlin.sh)** — Shell-based proof collection with inline Python for JSON ops
8. **Hook Configuration (hooks.json)** — Hook registration for gate and session-start
9. **MCP Manifest (manifest.json)** — Tool interface definitions

### Instruction/Reference Features
10. **Agent Definition (purlin.md)** — Core agent loop, spec format, hard gates, implicit routing
11. **Skill Definitions (skills/*)** — 12 skill SKILL.md files defining user-facing commands
12. **Reference Docs (references/)** — Spec format, proof format, invariant format, anchor format, quality guide, hard gates, commit conventions, command reference

### Test Infrastructure
13. **Test Runner (run_tests.sh)** — Master orchestrator for 7 test suites
14. **Test Conftest (conftest.py)** — Pytest plugin loader for internal tests

---

## Cross-Cutting Concerns

### Feature-Scoped Overwrite Pattern
Used by all 3 proof plugins (pytest, jest, shell): load existing proof file → purge current feature's entries → append new entries → write merged result. Prevents cross-feature interference.

### Two-File Config Resolution
Used by MCP server tools: config.json (team) + config.local.json (user) with copy-on-first-access. Precedence: local > team > empty.

### Gate Protection with Bypass Lock
Invariant files (`specs/_invariants/i_*`) are write-protected. Only `purlin:invariant sync` can create bypass lock. Session-start clears stale locks.

### Spec 3-Section Format
All specs use: `## What it does`, `## Rules` (RULE-N), `## Proof` (PROOF-N). Enforced by sync_status parser.

### Verification Hashing (vhash)
`sha256(sorted rule IDs + sorted proof IDs/statuses)[:8]` — proves rules/proofs unchanged since verification.

### Role-Based Directives
sync_status and changelog support role filtering (pm, eng, qa) for prioritized output.

### Markdown Regex Parsing
purlin_server.py uses regex to extract sections from markdown specs. No schema validation — structural issues produce warnings.

---

## Code Comments Index

- **Zero TODO/FIXME/HACK comments** — Clean codebase
- **Architecture comments**: config_engine.py (lines 2-12), purlin_server.py (lines 1-12, 27-29), gate.sh (lines 1-11)
- **Feature-scoped overwrite documented**: pytest_purlin.py (line 79-80), jest_purlin.js (line 83), shell_purlin.sh (lines 24-66)
- **Test suite documentation**: Each test file has module-level docstrings listing rules covered
- **Function docstrings**: purlin_server.py has comprehensive docstrings for all public functions

---

## Test Tier Flags per Module

| Module | Default | @slow | @e2e | @manual | Notes |
|--------|---------|-------|------|---------|-------|
| purlin_server.py | YES | YES | — | — | Filesystem I/O, git ops, subprocess |
| config_engine.py | YES | YES | — | — | File I/O, env var resolution |
| pytest_purlin.py | YES | YES | YES | — | Requires actual pytest execution |
| jest_purlin.js | YES | YES | YES | — | Requires actual Jest execution |
| shell_purlin.sh | YES | YES | YES | — | Requires actual bash execution |
| gate.sh | YES | YES | — | — | Lock file detection, path matching |
| session-start.sh | YES | YES | — | — | File cleanup |
| hooks.json | YES | — | — | — | JSON structure validation |
| manifest.json | YES | — | — | — | JSON structure validation |
| Agent definition | YES | — | — | — | Grep-based structural checks |
| Skill definitions | YES | — | — | — | Grep-based structural checks |
| Reference docs | YES | — | — | — | Grep-based structural checks |
| run_tests.sh | — | YES | — | — | Orchestrates test suites |
