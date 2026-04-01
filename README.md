<p align="center">
  <img src="assets/purlin-logo.svg" alt="Purlin" width="400">
</p>

# Purlin

[Documentation](docs/index.md)

**Rule-Proof Spec-Driven Development**

- Write better code through proof-based specs
- Prove spec / code drift with signed verification
- Enable multi-discipline collaboration with smart changelogs and remote invariant specs that cannot be adjusted during development

## How It Works

1. **Specs** define what your code must do. Each spec has rules (testable constraints) and proofs (observable assertions).
2. **Proof markers** in your tests link test cases to spec rules. Test runners emit proof files automatically.
3. **`sync_status`** reads specs and proof files, diffs them, and tells you exactly what to do next via `→` directives.

```
auth_login: 2/3 rules proved
  RULE-1: PASS (PROOF-1 in tests/test_login.py)
  RULE-2: PASS (PROOF-2 in tests/test_login.py)
  RULE-3: NO PROOF
  → Fix: write a test with @pytest.mark.proof("auth_login", "PROOF-3", "RULE-3")
  → Run: purlin:unit-test
```

## Install

**Prerequisites:** git, Python 3.8+, [Claude Code](https://docs.anthropic.com/en/docs/claude-code)

```bash
# Add as a Claude Code plugin
claude plugin install purlin
```

## Initialize a Project

```
purlin:init
```

This creates `.purlin/`, `specs/`, detects your test framework, and scaffolds the proof plugin.

## Write a Spec

```
purlin:spec auth_login
```

Specs use a 3-section format:

```markdown
# Feature: auth_login

> Scope: src/auth/login.js

## What it does
Handles user authentication via username/password and SSO.

## Rules
- RULE-1: Return 200 with session token on valid credentials
- RULE-2: Return 401 on invalid credentials
- RULE-3: SSO redirects to provider URL

## Proof
- PROOF-1 (RULE-1): POST valid creds returns 200 + token
- PROOF-2 (RULE-2): POST bad creds returns 401
- PROOF-3 (RULE-3): GET /sso redirects to provider
```

## Add Proof Markers to Tests

**pytest:**
```python
@pytest.mark.proof("auth_login", "PROOF-1", "RULE-1")
def test_valid_login():
    resp = client.post("/login", json={"user": "alice", "pass": "secret"})
    assert resp.status_code == 200
    assert "token" in resp.json()
```

**Jest:**
```javascript
it("returns 200 on valid login [proof:auth_login:PROOF-1:RULE-1:default]", async () => {
  const resp = await post("/login", { user: "alice", pass: "secret" });
  expect(resp.status).toBe(200);
  expect(resp.body.token).toBeDefined();
});
```

## Check Coverage

```
purlin:status
```

The `sync_status` MCP tool scans specs and proof files, then reports coverage with actionable `→` directives.

## Verify Everything

```
purlin:verify
```

Runs ALL tests, issues verification receipts for every feature with 100% rule coverage.

## 13 Skills

| Skill | Purpose |
|-------|---------|
| `purlin:spec` | Create/edit specs |
| `purlin:build` | Implement from spec rules |
| `purlin:verify` | Run all tests, issue receipts |
| `purlin:unit-test` | Run tests, emit proof files |
| `purlin:status` | Show coverage + directives |
| `purlin:changelog` | PM-readable summary of changes |
| `purlin:init` | Initialize project |
| `purlin:invariant` | Sync external constraints |
| `purlin:find` | Search specs |
| `purlin:config` | Read/write settings |
| `purlin:spec-from-code` | Generate specs from code |
| `purlin:help` | Command reference |
| `purlin:worktree` | Worktree management |

Skills are **optional** — you can write specs, code, and tests without invoking any skill. Skills provide scaffolding and workflow automation.

## Hard Gates (only 2)

1. **Invariant protection** — `specs/_invariants/i_*` files are read-only. Use `purlin:invariant sync` to update.
2. **Proof coverage** — `purlin:verify` won't issue a receipt unless every rule has a passing proof.

Everything else is optional guidance.

## Architecture

```
.purlin/
  config.json             # Project settings
  plugins/                # Proof plugin (scaffolded by init)
specs/
  <category>/
    <feature>.md          # Feature specs (3-section format)
    <feature>.proofs-*.json  # Proof files (emitted by test runners)
    <feature>.receipt.json   # Verification receipts
  _invariants/
    i_<prefix>_<name>.md  # Read-only external constraints
```

**MCP Server:** `scripts/mcp/purlin_server.py` — provides `sync_status` and `purlin_config` tools.
**Gate Hook:** `scripts/gate.sh` — blocks writes to invariant files.
**Proof Plugins:** `scripts/proof/` — pytest, Jest, and shell proof collectors.
