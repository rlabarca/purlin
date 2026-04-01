# SFC Inventory — Purlin Framework

## Directory Map

```
scripts/                          # Consumer-facing framework tooling (distributed contract)
├── mcp/                          # MCP server implementation
│   ├── __init__.py              # Package marker
│   ├── purlin_server.py         # Main MCP stdio server (809 lines)
│   ├── config_engine.py         # Config resolution engine (144 lines)
│   └── manifest.json            # MCP tool definitions (3 tools)
├── proof/                        # Proof plugins for test frameworks
│   ├── pytest_purlin.py         # Pytest proof plugin
│   ├── jest_purlin.js           # Jest proof reporter
│   └── shell_purlin.sh          # Shell proof harness
├── gate.sh                       # PreToolUse hook — blocks invariant writes
└── session-start.sh              # SessionStart hook — clears runtime locks

agents/
└── purlin.md                     # Main agent definition (spec-driven dev assistant)

skills/                           # 12 Claude Code skills
├── init/SKILL.md                # Initialize project
├── spec/SKILL.md                # Scaffold/edit specs
├── spec-from-code/SKILL.md      # Reverse-engineer specs from code
├── build/SKILL.md               # Implement from spec rules
├── verify/SKILL.md              # Run tests, issue receipts
├── unit-test/SKILL.md           # Run tests, emit proofs
├── status/SKILL.md              # Show coverage via sync_status
├── changelog/SKILL.md           # Summarize changes
├── find/SKILL.md                # Search specs by name
├── config/SKILL.md              # Read/write config
├── invariant/SKILL.md           # Sync external constraints
└── help/SKILL.md                # Command reference
```

## Tech Stack

- **Python 3** (stdlib only) — MCP server, config engine, pytest plugin
- **Bash** — hooks, gates, shell proof harness
- **JavaScript** — Jest proof reporter
- **Markdown** — specs, agent definition, skill definitions
- **MCP (Model Context Protocol)** — stdio JSON-RPC 2.0 transport
- **Git** — changelog generation, staleness detection
- **No external dependencies** — entire framework runs on stdlib

## Preliminary Feature Candidates

### MCP Server
1. **sync_status tool** — scans specs + proofs, produces coverage report with directives
2. **changelog tool** — git-based diff summary with file classification and spec change detection
3. **purlin_config tool** — read/write config via MCP
4. **config engine** — two-file resolution (local > shared), copy-on-first-access
5. **MCP transport** — JSON-RPC 2.0 stdio server, tool dispatch

### Proof Plugins
6. **pytest proof plugin** — collects @pytest.mark.proof markers, emits feature-scoped JSON
7. **jest proof reporter** — parses [proof:...] from test names, emits JSON
8. **shell proof harness** — bash functions for proof registration + finish

### Hooks
9. **gate hook (invariant protection)** — blocks writes to specs/_invariants/i_* without lock
10. **session-start hook** — clears stale runtime locks on session start

## Cross-Cutting Concerns

- **Spec format** — 3-section (What it does, Rules, Proof) used across all features
- **Proof file schema** — standard JSON format emitted by all 3 proof plugins
- **Feature-scoped overwrite** — all proof plugins purge old entries, write fresh ones
- **Invariant protection** — gate hook + lock file pattern spans hooks and skills
- **Config resolution** — two-file pattern used by MCP server and skills
- **Verification receipts** — vhash computation used by verify skill + sync_status

## Code Comments Index

- **No TODO/FIXME/HACK comments found** in scanned directories
- **Module docstrings present** in all Python files and JS file
- **Architectural decisions** documented in CLAUDE.md (hook stderr requirement, tool folder separation)
