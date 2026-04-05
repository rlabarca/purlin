<p align="center">
  <img src="assets/purlin-logo.svg" alt="Purlin" width="400">
</p>

# Purlin

[Documentation](docs/index.md)

**Rule-Proof Spec-Driven Development**

- Write better code through proof-based specs
- Prove spec / code drift with signed verification
- Enable multi-discipline collaboration with drift detection and anchor specs with external references

## Quick Start

After [installing Purlin](docs/installation-guide.md):

```
write a spec for login       ← describe what the feature must do
build login                  ← code + tests written, iterates until all rules pass
/purlin:verify               ← verification receipt committed — ship it
```

Three messages. Spec → code → ship.

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

From your terminal:

```bash
cd my-project
git init                # required -- Purlin needs git for proofs, receipts, and drift detection
claude plugin marketplace add git@bitbucket.org:rlabarca/purlin.git --scope project
```

The `--scope project` flag stores the marketplace in the project so teammates get it automatically when they clone. Omit it for user-level install.

Then start Claude Code and install:

```bash
claude
```

```
/plugin install purlin@purlin
```

Exit and restart Claude Code for skill autocomplete to take effect:
```bash
exit
claude
```

## Initialize a Project

```
purlin:init
```

This creates `.purlin/`, `specs/`, detects your test framework, and scaffolds the proof plugin.

### Upgrading from an older version of Purlin

If you have a pre-0.9.0 Purlin installation, keep your `features/` directory — `spec-from-code` migrates your old specs to the new format. Remove only the non-spec artifacts:

```bash
rm -rf .purlin/ pl-* *.sh
```

Then initialize and migrate:

```
purlin:init
purlin:spec-from-code
```

Your old scenarios and rules are preserved as input for the new-format specs. See the [Installation Guide](docs/installation-guide.md#upgrading-from-an-older-version-of-purlin) for details.

## Write a Spec

```
purlin:spec auth_login
```

Specs use a 3-section format:

```markdown
# Feature: auth_login

> Description: Handles user authentication via username/password and SSO.
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

## Build and Test

Just ask Claude. The agent writes code, adds proof markers to tests, and iterates until all rules pass:

```
build auth_login
```

Or even simpler:

```
test auth_login
```

Claude reads the spec, writes code if needed, writes tests with proof markers, runs them, and iterates until `sync_status` shows VERIFIED. You don't need to write proof markers yourself -- the agent does it.

Under the hood, proof markers link each test to a spec rule. The test framework plugin collects the results and emits proof files that `sync_status` reads. See the [Testing Workflow Guide](docs/testing-workflow-guide.md) for details on how proof markers work, manual proofs, tiers, and writing custom proof plugins.

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

## Skills

| Skill | Purpose |
|-------|---------|
| `purlin:spec` | Create/edit specs |
| `purlin:build` | Implement from spec rules |
| `purlin:verify` | Run all tests, issue receipts |
| `purlin:unit-test` | Run tests, emit proof files |
| `purlin:audit` | Evaluate proof quality |
| `purlin:status` | Show coverage + directives |
| `purlin:drift` | Drift detection and change summary |
| `purlin:init` | Initialize project |
| `purlin:anchor` | Sync external constraints |
| `purlin:find` | Search specs |
| `purlin:rename` | Rename feature across artifacts |
| `purlin:spec-from-code` | Generate specs from code |


Skills are **optional** -- you can write specs, code, and tests without invoking any skill. Skills provide scaffolding and workflow automation.

## Hard Gate (only 1)

1. **Proof coverage** -- `purlin:verify` won't issue a receipt unless every rule has a passing proof.

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
  _anchors/
    <name>.md             # Cross-cutting constraints (optionally synced from external sources)
```

**MCP Server:** `scripts/mcp/purlin_server.py` -- provides `sync_status` and `purlin_config` tools.
**Proof Plugins:** `scripts/proof/` -- pytest, Jest, and shell proof collectors.
