# Installation and Quick Start

## Quick Start

Already installed? Here's the whole workflow:

```
write a spec for login                    ← describe what the feature must do
build login                               ← code + tests, iterates until all rules pass
/purlin:verify                            ← verification receipt committed
```

Three messages. Everything else is detail.

That is the shortest path, not the only one. Purlin reads what exists rather than imposing an
order. You can also perfect a spec's proof descriptions first and grade them with
`purlin:audit --design` before any code is written. That is worth doing: a vague proof
description caps what the eventual test can prove.

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

# Existing project: cd into it
cd my-project
```

Add the Purlin marketplace from your terminal (this is a CLI command, not inside Claude Code):

```bash
claude plugin marketplace add https://github.com/rlabarca/purlin.git --scope project
```

The `--scope project` flag stores the marketplace config in the project directory (`.claude/settings.json`) so every team member who clones the repo gets Purlin automatically. Omit it for a user-level install that only applies to you.

Already added `purlin` using the SSH URL (`git@github.com:...`)? Run `claude plugin marketplace remove purlin` first, then the command above. The name `purlin` stays bound to whichever URL it was added with.

Then start Claude Code and install the plugin:

```bash
claude
```

```
/plugin install purlin@purlin
```

Reload plugins so skill autocomplete takes effect:

```
/reload-plugins
```

Then initialize the Purlin workspace:

```
purlin:init
```

This does 7 things:

1. **Creates `.purlin/`**: the config directory, with `config.json` for team defaults. `config.local.json` holds per-user overrides. It is gitignored by the block init writes, and it is created the first time something overrides a key.
2. **Creates `specs/`**: the directory for spec files, with a `_anchors/` subdirectory for cross-cutting constraints and external references.
3. **Scaffolds the proof plugin**: it detects your test framework (pytest, Jest, Vitest, C, PHP or SQL, see [supported frameworks](../references/supported_frameworks.md)) and installs the matching proof collector, so tests emit `*.proofs-*.json` files. The selection list offers every shipped plugin, including the ones with no auto-detection (shell) and the one with manual setup (xUnit for .NET).
4. **Verifies the MCP server**: the server carrying the `sync_status`, `purlin_config` and `drift` tools ships with the plugin and registers itself wherever the plugin is enabled, always at the installed plugin version. A project initialized before v0.9.4 carries a legacy version-pinned `purlin` entry in `.mcp.json` that shadows the bundled server, and init removes it. See [Upgrading the plugin](#upgrading-the-plugin), which owns every migration an older project needs.
5. **Installs the pre-push hook**: a git hook that runs tests before a push. Choose warn mode (block on failures, warn on partial coverage) or strict mode (block unless every feature is VERIFIED).
6. **Installs the pre-commit hook for the project digest**: it regenerates `.purlin/report-data.js`, the coverage and drift data, on every commit, so stakeholders see the current status without running Purlin tools. The modes are `auto` (default), `warn` and `off`.

The plugin also carries a Claude Code hook (`hooks/hooks.json`) that refreshes the same digest in the background after any tool call or turn that changed a spec, proof, receipt, gauge cache or the config, so the dashboard keeps up while agents work without anyone calling `purlin:status`. It needs no installation step: it comes with the plugin, honours `report` and `digest` in `.purlin/config.json` (`report: false` or `digest: off` disables it), never blocks, never prints, and never reaches the network.
7. **Configures audit criteria**: the built-in criteria always apply and cover both quality gauges. You can add team criteria from a git-hosted file, appended to the built-in ones. See [references/audit_criteria.md](../references/audit_criteria.md).

The skill asks the questions; `scripts/init/scaffold.py` writes the files and prints one line per path it wrote, kept, copied or linked, so what init did is on screen rather than inferred from the tree.

### Proof Plugin Setup by Framework

**pytest.** Adds a `conftest.py` that loads the proof plugin. `.purlin` is not an importable package name, so the plugin directory goes on `sys.path` and the plugin is named as a module:
```python
import os
import sys

sys.path.insert(0, os.path.join(
    os.path.dirname(os.path.abspath(__file__)), ".purlin", "plugins"))

pytest_plugins = ["pytest_purlin"]
```

**Jest.** Adds the reporter to `jest.config.js` or `package.json`:
```javascript
reporters: ["default", ".purlin/plugins/jest_purlin.js"]
```

**Vitest.** Adds the TypeScript reporter to `vitest.config.ts`. Vitest loads `.ts` reporters natively, so do not reuse the Jest reporter:
```typescript
test: { reporters: ['default', '.purlin/plugins/vitest_purlin.ts'] }
```

**Shell.** Source the harness in your test scripts:
```bash
source .purlin/plugins/shell_purlin.sh
```

**xUnit (.NET).** Manual setup. Compile `xunit_purlin.cs` into an assembly named `Purlin.TestLogger` (the .NET test platform only discovers loggers from `*TestLogger.dll` assemblies), reference it from your test project, then run:
```bash
dotnet test --logger purlin -- RunConfiguration.CollectSourceInformation=true
```
Full wiring steps: [references/formats/proofs_format.md](../references/formats/proofs_format.md).

## Config System

Purlin uses a two-file config system:

- **`.purlin/config.json`**: committed, team defaults
- **`.purlin/config.local.json`**: gitignored, per-user overrides

Resolution: `config.json` is the base layer and `config.local.json` overrides on top, so a local key wins for any key present in both. A key that only `config.json` carries, such as a new framework default, is always visible. Keep `config.local.json` sparse: override only what you need.

Default config (`version` is set from the installed framework's `VERSION` file at init time):
```json
{
  "version": "<installed version>",
  "test_framework": "auto",
  "spec_dir": "specs",
  "pre_push": "warn",
  "remote_verification": "off",
  "mutation_checks": false,
  "report": true,
  "digest": "auto"
}
```

`mutation_checks` is off by default. When it is on, every new or amended proof is mutation-checked before the commit that carries it: break the behaviour, watch the proof fail, restore. It is the only check that catches a proof which passes against broken code, and it costs roughly twice the tokens and minutes per proof; see [spec_quality_guide.md § Mutation check](../references/spec_quality_guide.md#mutation-check). `purlin:init` asks; `purlin:init --mutation-checks on|off` changes it later.

Two further fields are optional and `purlin:init` never writes them. `platforms` is the registry the `@on(<platform-id>)` proof tags resolve against; the family ids `windows`, `macos` and `linux` work with no config at all, and an entry is what adds a version, an architecture or a runner:

```json
{
  "platforms": {
    "windows-2022": {
      "os": "windows",
      "version": ">=10.0.20348",
      "arch": "x86_64",
      "runner": { "provider": "github", "runs_on": "windows-2022", "workflow": "purlin-windows-2022-proofs" }
    },
    "figma-mcp": { "kind": "environment", "label": "a host with the Figma MCP server configured" }
  }
}
```

A proof can depend on a platform, on an environment or on a prerequisite, and each one has its own mechanism. The rule set has a single home: [references/remote_verification.md](../references/remote_verification.md), section "Platforms, environments and prerequisites". For the registry itself see [Testing Workflow Guide § Platforms](testing-workflow-guide.md#platforms). `audit_llm` and `audit_criteria` are the cross-model and compliance-criteria fields; see [Regulated Environments](regulated-environments.md).

The HTML dashboard is enabled by default (`"report": true`). When enabled, `purlin:status` writes `.purlin/report-data.js` on every call, and `purlin:init` creates a `purlin-report.html` symlink at the project root. Open it in a browser to see live coverage. Toggle with `purlin:init --report`. See the [Dashboard Guide](dashboard-guide.md) for details.

Read or update config with the `purlin_config` MCP tool, or edit the files directly.

## What Gets Created

```
your-project/
  .purlin/
    config.json            # Team defaults
    config.local.json      # Per-user (gitignored)
    plugins/               # Proof collector for your test framework
    report-data.js         # Project digest (committed, regenerated by pre-commit hook)
  specs/
    _anchors/              # Cross-cutting constraints (optionally synced from external sources)
  .gitignore               # Updated with Purlin entries
  purlin-report.html       # Dashboard symlink (gitignored, if report enabled)
  .git/hooks/pre-push      # Proof coverage check
  .git/hooks/pre-commit    # Digest regeneration
```

## Changing Settings After Init

Already initialized? Use `purlin:init --force` to reconfigure, or change individual settings:

| What you want | How |
|---------------|-----|
| Switch pre-push mode (warn/strict/off) | `purlin:init --pre-push` |
| Turn mutation checks on or off | `purlin:init --mutation-checks on\|off` |
| Migrate the project to the installed plugin | `purlin:init --update` |
| Toggle HTML dashboard | `purlin:init --report` |
| Change digest mode (auto/warn/off) | `purlin:init --digest` |
| Add a proof plugin | `purlin:init --add-plugin ./my-plugin.py` |
| See installed plugins | `purlin:init --list-plugins` |
| Set external audit criteria | `purlin:init --sync-audit-criteria` |
| Change audit LLM (experimental) | `purlin:init --audit-llm` |
| Re-run full setup | `purlin:init --force` |

## Scaling

The filesystem is Purlin's state. Specs are Markdown files and proofs are JSON files beside them. `purlin:status` scans both on every call. That is deliberate: no infrastructure, no dependencies, it works offline and there is nothing to configure.

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

## Upgrading the plugin

After `claude plugin marketplace update`, the plugin has moved and the project has not. Run:

```
purlin:init --update
```

It detects what is pending from the project's own contents (never from the `version` field), shows the delta, asks before writing anything, and then migrates:

| Migration | What it does |
|---|---|
| `legacy-tier-windows` | Rewrites `@windows` proof tags to `@unit @on(<platform-id>)` |
| `legacy-proof-file` | `git mv`s `<feature>.proofs-windows.json` to `<feature>.proofs-unit@<platform-id>.json` and stamps `platform` on it |
| `legacy-marker` | Rewrites every plugin's `windows`-tier proof marker to tier `unit` plus the platform |
| `plugin-copies-stale` | Replaces each `.purlin/plugins/` copy with the installed plugin's file |
| `config-fields-missing` | Fills config fields from the template and stamps `version` from the installed `VERSION` |
| `receipt-v1` | Prints `→ Run: purlin:verify`. A receipt is a claim that tests ran, so the update never writes one |
| `legacy-mcp` | Removes the legacy `purlin` entry from `.mcp.json` (this is what `purlin:init --mcp` runs on its own), then `/reload-plugins` |

`purlin:init --update --check` reports what is pending and writes nothing; it is also what a CI preflight runs, so a runner never proves anything with stale plugin copies. `purlin:init --update --platform-id <id>` says what a legacy `@windows` tag becomes (default: the `windows` OS family). Every skill points at the same advisory: when `purlin:status` or any other skill opens with a pending-migrations block, that is this command asking to be run.

The update never scaffolds a runner and never issues a receipt. Registering a platform and writing its workflow is `purlin:test`'s consent path; receipts come from `purlin:verify` after a fresh run.

## Upgrading from an Older Version of Purlin

If you have a pre-0.9.0 Purlin installation (with `features/`, companion files, sync ledger, etc.):

**Keep your old `features/` directory.** `purlin:spec-from-code` reads your existing specs and uses them as migration context, so old scenarios and rules survive in the new format. Do not throw away work you have already done.

Remove old artifacts that are now managed by the plugin system:

```bash
rm -rf .purlin/ pl-* *.sh
rm -rf .claude/commands/
rm -f .claude/agents/purlin-*.md
```

This removes:
- `.purlin/`: old config and state files, regenerated by `purlin:init`
- `pl-*`: old symlinks at the project root
- `*.sh`: old shell scripts at the project root
- `.claude/commands/`: old command definitions, now provided by the plugin
- `.claude/agents/purlin-*.md`: old project-local agent definitions. The independent auditor ships with the plugin as `purlin:purlin-auditor`; the former `purlin-builder` and `purlin-reviewer` are retired

Then initialize and migrate:

```
purlin:init
purlin:spec-from-code
```

`purlin:spec-from-code` detects existing specs in any format, whether in `features/` (pre-0.9.0) or non-compliant specs already in `specs/`, and migrates them to the current format. Your existing rules and descriptions are preserved as the primary input. Migration candidates are annotated `(migrating)` in the taxonomy review. After migration from `features/`, the skill offers to clean up the old directory.

## Adding More Proof Plugins

Purlin ships proof plugins for Python (pytest), JavaScript and TypeScript (Jest, Vitest), .NET (xUnit for C#, F# and VB.NET), C, PHP, SQL and Bash. See [supported frameworks](../references/supported_frameworks.md). If your project uses another language or framework, add a community or custom proof plugin.

Proof plugins read proof markers from your tests and write the JSON files that Purlin reads for coverage reporting. See the [Testing Workflow Guide](testing-workflow-guide.md#proof-plugins) for details on what they are and how they work.

```
purlin:init --add-plugin ./my-go-plugin.py
purlin:init --add-plugin git@github.com:someone/purlin-rust-proof.git
```

Plugins are installed to `.purlin/plugins/` and work immediately. To see what's installed:

```
purlin:init --list-plugins
```
