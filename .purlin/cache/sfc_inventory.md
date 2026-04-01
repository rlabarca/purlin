# Codebase Inventory (Phase 1)

## Directory Map

```
purlin/
├── scripts/                    # Consumer-facing framework tooling
│   ├── gate.sh                 # Pre-write hook: blocks invariant file writes
│   ├── session-start.sh        # Session hook: clears stale runtime locks
│   ├── mcp/
│   │   ├── purlin_server.py    # MCP server (sync_status, changelog, purlin_config)
│   │   ├── config_engine.py    # Two-file config resolution
│   │   ├── manifest.json       # MCP tool definitions
│   │   └── __init__.py
│   └── proof/
│       ├── pytest_purlin.py    # pytest proof collector plugin
│       ├── jest_purlin.js      # Jest proof reporter
│       └── shell_purlin.sh     # Bash proof harness
├── agents/
│   └── purlin.md               # Agent persona + core loop definition
├── skills/                     # 12 CLI skill definitions (SKILL.md each)
│   ├── build/                  # Implement from spec + rules
│   ├── changelog/              # Structured changelog
│   ├── config/                 # Read/write config
│   ├── find/                   # Search specs
│   ├── help/                   # Command reference
│   ├── init/                   # Bootstrap project
│   ├── invariant/              # Sync read-only constraints
│   ├── spec/                   # Scaffold/edit specs
│   ├── spec-from-code/         # Reverse-engineer specs
│   ├── status/                 # Show rule coverage
│   ├── unit-test/              # Run tests, emit proofs
│   └── verify/                 # Full verification + receipts
├── hooks/
│   └── hooks.json              # PreToolUse (gate.sh), SessionStart (session-start.sh)
└── dev/                        # Framework development tests
    ├── run_tests.sh            # Master test runner (all 7 suites)
    ├── conftest.py             # pytest config (loads pytest_purlin)
    ├── test_config_engine.py   # Config resolution unit tests
    ├── test_mcp_server.py      # MCP server unit tests
    ├── test_gate_hook.sh       # Gate hook functional tests
    ├── test_session_start.sh   # Session-start functional tests
    ├── test_proof_jest.sh      # Jest plugin integration tests
    ├── test_proof_pytest.sh    # pytest plugin integration tests
    └── test_proof_shell.sh     # Shell harness integration tests
```

## Tech Stack

- **Languages:** Python 3 (stdlib only), Bash, Node.js (minimal), Markdown
- **Frameworks:** MCP (JSON-RPC stdio), pytest, Jest (optional), Claude Code hooks
- **Dependencies:** Python stdlib (json, os, re, subprocess, glob, hashlib, shutil), Node.js glob
- **Execution Model:** Agent-driven skills (Claude interprets steps, invokes tools)
- **No external package dependencies** for core library code

## Preliminary Feature Candidates

### MCP Server & Config
1. **mcp-server** — JSON-RPC MCP server exposing sync_status, changelog, purlin_config tools
2. **config-engine** — Two-file config resolution (config.local.json > config.json), copy-on-first-access

### Proof Plugins
3. **proof-pytest** — pytest marker-based proof collector, feature-scoped JSON emission
4. **proof-jest** — Jest reporter parsing `[proof:feature:PROOF-N:RULE-N:tier]` from test titles
5. **proof-shell** — Bash harness with `purlin_proof()` accumulator + Python finalization

### Hooks
6. **gate-hook** — Pre-write hook blocking writes to `specs/_invariants/i_*` unless bypass lock
7. **session-start** — Session startup hook clearing `.purlin/runtime/invariant_write_lock`

### Skills (workflow definitions)
8. **skill-build** — Load spec + Requires dependencies, implement code, write proof-marked tests
9. **skill-spec** — Scaffold/edit 3-section feature specs, anchor/invariant support
10. **skill-verify** — Run all tests, compute vhash, issue receipts, --audit and --manual modes
11. **skill-unit-test** — Framework detection, tier filtering, feature-scoped proof emission
12. **skill-status** — MCP wrapper displaying coverage + actionable directives
13. **skill-changelog** — Git-based changelog with spec cross-references, role-aware output
14. **skill-spec-from-code** — Reverse-engineer specs via parallel agents, interactive taxonomy
15. **skill-init** — Bootstrap .purlin/, specs/, proof plugins per framework
16. **skill-invariant** — Sync read-only constraint specs from git/Figma sources
17. **skill-find** — Search specs by name, display coverage
18. **skill-config** — Read/write config via MCP
19. **skill-help** — Static command reference display

### Agent
20. **agent-definition** — Core loop, spec format, proof markers, hard gates, implicit routing

## Cross-Cutting Concerns

### Feature-scoped proof overwrite
All three proof plugins (pytest, jest, shell) use the same strategy: each test run replaces proof entries for the tested feature while preserving entries from other features. Solves "ghost proofs" problem.

### Invariant protection
gate.sh blocks writes to `specs/_invariants/i_*`. Bypass via `.purlin/runtime/invariant_write_lock` (JSON with `target` field). session-start.sh clears lock on startup. Only `purlin:invariant` creates the lock.

### Two-file config resolution
config.local.json (gitignored, per-user) > config.json (committed, team defaults). Copy-on-first-access auto-creates local from shared.

### Git integration
Project root detection (PURLIN_PROJECT_ROOT env or .purlin/ marker climbing). Git subprocess calls for changelog, staleness checks, commit SHAs. 5s timeout on git calls.

### Spec lifecycle
Draft → Write (3-section format) → Validate → Commit. Rules = testable constraints, Proofs = observable assertions. Coverage tracked via sync_status.

### Error handling
- Gate: exit code 2 with stderr message on blocked write
- Config: fallback to shared if local malformed
- Proof files: graceful merge (missing → empty dict)
- Git subprocess: 5s timeout, empty on failure

## Code Comments Index

- **No TODO, FIXME, or HACK comments found** — codebase is clean
- Key architectural comments:
  - `config_engine.py:3-12` — Two-file resolution rationale
  - `gate.sh:8-22` — Invariant protection mechanism
  - `jest_purlin.js:1-16` — Proof collection docstring
  - `shell_purlin.sh:54` — Feature-scoped overwrite strategy
  - `purlin_server.py:31-41` — Proof file regex patterns

## Test Tier Flags

| Module | Default Tier | Notes |
|--------|-------------|-------|
| mcp-server | unit | Git subprocess mocked in tests |
| config-engine | unit | Temp fixture dirs only |
| proof-pytest | unit | pytest invocation in fixture |
| proof-jest | unit | Node.js + glob required |
| proof-shell | unit | Python sub-invocation |
| gate-hook | unit | Temp fixture dirs |
| session-start | unit | Temp fixture dirs |
| Skills (workflow) | manual | Interactive Q&A, agent-driven |
| skill-verify/unit-test | e2e/slow | Run full test suites |
| skill-changelog/invariant | slow | Git subprocess, possible network |
| skill-status/find/config/help | unit | MCP call or static |
