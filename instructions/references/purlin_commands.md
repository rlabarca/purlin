# Purlin Agent Command Tables

> Read by the Purlin Agent during startup. Print the appropriate variant.

## Default Variant (no mode active)

```
Purlin Agent — Ready
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Unified agent with three modes: Engineer, PM, QA.
Activate a mode with /pl-mode or invoke a mode-specific skill.

  Common
  ──────
  /pl-status                 Project status and work discovery
  /pl-mode <mode>            Switch mode (pm | engineer | qa)
  /pl-resume [save]          Save or restore session state
  /pl-help                   Full command reference
  /pl-find <topic>           Search feature specs
  /pl-cdd                    Start/stop CDD Dashboard
  /pl-remote <cmd>           Branch collaboration (push | pull | add)
  /pl-override-edit          Edit PURLIN_OVERRIDES.md
  /pl-update-purlin          Update Purlin submodule
  /pl-whats-different        Compare branches

  Engineer Mode
  ──────
  /pl-build [feature]        Implement features (activates Engineer)
  /pl-unit-test              Run/author unit tests
  /pl-web-test               Visual verification via Playwright
  /pl-delivery-plan          Create phased delivery plan
  /pl-release <cmd>          Release checklist (check | run | step)
  /pl-server                 Dev server lifecycle
  /pl-infeasible             Escalate INFEASIBLE to PM
  /pl-propose                Propose spec changes to PM
  /pl-spec-code-audit        Spec-code alignment audit
  /pl-spec-from-code         Reverse-engineer specs from code
  /pl-anchor arch_*          Create/update technical anchors
  /pl-tombstone              Retire a feature

  PM Mode
  ──────
  /pl-spec [topic]           Author/refine feature spec (activates PM)
  /pl-anchor design_*|policy_*  Create/update design/policy anchors
  /pl-design-ingest          Figma-to-spec pipeline
  /pl-design-audit           Spec-design consistency audit

  QA Mode
  ──────
  /pl-verify [feature]       Verification workflow (activates QA)
  /pl-complete               Mark feature complete
  /pl-discovery              Record/manage discoveries
  /pl-qa-report              QA session summary
  /pl-regression <cmd>       Regression suite (run | author | evaluate)
  /pl-fixture                Test fixture management

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```
