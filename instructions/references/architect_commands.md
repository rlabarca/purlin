# Architect Command Tables

> This file is read by the Architect during the Startup Print Sequence (Section 5.0).
> Print the appropriate variant verbatim based on the current branch.

## Main Branch Variant

Print this variant when the branch is `main` (no active collaboration branch).

```
Purlin Architect — Ready
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

This is the Architect — it designs feature specs, sets
architectural rules, and owns the release process. It doesn't
write code; everything gets handed off to the Builder through
specs.

  Global
  ──────
  /pl-status                 Check CDD status and action items
  /pl-resume [save|role]     Save or restore session state
  /pl-help                   Re-display this command list
  /pl-find <topic>           Discover where a topic lives in specs
  /pl-agent-config           Modify agent config
  /pl-cdd                    Start, stop, or check CDD Dashboard
  /pl-override-edit          Edit & validate ARCHITECT_OVERRIDES.md
  /pl-update-purlin          Intelligent submodule update

  Specification & Design
  ──────
  /pl-spec <topic>           Add or refine a feature spec
  /pl-anchor <topic>         Create or update an anchor node
  /pl-tombstone <name>       Retire a feature (tombstone for Builder)
  /pl-design-ingest          Ingest a design artifact into visual spec
  /pl-design-audit           Audit design artifact integrity
  /pl-spec-code-audit        Full spec-code audit (plan mode)
  /pl-spec-from-code         Reverse-engineer specs from existing code
  /pl-fixture                Test fixture convention and workflow

  Release
  ──────
  /pl-release-check          Execute the release checklist step by step
  /pl-release-run            Run a single release step by name
  /pl-release-step           Create, modify, or delete a release step

  Collaboration & Git
  ──────
  /pl-whats-different        Compare branches (main checkout only)
  /pl-remote-push            Push active branch to remote
  /pl-remote-pull            Pull remote into active branch

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

## Branch Collaboration Variant

Print this variant when `.purlin/runtime/active_branch` exists and is non-empty. Substitute the actual branch name for `<branch>`.

```
Purlin Architect — Ready  [Branch: <branch>]
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

This is the Architect — it designs feature specs, sets
architectural rules, and owns the release process. It doesn't
write code; everything gets handed off to the Builder through
specs.

  Global
  ──────
  /pl-status                 Check CDD status and action items
  /pl-resume [save|role]     Save or restore session state
  /pl-help                   Re-display this command list
  /pl-find <topic>           Discover where a topic lives in specs
  /pl-agent-config           Modify agent config
  /pl-cdd                    Start, stop, or check CDD Dashboard
  /pl-override-edit          Edit & validate ARCHITECT_OVERRIDES.md
  /pl-update-purlin          Intelligent submodule update

  Specification & Design
  ──────
  /pl-spec <topic>           Add or refine a feature spec
  /pl-anchor <topic>         Create or update an anchor node
  /pl-tombstone <name>       Retire a feature (tombstone for Builder)
  /pl-design-ingest          Ingest a design artifact into visual spec
  /pl-design-audit           Audit design artifact integrity
  /pl-spec-code-audit        Full spec-code audit (plan mode)
  /pl-spec-from-code         Reverse-engineer specs from existing code
  /pl-fixture                Test fixture convention and workflow

  Release
  ──────
  /pl-release-check          Execute the release checklist step by step
  /pl-release-run            Run a single release step by name
  /pl-release-step           Create, modify, or delete a release step

  Collaboration & Git
  ──────
  /pl-remote-push            Push active branch to remote
  /pl-remote-pull            Pull remote into active branch

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

