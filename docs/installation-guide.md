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
- A Python 3.8 or newer interpreter reachable on `PATH` as `python3`, `python` or `py`. Purlin tries those three names in that order and accepts a `python` only when it reports major version 3, so a Python 2 under that name is skipped rather than run. Set `PURLIN_PYTHON` to the interpreter's path when your host carries it under none of those names, or when the first name found is not the one you want: it is tried before all three
- `sh` on `PATH`. Every git hook and the MCP server are launched through it, and it is what runs the interpreter lookup above. macOS and Linux ship it; on Windows, Git for Windows provides it
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

The `--scope project` flag stores the marketplace config in the project directory (`.claude/settings.json`) so every team member who clones the repo resolves the plugin from the same source. It does not install the plugin for them. Each team member still runs the three steps below in their own checkout: `/plugin install purlin@purlin`, then `/reload-plugins`, then `purlin:init --force`, which writes their own git hooks and their own gitignored copy of the dashboard. Omit it for a user-level install that only applies to you.

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
5. **Installs the pre-push hook**: a git hook that runs tests before a push. Choose warn mode (block on failures, warn on partial coverage) or strict mode (block unless every feature is VERIFIED). Both hooks install the same way, in two parts. The body is a generated shim at `.purlin/hooks/<name>`, tracked in git because it names no machine and no plugin version: it finds the installed plugin at run time and runs that plugin's hook script, so a plugin update changes the hook and nothing in the project is rewritten. The file git itself runs is a three-line delegator to that shim, written into the hooks directory git reads, which is `core.hooksPath` when your repository sets one and the repository's common hooks directory otherwise, so a linked worktree gets a hook that runs. Every hook path ends in one of five outcomes and init prints which: the shim is **wrote** or **kept**, the delegator is **wrote** into a free slot, **kept** when Purlin's delegator is already there, and **skipped** when the slot holds anything else. A hook you or a manager put there is never written over. If husky, lefthook or the pre-commit framework owns your hooks, init names the manager and prints the one line to add to its hook, for example `exec "$(git rev-parse --show-toplevel)/.purlin/hooks/pre-push" "$@"` in `.husky/pre-push`.
6. **Installs the pre-commit hook for the project digest**: it regenerates `.purlin/report-data.js`, the coverage and drift data, on every commit, so stakeholders see the current status without running Purlin tools. The modes are `auto` (default), `warn` and `off`.
7. **Configures audit criteria**: the built-in criteria always apply and cover both quality gauges. You can add team criteria from a git-hosted file, appended to the built-in ones. See [references/audit_criteria.md](../references/audit_criteria.md).

The plugin also carries a Claude Code hook (`hooks/hooks.json`) that refreshes the same digest in the background after any tool call or turn that changed a spec, proof, receipt, gauge cache or the config, so the dashboard keeps up while agents work without anyone calling `purlin:status`. It needs no installation step: it comes with the plugin, honours `report` and `digest` in `.purlin/config.json` (`report: false` or `digest: off` disables it), never blocks, never prints, and never reaches the network.

The skill asks the questions; `scripts/init/scaffold.py` writes the files and prints one line per path it wrote, kept, copied or skipped, so what init did is on screen rather than inferred from the tree.

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

**Shell.** Source the harness in your test scripts. `purlin:init` copies `scripts/proof/shell_purlin.sh`
into the project under the name every shell test sources, which is the **Installed as** column of
[supported frameworks](../references/supported_frameworks.md):
```bash
source .purlin/plugins/purlin-proof.sh
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
  "pre_push": "warn",
  "remote_verification": "off",
  "mutation_checks": false,
  "report": true,
  "digest": "auto"
}
```

`mutation_checks` is off by default. When it is on, every new or amended proof is mutation-checked before the commit that carries it: break the behaviour, watch the proof fail, restore. It is the only check that catches a proof which passes against broken code, and it costs roughly twice the tokens and minutes per proof; see [spec_quality_guide.md § Mutation check](../references/spec_quality_guide.md#mutation-check). `purlin:init` asks; `purlin:init --set mutation_checks on|off` changes it later.

Three further fields are optional and a full `purlin:init` never writes them. `platforms` is the registry the `@on(<platform-id>)` proof tags resolve against; the family ids `windows`, `macos` and `linux` work with no config at all, and an entry is what adds a version, an architecture or a runner:

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

`quality_gate` is the third. It is project policy for the CI gate `scripts/ci/verify_gate.py`, not a framework setting: `"off"`, which is also what the gate assumes when the key is absent, or `"deterministic"`, under which the gate fails on a test graded HOLLOW by the deterministic checks and on a proof description graded UNPROVABLE. A proof the checks cannot read is never a failure. Set it with `purlin:init --set quality_gate off|deterministic`, which writes that one key and nothing else; `purlin:init --update` never backfills it and never asks, so a project that has not opted in carries no such key. The field declares the policy and branch protection on the gate job enforces it, exactly as `remote_verification` does; see [Regulated Environments](regulated-environments.md).

The HTML dashboard is enabled by default (`"report": true`). When enabled, `purlin:status` writes `.purlin/report-data.js` on every call, and `purlin:init` copies the plugin's `purlin-report.html` to the project root. Open it in a browser to see live coverage. Toggle with `purlin:init --set report on|off`. See the [Dashboard Guide](dashboard-guide.md) for details.

Read or update config with the `purlin_config` MCP tool, or edit the files directly.

## What Gets Created

```
your-project/
  .purlin/
    config.json            # Team defaults
    config.local.json      # Per-user (gitignored)
    plugins/               # Proof collector for your test framework
    hooks/                 # The generated hook shims (committed)
    plugin-root            # Where this machine keeps the plugin (gitignored)
    report-data.js         # Project digest (committed, regenerated by pre-commit hook)
  specs/
    _anchors/              # Cross-cutting constraints (optionally synced from external sources)
  .gitignore               # Updated with Purlin entries
  purlin-report.html       # Dashboard copy (gitignored, if report enabled)
  .git/hooks/pre-push      # Delegates to .purlin/hooks/pre-push
  .git/hooks/pre-commit    # Delegates to .purlin/hooks/pre-commit
```

## Changing Settings After Init

Already initialized? Use `purlin:init --force` to reconfigure, or change individual settings:

| What you want | How |
|---------------|-----|
| Switch pre-push mode (warn/strict/off) | `purlin:init --set pre_push` |
| Turn mutation checks on or off | `purlin:init --set mutation_checks on\|off` |
| Migrate the project to the installed plugin | `purlin:init --update` |
| Toggle HTML dashboard | `purlin:init --set report` |
| Change digest mode (auto/warn/off) | `purlin:init --set digest` |
| Add a proof plugin | `purlin:init --add-plugin ./my-plugin.py` |
| Set external audit criteria | `purlin:init --sync-audit-criteria` |
| Change audit LLM (experimental) | `purlin:init --audit-llm` |
| Write the CI workflow | `purlin:init --ci` |
| Re-run full setup | `purlin:init --force` |

## Continuous integration

```
purlin:init --ci
```

Purlin asks before it writes anything, then writes one file:
`.github/workflows/purlin-verify-gate.yml`. It is the same verification gate
this plugin runs on itself, in the form a project that clones the tooling
needs. A file already at that path is kept and its bytes are left alone.

What the job does, on a push or pull request that touches `specs/**`,
`.purlin/config.json` or `.github/workflows/**`: it checks out the full
history, clones Purlin at a pinned ref, and runs
`scripts/ci/verify_gate.py --check`, which exits 1 when a feature is not
VERIFIED or is awaiting a runner. Those three trigger paths are what a project
can change; the plugin's own workflow also watches its `scripts/`, which no
project that installs Purlin has.

The trigger and the ref, as the written file carries them:

```yaml
on:
  push:
    paths:
      - 'specs/**'
      - '.purlin/config.json'
      - '.github/workflows/**'

jobs:
  verify-gate:
    runs-on: ubuntu-latest
    env:
      PURLIN_REF: v<VERSION>
```

`PURLIN_REF` is stamped with the version that was installed when the file was
written, and the clone step reads it. Change that one line to move the job to
another release; nothing else in the file names a version.

Two things the file does not do. It does not run your tests: the gate reads
the proof files the run leaves behind, so the job that regenerates them is
yours to write, and the recipe for the two of them in one job is in
[the testing workflow guide](testing-workflow-guide.md#ci-pipeline). And it is
a check, not a gate, until branch protection marks it required; which layer
that is, and what each layer can and cannot stop, is in
[references/hard_gates.md](../references/hard_gates.md).

For the platform side of CI, the runner workflow that proves an `@on(...)`
proof on another operating system and commits the scoped proof file back, see
[references/remote_verification.md](../references/remote_verification.md).

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

## A workspace in a subdirectory

`purlin:init` creates the workspace where you run it. In a monorepo that is usually one package, so `.purlin/` and `specs/` sit under `packages/api/` rather than at the repository root. The Purlin MCP server resolves one project root when the session starts, in this order:

1. `PURLIN_PROJECT_ROOT`, when it is set and names a directory that exists.
2. A climb from the working directory to the nearest `.purlin/` marker.
3. The working directory, when no marker is found in it or above it.

A session opened at the monorepo root never climbs downward, so step 2 finds nothing and step 3 hands back the root. Rather than report a project with no features, every tool answers with two lines:

```
No Purlin workspace at /Users/you/repo: .purlin/config.json is not there. That root came from the working directory, with no .purlin/ marker in it or above it.
Fix: pass project_root to this tool, or set PURLIN_PROJECT_ROOT to the workspace directory (in .claude/settings.json "env" for the project), or run purlin:init there.
```

There are two ways to point it at the workspace.

**Set it for the project.** Add the variable to `.claude/settings.json` at the monorepo root, so every session started anywhere in that repository resolves the same root:

```json
{
  "env": {
    "PURLIN_PROJECT_ROOT": "/Users/you/repo/packages/api"
  }
}
```

The value is read as a literal path, so give it an absolute one. Commit the file and everyone on the team gets the same root.

**Or name it per call.** Each of the three tools takes an optional `project_root` argument that overrides the resolved root for that one call. Use it to look at a second workspace without restarting the session, which is the only way to change the startup root otherwise.

Splitting one repository into several workspaces (the Scaling advice above) means one of these per workspace.

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
| `plugin-copies-stale` | Replaces each `.purlin/plugins/` copy with the installed plugin's file, keeping the bytes that were there at `.purlin/plugins/<name>.local-<sha8>.bak` first |
| `config-fields-missing` | Fills config fields from the template, removes retired ones and stamps `version` from the installed `VERSION` |
| `hooks-stale` | Rewrites `.purlin/hooks/pre-commit` and `.purlin/hooks/pre-push` from the installed plugin and reinstalls the hook git runs, when the one that is there is a Purlin hook in a shape the plugin stopped writing (a dangling symlink, a symlink into the plugin, a copy of the hook body, or a delegator without the missing-shim guard). A hook of your own is never touched |
| `dashboard-stale` | Copies the installed `purlin-report.html` over a root dashboard that is a dangling symlink or whose bytes are not this plugin's |
| `digest-schema-old` | Rebuilds `.purlin/report-data.js` when it was written at an older payload schema, so the dashboard and the QA report stop reading fields that are not there |
| `receipt-v1` | Prints `→ Run: purlin:verify`. A receipt is a claim that tests ran, so the update never writes one |
| `legacy-mcp` | Removes the legacy `purlin` entry from `.mcp.json` (Step 5c of `purlin:init`), then `/reload-plugins` |

`purlin:init --update --check` reports what is pending and writes nothing; it is also what a CI preflight runs, so a runner never proves anything with stale plugin copies. `purlin:init --update --platform-id <id>` says what a legacy `@windows` tag becomes (default: the `windows` OS family). Every skill points at the same advisory: when `purlin:status` or any other skill opens with a pending-migrations block, that is this command asking to be run.

### When the plugin is older than the project

The opposite case is not a migration. A project stamped with a version newer than the installed
plugin (a teammate who has not run the marketplace update yet, or a branch someone else
initialized) gets one line saying so:

```
⚠ This project was initialized by Purlin 0.11.0 and the installed plugin is 0.10.0.
→ Update the plugin, not the project: claude plugin marketplace update
```

Nothing is pending, and `purlin:init --update` is not the fix: it would stamp the project down to
the older plugin and lose what the newer one wrote. Update the plugin and the line goes away.

The update never scaffolds a runner and never issues a receipt. Registering a platform and writing its workflow is `purlin:test`'s consent path; receipts come from `purlin:verify` after a fresh run.

## Upgrading from an Older Version of Purlin

If you have a pre-0.9.0 Purlin installation (with `features/`, companion files, sync ledger, etc.):

**Keep your old `features/` directory.** `purlin:spec-from-code` reads your existing specs and uses them as migration context, so old scenarios and rules survive in the new format. Do not throw away work you have already done.

Remove old artifacts that are now managed by the plugin system. Every path is written out in full
because this is pasted at the root of your project, where `rm -rf pl-* *.sh` would take the shell
scripts you wrote along with the ones Purlin left behind:

```bash
rm -rf .purlin/
rm -f pl-init.sh pl-run.sh
rm -f pl-cdd-start.sh pl-cdd-stop.sh
rm -f pl-run-architect.sh pl-run-builder.sh pl-run-qa.sh
rm -rf .claude/commands/
rm -f .claude/agents/purlin-auditor.md
rm -f .claude/agents/purlin-builder.md
rm -f .claude/agents/purlin-reviewer.md
```

This removes:
- `.purlin/`: old config and state files, regenerated by `purlin:init`
- `pl-init.sh` and `pl-run.sh`: the launcher scripts the v0.8.5 submodule layout symlinked at the project root
- `pl-cdd-start.sh`, `pl-cdd-stop.sh`, `pl-run-architect.sh`, `pl-run-builder.sh` and `pl-run-qa.sh`: the same launchers under the names v0.8.0 and earlier used. Delete only the ones your root actually carries
- `.claude/commands/`: old command definitions, now provided by the plugin
- `purlin-auditor.md`, `purlin-builder.md` and `purlin-reviewer.md` under `.claude/agents/`: old project-local agent definitions. The independent auditor ships with the plugin as `purlin:purlin-auditor`; the former `purlin-builder` and `purlin-reviewer` are retired

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

Plugins are installed to `.purlin/plugins/` and work immediately; `ls .purlin/plugins/` is what lists them.
