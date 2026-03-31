# Purlin Agent Command Tables

> Read and printed by `purlin:help` and `purlin:mode`. NOT printed at startup — startup shows `Use purlin:help for commands` only.

## Default Variant (no mode active)

```
Purlin Agent — Ready
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Unified agent with three modes: Engineer, PM, QA.
Activate a mode with purlin:mode or invoke a mode-specific skill.

  Common
  ──────
  purlin:status                 What needs doing? (project scan)
  purlin:mode [mode]            Show current mode, or switch (pm | engineer | qa)
  purlin:help                   Full command reference
  purlin:find <topic>           Search feature specs
  purlin:init [--force]         Initialize project for Purlin
  purlin:update                 Update Purlin plugin
  purlin:config [setting] [on|off]
                                View or change Purlin behavior settings
  purlin:session-name [label]   Update terminal session display name
  purlin:purlin-issue           Report a Purlin framework bug

  Session & Branching
  ──────
  purlin:resume [OPTIONS]       Session recovery (--mode, --build, --verify, --pm,
                                --worktree, --yolo, --find-work, --no-save)
  purlin:resume save            Save checkpoint before /clear or terminal close
  purlin:resume merge-recovery  Resolve pending worktree merge failures
  purlin:remote push            Push collaboration branch to remote
  purlin:remote pull [branch]   Pull remote branch into local
  purlin:remote add [url]       Configure a git remote
  purlin:remote branch <cmd>    Branch lifecycle (create | join | leave | list)
  purlin:whats-different        Compare branches
  purlin:worktree <cmd>         Worktree management (list | cleanup-stale [--dry-run])
  purlin:merge                  Merge worktree back to source branch

  Engineer Mode
  ──────
  purlin:build [feature]        Implement features (activates Engineer)
  purlin:unit-test              Run/author unit tests
  purlin:web-test               Visual verification via Playwright
  purlin:delivery-plan          Create phased delivery plan
  purlin:toolbox                Guided interactive menu
  purlin:toolbox list           Show all tools grouped by category
  purlin:toolbox run <tool>     Execute a tool
  purlin:toolbox create         Create a new project tool
  purlin:toolbox edit <tool>    Edit a project or community tool
  purlin:toolbox copy <tool>    Copy a purlin tool to project
  purlin:toolbox add <git-url>  Download a community tool
  purlin:toolbox pull [tool]    Update community tool(s)
  purlin:toolbox push <tool>    Push tool to source repo
  purlin:toolbox delete <tool>  Delete a project or community tool
  purlin:server                 Dev server lifecycle
  purlin:infeasible             Escalate INFEASIBLE to PM
  purlin:propose                Propose spec changes to PM
  purlin:spec-code-audit        Spec-code alignment audit
  purlin:spec-from-code         Reverse-engineer specs from code
  purlin:anchor arch_*          Create/update technical anchors
  purlin:tombstone              Retire a feature

  PM Mode
  ──────
  purlin:spec [topic]           Author/refine feature spec (activates PM)
  purlin:anchor design_*|policy_*  Create/update design/policy anchors
  purlin:invariant list         List all invariants and their status
  purlin:invariant add <repo-url> [path]
                                Import a git-sourced invariant
  purlin:invariant add-figma <figma-url> [anchor]
                                Import a Figma-sourced design invariant
  purlin:invariant sync [name]  Sync invariant(s) from upstream source
  purlin:invariant check-updates
                                Check all invariants for upstream changes
  purlin:invariant check-conflicts [name]
                                Check for spec conflicts with invariant
  purlin:invariant check-feature <feature>
                                Check feature compliance with invariants
  purlin:invariant validate [name]
                                Validate invariant format and metadata
  purlin:invariant remove <name>
                                Remove an invariant
  purlin:design-audit           Spec-design consistency audit

  QA Mode
  ──────
  purlin:verify [feature] [--mode <mode>] [--auto-verify]
                             Verification workflow (activates QA)
                             Modes: auto | smoke | regression | manual
                             Default: full pipeline (Phase A + B)
  purlin:complete <feature>     Mark feature complete (7 gates)
  purlin:discovery              Record/manage discoveries
  purlin:qa-report              QA session summary
  purlin:regression             Auto-detect and run next step
  purlin:regression run [feature]
                                Execute regression test suite
  purlin:regression author [feature]
                                Author regression test scenarios
  purlin:regression evaluate [feature]
                                Evaluate results against baselines
  purlin:regression promote <feature>
                                Promote a feature to smoke tier
  purlin:regression suggest     Suggest features for smoke tier

  Also available from QA (no mode switch):
  purlin:unit-test              Run tests (verify-only, cannot edit code)
  purlin:web-test               Run browser tests (verify-only)
  purlin:server                 Start/stop dev server (run-only)

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```
