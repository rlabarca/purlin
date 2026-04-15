<p align="center">
  <img src="assets/purlin-logo.svg" alt="Purlin" width="400">
</p>

# Purlin

[Documentation](docs/index.md)

**Rule-Proof Spec-Driven Development**

Purlin is a Claude Code plugin that adds spec-driven development to your workflow. You use Claude exactly as you normally would — Purlin just gives it a structured way to track what your code should do, prove that it does it, and tell you what's missing.

## Install

**Prerequisites:** git, Python 3.8+, [Claude Code](https://docs.anthropic.com/en/docs/claude-code)

```bash
cd my-project
git init                # required — Purlin needs git
claude plugin marketplace add git@bitbucket.org:boomerangdev/purlin.git --scope project
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

Then initialize:

```
purlin:init
```

This creates `.purlin/`, `specs/`, detects your test framework, scaffolds the proof plugin, and installs git hooks.

## What a Session Looks Like

You don't need to learn a new workflow. You just use Claude Code as usual. Here's what a typical session looks like:

**If you have an existing codebase**, generate specs from your code:

```
purlin:spec-from-code
```

**Day-to-day work** — use any combination of these as you go:

```
purlin:spec auth_login     ← define what a feature must do
purlin:build auth_login    ← Claude writes code + tests, iterates until rules pass
purlin:verify              ← sign off — verification receipts committed
```

**See what needs attention:**

```
purlin:status              ← coverage table with → directives telling you what to do next
purlin:drift               ← what changed since last verification, who needs to act
```

You can tell Claude to handle the items that come back from status and drift — they're actionable directives, not just reports.

**Check test quality** (expensive — don't run every session):

```
purlin:audit               ← evaluates whether your tests actually prove what they claim
```

**Visual dashboard** — `purlin:status` prints a dashboard link at the bottom. Open it in your browser for a visual view of coverage and test quality. You don't need to use it — the CLI output has everything — but it's there if you want it.

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

## How It Works

1. **Specs** define what your code must do. Each spec has rules (testable constraints) and proofs (observable assertions).
2. **Proof markers** in your tests link test cases to spec rules. Test runners emit proof files automatically.
3. **`sync_status`** reads specs and proof files, diffs them, and tells you exactly what to do next.

```
auth_login: 2/3 rules proved
  RULE-1: PASS (PROOF-1 in tests/test_login.py)
  RULE-2: PASS (PROOF-2 in tests/test_login.py)
  RULE-3: NO PROOF
  → Fix: write a test with @pytest.mark.proof("auth_login", "PROOF-3", "RULE-3")
  → Run: purlin:unit-test
```

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

Skills are **optional** — you can write specs, code, and tests without invoking any skill. Skills provide scaffolding and workflow automation.

## Stakeholder Tools

The `tools/` directory contains skills for non-engineer stakeholders who interact with Purlin projects through Claude Desktop. These don't require a development environment — just a repo URL.

| Tool | Audience | What it does |
|------|----------|-------------|
| `tools/QA/purlin-qa-report` | QA | Fetches project digest, produces triaged HTML report of failures, drift, test quality, manual tests due, and sign-off readiness |
| `tools/PM/purlin-anchor-userstories` | Product | Creates and maintains user story anchor files that drive spec-driven development |

Install these as Claude Desktop skills (drag the `.skill` file or paste the `.md` contents into project instructions). They clone the repo, read the project digest, and produce visual reports — no dev tools needed.

## Hard Gate (only 1)

1. **Proof coverage** — `purlin:verify` won't issue a receipt unless every rule has a passing proof.

Everything else is optional guidance.

## Architecture

```
.purlin/
  config.json             # Project settings
  report-data.js          # Project digest (auto-generated on commit)
  plugins/                # Proof plugin (scaffolded by init)
specs/
  <category>/
    <feature>.md          # Feature specs (3-section format)
    <feature>.proofs-*.json  # Proof files (emitted by test runners)
    <feature>.receipt.json   # Verification receipts
  _anchors/
    <name>.md             # Cross-cutting constraints (optionally synced from external sources)
tools/
  QA/                     # QA report skill for Claude Desktop
  PM/                     # Product anchor skill for Claude Desktop
```

**MCP Server:** `scripts/mcp/purlin_server.py` — provides `sync_status`, `drift`, and `purlin_config` tools.
**Proof Plugins:** `scripts/proof/` — pytest, Jest, and shell proof collectors.
**Git Hooks:** `scripts/hooks/` — pre-push (coverage check) and pre-commit (digest auto-generation).
