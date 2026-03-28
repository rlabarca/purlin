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
  purlin:resume [save]          Recover after context clear or restart
  purlin:help                   Full command reference
  purlin:find <topic>           Search feature specs
  purlin:remote <cmd>           Branch collaboration (push | pull | add | branch)
  purlin:override-edit          Edit PURLIN_OVERRIDES.md
  purlin:update                 Update Purlin plugin
  purlin:whats-different        Compare branches
  purlin:session-name [label]   Update terminal session display name
  purlin:worktree <cmd>         Worktree management (list | cleanup-stale)
  purlin:merge                  Merge worktree back to source branch
  purlin:purlin-issue           Report a Purlin framework bug

  Engineer Mode
  ──────
  purlin:build [feature]        Implement features (activates Engineer)
  purlin:unit-test              Run/author unit tests
  purlin:web-test               Visual verification via Playwright
  purlin:delivery-plan          Create phased delivery plan
  purlin:toolbox <cmd>          Agentic Toolbox (list | run | create | edit | ...)
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
  purlin:design-ingest          Figma-to-spec pipeline
  purlin:design-audit           Spec-design consistency audit

  QA Mode
  ──────
  purlin:verify [feature] [--mode <mode>]
                             Verification workflow (activates QA)
                             Modes: auto | smoke | regression | manual
                             Default: full pipeline (Phase A + B)
  purlin:complete               Mark feature complete
  purlin:discovery              Record/manage discoveries
  purlin:qa-report              QA session summary
  purlin:regression <cmd>       Regression suite (run | author | evaluate)
  purlin:smoke <feature>        Promote tests to smoke tier
  purlin:fixture                Test fixture management

  Also available from QA (no mode switch):
  purlin:unit-test              Run tests (verify-only, cannot edit code)
  purlin:web-test               Run browser tests (verify-only)
  purlin:server                 Start/stop dev server (run-only)

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```
