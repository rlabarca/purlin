# Installation and Quick Start

## Quick Start

Already installed? Here's the whole workflow:

```
write a spec for login                    ← describe what the feature must do
build login                               ← code + tests, iterates until VERIFIED
/purlin:verify                            ← verification receipt committed
```

Three messages. Spec → code → ship. Everything else is detail.

---

## Prerequisites

- git
- Python 3.8+
- [Claude Code](https://docs.anthropic.com/en/docs/claude-code)

## Set Up a Project

Your project must be a git repository. Purlin uses git for verification receipts, manual proof stamps, drift detection, and commit-based staleness detection.

```bash
# New project
mkdir my-project && cd my-project
git init

# Existing project — just cd into it
cd my-project
```

Add the Purlin marketplace from your terminal (this is a CLI command, not inside Claude Code):

```bash
claude plugin marketplace add git@bitbucket.org:rlabarca/purlin.git --scope project
```

The `--scope project` flag stores the marketplace config in the project directory (`.claude/settings.json`) so every team member who clones the repo gets Purlin automatically. Omit it for a user-level install that only applies to you.

Then start Claude Code and install the plugin:

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

Then initialize the Purlin workspace:

```
purlin:init
```

This does 5 things:

1. **Creates `.purlin/`** — config directory with `config.json` (team defaults) and `config.local.json` (per-user overrides, gitignored).
2. **Creates `specs/`** -- directory for spec files, with a `_anchors/` subdirectory for cross-cutting constraints with external references.
3. **Scaffolds proof plugin** — detects your test framework (pytest, Jest, or shell) and installs the appropriate proof collector so tests emit `*.proofs-*.json` files.
4. **Installs pre-push hook** — a git hook that runs tests before push. You choose warn mode (block on failures, warn on partial) or strict mode (block unless all features are VERIFIED).
5. **Configures audit criteria** — built-in criteria always apply. Optionally add team-specific criteria from a git-hosted file (appended to built-in defaults). See [references/audit_criteria.md](../references/audit_criteria.md).

### Proof Plugin Setup by Framework

**pytest** — Adds `conftest.py` that imports the proof plugin:
```python
pytest_plugins = [".purlin/plugins/pytest_purlin"]
```

**Jest** — Adds the reporter to `jest.config.js`:
```javascript
reporters: ["default", ".purlin/plugins/jest_purlin.js"]
```

**Shell** — Source the harness in your test scripts:
```bash
source .purlin/plugins/purlin-proof.sh
```

## Config System

Purlin uses a two-file config system:

- **`.purlin/config.json`** — committed, team defaults
- **`.purlin/config.local.json`** — gitignored, per-user overrides

Resolution: `config.json` is the base layer. `config.local.json` overrides on top — local keys win for any key present in both. Keys only in `config.json` (like new framework defaults) are always visible. `config.local.json` should be sparse — only override what you need.

Default config:
```json
{
  "version": "0.9.0",
  "test_framework": "auto",
  "spec_dir": "specs",
  "report": true
}
```

The HTML dashboard is enabled by default (`"report": true`). When enabled, `purlin:status` writes `.purlin/report-data.js` on every call, and `purlin:init` creates a `purlin-report.html` symlink at the project root. Open it in a browser to see live coverage. Toggle with `purlin:init --report`. See the [Dashboard Guide](dashboard-guide.md) for details.

Read or update config with the `purlin_config` MCP tool, or edit the files directly.

## What Gets Created

```
your-project/
  .purlin/
    config.json            # Team defaults
    config.local.json      # Per-user (gitignored)
    plugins/               # Proof collector for your test framework
  specs/
    _anchors/              # Cross-cutting constraints (optionally synced from external sources)
  .gitignore               # Updated with Purlin entries
```

## Changing Settings After Init

Already initialized? Use `purlin:init --force` to reconfigure, or change individual settings:

| What you want | How |
|---------------|-----|
| Switch pre-push mode (warn/strict) | `purlin:init --pre-push` |
| Toggle HTML dashboard | `purlin:init --report` |
| Add a proof plugin | `purlin:init --add-plugin ./my-plugin.py` |
| See installed plugins | `purlin:init --list-plugins` |
| Set external audit criteria | `purlin:init --sync-audit-criteria` |
| Change audit LLM (experimental) | `purlin:init --audit-llm` |
| Re-run full setup | `purlin:init --force` |

## Scaling

Purlin uses the filesystem as its state — specs are Markdown files, proofs are JSON files next to specs. `purlin:status` scans both on every call. This is intentional: zero infrastructure, zero dependencies, works offline, nothing to configure.

**What this means for project size:**

| Project size | Specs | Scan time | Experience |
|---|---|---|---|
| Small (startup, side project) | 5-20 | <100ms | Instant |
| Medium (team product) | 20-50 | <500ms | Fast |
| Large (multi-team) | 50-100 | <1s | Fine |
| Very large (monorepo, 100+) | 100+ | Seconds | Consider splitting |

Purlin is designed for projects with up to ~100 feature specs. If your project grows beyond this:

- **Split by domain:** create separate `specs/` directories per team or service, each with its own Purlin workspace
- **Use git worktrees:** each worktree has independent proof files, reducing merge conflicts

If `purlin:status` becomes noticeably slow, the project has likely outgrown a single spec directory.

## Updating Purlin

From the terminal:

```bash
claude plugin marketplace update
```

Or inside Claude Code:

```
/plugin marketplace update
```

Both pull the latest version. Existing specs, proofs, and config are preserved.

## Upgrading from an Older Version of Purlin

If you have a pre-0.9.0 Purlin installation (with `features/`, companion files, sync ledger, etc.):

**Keep your old `features/` directory.** `purlin:spec-from-code` reads your existing specs and uses them as migration context — old scenarios and rules are preserved in the new format. Don't throw away work you've already done.

Remove only the non-spec artifacts:

```bash
rm -rf .purlin/ pl-* *.sh
```

This removes:
- `.purlin/` — old config and state files (regenerated by `purlin:init`)
- `pl-*` — old symlinks at project root
- `*.sh` — old shell scripts at project root

Then initialize and migrate:

```
purlin:init
purlin:spec-from-code
```

`purlin:spec-from-code` detects existing specs in any format — `features/` (pre-0.9.0) or non-compliant specs already in `specs/` — and migrates them to the current format. Your existing rules and descriptions are preserved as the primary input. Migration candidates are annotated `(migrating)` in the taxonomy review. After migration from `features/`, the skill offers to clean up the old directory.

## Adding More Proof Plugins

Purlin ships with proof plugins for Python (pytest), JavaScript (Jest), and Bash (shell). If your project uses another language or framework, you can add a community or custom proof plugin.

Proof plugins read proof markers from your tests and write the JSON files that Purlin reads for coverage reporting. See the [Testing Workflow Guide](testing-workflow-guide.md#proof-plugins) for details on what they are and how they work.

```
purlin:init --add-plugin ./my-go-plugin.py
purlin:init --add-plugin git@github.com:someone/purlin-rust-proof.git
```

Plugins are installed to `.purlin/plugins/` and work immediately. To see what's installed:

```
purlin:init --list-plugins
```
