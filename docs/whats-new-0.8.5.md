# What's New in v0.8.5

> **Note:** The `pl-run.sh` launcher introduced in this release was subsequently retired in v0.8.6 as part of the plugin migration. It has been replaced by the `purlin:resume` skill, which runs inside an already-active Claude Code session. References to `./pl-run.sh` below are historical.

Upgrading from v0.8.4 or earlier? Here's everything that changed.

---

## The Big Change: One Agent, Three Modes

Previously, Purlin ran **four separate agents** — Architect, Builder, QA, and PM — each with its own launcher, config, and command set. That's gone.

Now there is **one unified agent** with three operating modes: **PM**, **Engineer**, and **QA**. You launch it once and switch modes during the session.

| Old (v0.8.4) | New (v0.8.5) |
|---|---|
| `pl-run-architect.sh` | `./pl-run.sh` |
| `pl-run-builder.sh` | `./pl-run.sh --mode engineer` |
| `pl-run-qa.sh` | `./pl-run.sh --mode qa` |
| `pl-run-pm.sh` | `./pl-run.sh --mode pm` |

Switch mid-session with `purlin:mode engineer`, `purlin:mode pm`, or `purlin:mode qa`. Write-access boundaries still enforce that each mode can only touch its own files.

**Role renames:** Architect is now **PM**. Builder is now **Engineer**. QA stays QA.

---

## How Each Mode Changed

### PM Mode

- Owns feature specs, design/policy anchors, and prose docs (same as Architect, new name).
- Still the Figma integration point — `purlin:invariant add-figma` replaces `purlin:design-ingest` for Figma imports; `purlin:design-audit` works the same.
- New responsibility: reviews Engineer deviations recorded in companion files.
- No longer has a Critic feeding it action items — you use `purlin:status` instead.

### Engineer Mode

- Owns code, tests, scripts, companion files, and instructions (same as Builder, new name).
- **Companion commit covenant:** Every code commit for a feature MUST include a companion file update. This is enforced on mode switch — you can't leave Engineer mode with companion debt.
- Three escalation paths to PM: `purlin:infeasible` (blocking), inline deviations (non-blocking), `purlin:propose` (proactive).
- `purlin:verify` auto-fix loop now toggles into Engineer internally to fix failing tests without a full mode switch.

### QA Mode

- Runs the full verification workflow: `purlin:verify` with auto-fix, strategy menu, and regression readiness checks.
- **Cross-mode test execution:** QA can run `purlin:unit-test`, `purlin:web-test`, and `purlin:server` for verification without switching to Engineer.
- `purlin:regression` is now a single unified command (replaces three separate commands).
- Smoke testing tiers still work — `purlin:smoke` promotes features to higher priority.

---

## New and Deprecated Skills

### New Skills

| Skill | Mode | What It Does |
|---|---|---|
| `purlin:mode` | Any | Switch between PM, Engineer, and QA mid-session. |
| `purlin:regression` | QA | Unified regression management (author + run + evaluate). |
| `purlin:remote` | Any | Unified branch collaboration (replaces push/pull/add). |

| `purlin:session-name` | Any | Set terminal identity (badge + title). |
| `purlin:toolbox` | Any | Manage project tools — list, run, create, share. |
| `purlin:tombstone` | Engineer | Retire a feature with a tombstone record. |

### Deprecated / Removed Skills

| Old Skill | Replacement |
|---|---|
| `purlin:regression-run` | `purlin:regression` |
| `purlin:regression-author` | `purlin:regression` |
| `purlin:regression-evaluate` | `purlin:regression` |
| `purlin:remote-push` | `purlin:remote` |
| `purlin:remote-pull` | `purlin:remote` |
| `purlin:remote-add` | `purlin:remote` |

| `purlin:release-run` | Removed (toolbox tools replace release steps) |
| `purlin:release-check` | Removed |
| `purlin:release-step` | Removed |
| `purlin:cdd` (removed) | Removed (dashboard is gone) |

---

## Running the Agent — All New

One launcher: `./pl-run.sh`. Everything is a flag.

```bash
# Default — starts in open mode, waits for you
./pl-run.sh

# Start in a specific mode
./pl-run.sh --mode engineer
./pl-run.sh --mode pm
./pl-run.sh --mode qa

# Auto-build: Engineer mode, finds work, starts immediately
./pl-run.sh --auto-build

# Auto-verify: QA mode, finds work, starts immediately
./pl-run.sh --auto-verify

# Control work discovery and auto-start separately
./pl-run.sh --find-work --mode engineer
./pl-run.sh --find-work --auto-start --mode qa

# Model and effort overrides
./pl-run.sh --model claude-sonnet-4-6 --effort medium
./pl-run.sh --model "claude-opus-4-6[1m]"

# Bypass permissions (YOLO mode)
./pl-run.sh --yolo

# Session-only settings (don't persist to config)
./pl-run.sh --model claude-sonnet-4-6 --no-save
```

**Startup flags:**
- `--find-work` — Scan the project and suggest work on startup (default: off for manual sessions).
- `--auto-start` — Begin executing the work plan immediately (implies `--find-work`).
- `--auto-build` — Shorthand for `--mode engineer --find-work --auto-start`.
- `--auto-verify` — Shorthand for `--mode qa --find-work --auto-start`.

**Config persistence:** Flags are saved to your local config by default. Use `--no-save` for one-off overrides.

---

## The Dashboard Is Gone

The CDD Dashboard (`serve.py`, `pl-cdd-start.sh`, the web UI at localhost:3000) and the Critic background engine have been **completely removed** — about 24,000 lines of code deleted.

**What replaces it:**

| Old Dashboard Feature | v0.8.5 Equivalent |
|---|---|
| Feature status grid | `purlin:status` — text-based, mode-aware, always current |
| Spec Map visualization | `purlin:toolbox run spec map` — generates a full dependency graph PNG and displays it in a split pane (requires iTerm2) |
| Critic action items | `purlin:status` action items per mode |
| Delivery plan progress | `purlin:status` shows phase progress inline |
| Agent configuration panel | `./pl-run.sh` flags + `.purlin/config.json` |
| Branch collaboration panel | `purlin:remote` + `git` directly |
| Execution group display | `purlin:delivery-plan` output |

The scan engine (`tools/cdd/scan.sh`) still runs — it powers `purlin:status`. You just don't need a browser anymore.

---

## The Agentic Toolbox

The release checklist system is gone. In its place: the **Agentic Toolbox** — independent, reusable tools that the agent can run in any order at any time.

```
purlin:toolbox list                     # See all available tools
purlin:toolbox run spec check           # Run Purlin's spec integrity checker
purlin:toolbox run spec map             # Generate a visual dependency graph (iTerm2 required)
purlin:toolbox create                   # Build your own project tool
purlin:toolbox add <git-url>            # Install a community tool
```

Three categories of tools:

| Category | Where They Live | Examples |
|----------|----------------|---------|
| **Purlin** | Framework-distributed (read-only) | Spec Check, Spec Map |
| **Project** | `.purlin/toolbox/project_tools.json` | Record Version Notes, Docs Update, Push to Remote |
| **Community** | Downloaded via `add` | Shared tools from git repos |

Each tool is a JSON definition with either shell commands, agent instructions, or both. Create project tools with `purlin:toolbox create`. Copy and customize Purlin tools with `purlin:toolbox copy`.

---

## QA Voice

QA mode now speaks like **Michelangelo** from Teenage Mutant Ninja Turtles — surfer-dude energy with full technical accuracy. Bug reports are still precise and correct, just delivered Mikey-style. The voice is exclusive to QA mode; PM and Engineer use standard professional tone.

---

## Spec-Code Audit Improvements

`purlin:spec-code-audit` now detects **circular dependencies** in the prerequisite graph. When cycles are found, the audit presents each cycle with resolution options and recommends which link to break based on the weakest prerequisite relationship.

The Spec Check toolbox tool (`purlin:toolbox run spec check`) provides broader integrity analysis: stale references, naming consistency, category grouping, and orphaned companion files.

---

## Verification Auto-Fix Loop

`purlin:verify` now includes an **auto-fix iteration loop** (Phase A.5). When automated scenarios fail:

1. QA identifies the failure.
2. An internal mode switch gives Engineer write access.
3. Engineer fixes the issue.
4. QA re-verifies.
5. Repeat until clean or a configurable retry limit is reached.

This happens inside a single QA session — no manual mode switching needed. A **strategy menu** at the start of verification lets you choose: targeted (specific features), full (everything in TESTING), or regression-only.

---

## Session Improvements

**PID-scoped checkpoints.** Each terminal gets its own checkpoint file (`session_checkpoint_<pid>.md`), so concurrent terminals never collide. Stale checkpoints from crashed terminals are automatically reaped at startup.

**Warp terminal support.** Terminal identity (badge and title) now works in both iTerm2 and Warp. The agent detects your terminal and dispatches to the right API.

---

## Tips and Tricks

**Start simple.** Launch with `./pl-run.sh`, no flags. Ask for what you need. The agent will suggest a mode.

**Let `purlin:status` be your home screen.** It shows exactly what needs attention in your current mode. Run it whenever you lose context.

**Use `--auto-build` for batch work.** If you have a delivery plan with multiple features, `./pl-run.sh --auto-build` picks up where you left off and builds through the queue.

**Mode switching is cheap.** Wrote a spec and want to build it? `purlin:mode engineer` — your context carries over. Found a bug during build? `purlin:mode qa` to record a discovery, then `purlin:mode engineer` to fix it.

**Session recovery works.** If you run out of context or close the terminal, `purlin:resume` picks up where you left off. The agent saves checkpoints automatically. Use `purlin:resume save` before a deliberate `/clear`.

**Companion files are mandatory now.** Every code commit needs a companion file entry. Don't fight it — a one-line `[IMPL] Built the thing` is enough. The agent blocks mode switches if you skip it.

**Concurrent builds still work.** `purlin:delivery-plan` groups independent features into parallel phases. `purlin:build` spawns worktree sub-agents to build them simultaneously.

**Upgrading?** Run `purlin:update` from your old session, exit, then relaunch with `./pl-run.sh`. Run `purlin:update` a second time — it will ask you to finalize the update. That's when it converts your project: consolidating config, renaming roles, and cleaning up old launchers.
